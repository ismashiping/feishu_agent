"""Bounded synchronous execution and per-application runtime state."""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from typing import TYPE_CHECKING, TypeVar

from clinical_agent.api.middleware import _error_response, identity
from clinical_agent.api.schemas import ApiSettings
from clinical_agent.domain.research import ResearchError
from clinical_agent.domain.retrieval import RetrievalError
from clinical_agent.logging_config import log_unexpected

if TYPE_CHECKING:
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from clinical_agent.api.runtime import ServiceBundle

T = TypeVar("T")


class BusyError(RuntimeError):
    pass


class WorkerPool:
    """Bound admission before submit; capacity follows actual concurrent Future completion."""

    def __init__(self, capacity: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=capacity, thread_name_prefix="clinical-api")
        self._slots = BoundedSemaphore(capacity)
        self._lock = Lock()
        self._closing = False

    def submit(self, operation: Callable[[], T]) -> Future[T]:
        with self._lock:
            if self._closing or not self._slots.acquire(blocking=False):
                raise BusyError("busy")
            try:
                future = self._executor.submit(operation)
            except BaseException:
                self._slots.release()
                raise
            future.add_done_callback(lambda _future: self._slots.release())
            return future

    def close(self) -> None:
        with self._lock:
            self._closing = True
        self._executor.shutdown(wait=True, cancel_futures=False)


@dataclass
class _State:
    settings: ApiSettings | None = None
    services: "ServiceBundle | None" = None
    pool: WorkerPool | None = None
    ready: bool = False


async def execute[T](
    state: _State, request: "Request", operation: Callable[[], T]
) -> "T | JSONResponse":
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
        if code in {
            "retrieval_failed",
            "retrieval_embedding_failed",
            "generation_failed",
            "pubmed_failed",
            "openalex_failed",
            "openalex_auth_failed",
            "openalex_rate_limited",
            "openalex_timeout",
        }:
            return _error_response(request, code, 503, True)
        if code in {
            "model_output_invalid",
            "analysis_output_truncated",
            "citation_invalid",
            "extraction_failed",
            "pubmed_invalid",
            "openalex_invalid",
            "openalex_plan_required",
            "openalex_options_retired",
            "openalex_required",
            "local_corpus_not_evidence",
        }:
            return _error_response(request, code, 502)
        return _error_response(
            request,
            code,
            422 if code in {"context_limit", "retrieval_language_unsupported"} else 500,
        )
    except Exception as error:
        log_unexpected("api", error)
        return _error_response(request, "internal_error", 500)


class _SourceError(ValueError):
    pass
