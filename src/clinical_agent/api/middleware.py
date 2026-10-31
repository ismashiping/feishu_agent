"""ASGI request boundary, correlation and safe HTTP errors."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from clinical_agent.api.schemas import ApiError

if TYPE_CHECKING:
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from clinical_agent.api.execution import _State


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


def identity(request: "Request") -> UUID:
    return cast(UUID, getattr(request.state, "request_id", uuid4()))


def _error_response(
    request: "Request", code: str, status: int, retryable: bool = False
) -> "JSONResponse":
    return _error(identity(request), code, status, retryable)


class _Boundary:
    """Small ASGI transport boundary, using the framework for routing and JSON validation."""

    def __init__(self, app: "ASGIApp", state: "_State") -> None:
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
        if scope["method"] == "POST" and scope["path"] in {
            "/v1/documents/import",
            "/v1/questions",
            "/v1/analyses",
            "/v1/reports",
        }:
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
