"""Local HTTP adapter; import does not assemble clients, models, FastAPI or settings."""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import UUID, uuid4

from clinical_agent.api_runtime import (
    ApiError,
    ApiSettings,
    BusyError,
    HealthReport,
    ImportBody,
    ImportResponse,
    QuestionBody,
    ServiceBundle,
    WorkerPool,
    open_api_runtime,
)
from clinical_agent.config import load_settings
from clinical_agent.domain.ingestion import BatchIngestionResult, ImportRequest
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer, ResearchError
from clinical_agent.domain.retrieval import RetrievalError
from clinical_agent.logging_config import configure_logging

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

RuntimeFactory = Callable[[ApiSettings], AbstractContextManager[ServiceBundle]]
T = TypeVar("T")


def _error(identity: UUID, code: str, status: int, retryable: bool = False) -> "JSONResponse":
    from fastapi.responses import JSONResponse

    payload = ApiError(
        request_id=identity,
        error_code=code,
        message="Request could not be completed.",
        retryable=retryable,
    )
    logging.getLogger("clinical_agent").warning(
        "api_request_failed", extra={"request_id": str(identity), "error_code": code}
    )
    return JSONResponse(
        payload.model_dump(mode="json"),
        status_code=status,
        headers={"X-Request-ID": str(identity), **({"Retry-After": "1"} if code == "busy" else {})},
    )


@dataclass
class _State:
    settings: ApiSettings | None = None
    services: ServiceBundle | None = None
    pool: WorkerPool | None = None
    ready: bool = False


class _Boundary:
    """Small ASGI transport boundary, using the framework for routing and JSON validation."""

    def __init__(self, app: "ASGIApp", state: _State) -> None:
        self.app, self.state = app, state

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        identity = uuid4()
        headers = scope.get("headers", [])
        ids = [value for key, value in headers if key.lower() == b"x-request-id"]
        invalid_id = False
        if ids:
            try:
                if len(ids) != 1:
                    raise ValueError("Duplicate identity")
                identity = UUID(ids[0].decode("ascii"))
            except (ValueError, UnicodeError):
                invalid_id = True
        scope.setdefault("state", {})["request_id"] = identity

        async def identified(message: "Message") -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ] + [(b"x-request-id", str(identity).encode())]
            await send(message)

        async def reject(code: str, status: int) -> None:
            await _error(identity, code, status)(scope, receive, identified)

        if invalid_id:
            await reject("invalid_request_id", 400)
            return
        if scope["method"] == "POST" and scope["path"] in {"/v1/documents/import", "/v1/questions"}:
            mapping = {key.lower(): value for key, value in headers}
            if (
                mapping.get(b"content-encoding", b"identity") != b"identity"
                or mapping.get(b"content-type", b"").split(b";")[0].strip().lower()
                != b"application/json"
            ):
                await reject("unsupported_media_type", 415)
                return
            limit = self.state.settings.max_request_bytes if self.state.settings else 16384
            try:
                size = int(mapping.get(b"content-length", b"0"))
                if size < 0:
                    raise ValueError("Negative length")
            except ValueError:
                await reject("invalid_headers", 400)
                return
            if size > limit:
                await reject("request_too_large", 413)
                return
            body = bytearray()
            try:
                async with asyncio.timeout(10):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        block = message.get("body", b"")
                        if len(body) + len(block) > limit:
                            await reject("request_too_large", 413)
                            return
                        body.extend(block)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await reject("request_timeout", 408)
                return
            delivered = False

            async def replay() -> "Message":
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay, identified)
        else:
            await self.app(scope, receive, identified)


def create_app(
    *, settings: ApiSettings | None = None, runtime_factory: RuntimeFactory | None = None
) -> "FastAPI":
    from fastapi import FastAPI, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    state = _State()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> "AsyncIterator[None]":
        stack = ExitStack()
        try:
            try:
                state.settings = (
                    ApiSettings.model_validate(settings)
                    if settings
                    else cast(Callable[[], ApiSettings], ApiSettings)()
                )
                configure_logging(load_settings())
                state.services = await asyncio.to_thread(
                    stack.enter_context, (runtime_factory or open_api_runtime)(state.settings)
                )
                state.pool = WorkerPool(state.settings.max_in_flight)
                state.ready = True
            except Exception:
                raise RuntimeError("startup_failed") from None
            yield
        finally:
            state.ready = False
            try:
                if state.pool is not None:
                    await asyncio.to_thread(state.pool.close)
                await asyncio.to_thread(stack.close)
            except Exception:
                raise RuntimeError("shutdown_failed") from None

    app = FastAPI(
        title="Clinical Literature Agent",
        lifespan=lifespan,
        debug=False,
        responses={
            status: {"model": ApiError}
            for status in (400, 404, 405, 408, 413, 415, 422, 500, 502, 503, 504)
        },
    )
    app.add_middleware(_Boundary, state=state)

    def identity(request: Request) -> UUID:
        return cast(UUID, getattr(request.state, "request_id", uuid4()))

    async def invalid(request: Request, _error: Exception) -> "JSONResponse":
        return _error_response(request, "invalid_request", 422)

    def _error_response(
        request: Request, code: str, status: int, retryable: bool = False
    ) -> "JSONResponse":
        return _error(identity(request), code, status, retryable)

    app.add_exception_handler(RequestValidationError, invalid)

    async def bad_request(request: Request, _exception: Exception) -> "JSONResponse":
        return _error_response(request, "invalid_request", 400)

    async def internal_error(request: Request, _exception: Exception) -> "JSONResponse":
        return _error_response(request, "internal_error", 500)

    app.add_exception_handler(400, bad_request)
    app.add_exception_handler(Exception, internal_error)

    async def not_found(request: Request, _exception: Exception) -> "JSONResponse":
        return _error_response(request, "not_found", 404)

    async def method_error(request: Request, _exception: Exception) -> "JSONResponse":
        return _error_response(request, "method_not_allowed", 405)

    app.add_exception_handler(404, not_found)
    app.add_exception_handler(405, method_error)

    async def execute(request: Request, operation: Callable[[], T]) -> T | JSONResponse:
        if not state.ready or state.pool is None:
            return _error_response(request, "not_ready", 503, True)
        try:
            result = await asyncio.wrap_future(state.pool.submit(operation))
            logging.getLogger("clinical_agent").info(
                "api_request_completed", extra={"request_id": str(identity(request))}
            )
            return result
        except _SourceError:
            return _error_response(request, "source_invalid", 400)
        except BusyError:
            return _error_response(request, "busy", 503, True)
        except (RetrievalError, ResearchError) as error:
            safe = (
                RetrievalError(error.code)
                if isinstance(error, RetrievalError)
                else ResearchError(error.code)
            )
            code = safe.code
            if code.endswith("timeout"):
                return _error_response(request, code, 504, True)
            if code in {"retrieval_failed", "retrieval_embedding_failed", "generation_failed"}:
                return _error_response(request, code, 503, True)
            if code in {"model_output_invalid", "citation_invalid"}:
                return _error_response(request, code, 502)
            return _error_response(request, code, 422 if code == "context_limit" else 500)
        except Exception:
            return _error_response(request, "internal_error", 500)

    @app.get("/health/live", response_model=HealthReport)
    async def live(request: Request) -> HealthReport:
        return HealthReport(request_id=identity(request), status="ok", scope="process")

    @app.get("/health/ready", response_model=HealthReport)
    async def ready(request: Request) -> HealthReport | JSONResponse:
        if not state.ready:
            return _error_response(request, "not_ready", 503, True)
        return HealthReport(request_id=identity(request), status="ok", scope="runtime")

    @app.post("/v1/questions", response_model=ResearchAnswer)
    async def question(body: QuestionBody, request: Request) -> ResearchAnswer | JSONResponse:
        def operation() -> ResearchAnswer:
            assert state.services is not None
            question = QuestionRequest(request_id=identity(request), **body.model_dump())
            answer = ResearchAnswer.model_validate(state.services.research.answer(question))
            if answer.request_id != question.request_id:
                raise ValueError("Answer correlation mismatch")
            return answer

        return await execute(request, operation)

    @app.post("/v1/documents/import", response_model=ImportResponse)
    async def ingest(body: ImportBody, request: Request) -> ImportResponse | JSONResponse:
        def operation() -> ImportResponse:
            assert state.services is not None and state.settings is not None
            try:
                root = state.settings.import_root.resolve(strict=True)
                path = (root / body.relative_path).resolve(strict=True)
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError("Source outside import root")
            except (OSError, ValueError):
                raise _SourceError() from None
            incoming = ImportRequest(
                source_type=body.source_type,
                path=path,
                allowed_root=root,
                ingestion_time=datetime.now(UTC),
            )
            result = BatchIngestionResult.model_validate(state.services.ingestion.ingest(incoming))
            return ImportResponse(request_id=identity(request), result=result)

        return await execute(request, operation)

    return app


class _SourceError(ValueError):
    pass
