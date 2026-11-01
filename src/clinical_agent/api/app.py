"""Application creation, lifespan ownership and exception registration."""

import asyncio
from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack, asynccontextmanager
from typing import TYPE_CHECKING, cast

from clinical_agent.api.execution import WorkerPool, _State
from clinical_agent.api.middleware import _Boundary, _error_response
from clinical_agent.api.routes import register_routes
from clinical_agent.api.runtime import ServiceBundle, open_api_runtime
from clinical_agent.api.schemas import ApiError, ApiSettings
from clinical_agent.config import load_settings
from clinical_agent.logging_config import configure_logging, log_unexpected

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
#符合 RuntimeFactory 类型要求的函数，应当接收一个 ApiSettings
# 对象，返回一个上下文管理器，进入该上下文后获得 ServiceBundle 对象。
RuntimeFactory = Callable[[ApiSettings], AbstractContextManager[ServiceBundle]]


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
                configure_logging(load_settings())
                state.settings = (
                    ApiSettings.model_validate(settings)
                    if settings
                    else cast(Callable[[], ApiSettings], ApiSettings)()
                )
                state.services = await asyncio.to_thread(
                    stack.enter_context, (runtime_factory or open_api_runtime)(state.settings)
                )
                state.pool = WorkerPool(state.settings.max_in_flight)
                state.ready = True
            except Exception as error:
                log_unexpected("startup", error)
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

    async def invalid(request: Request, _error: Exception) -> "JSONResponse":
        return _error_response(request, "invalid_request", 422)

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

    register_routes(app, state)
    return app
