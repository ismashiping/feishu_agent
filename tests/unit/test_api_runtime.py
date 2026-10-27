"""Bounded standard executor and API resource assembly contracts."""

import asyncio
import threading
from contextlib import contextmanager

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_in_flight", 0),
        ("max_in_flight", 5),
        ("max_in_flight", True),
        ("max_request_bytes", 0),
        ("max_request_bytes", 65537),
    ],
)
def test_settings_are_bounded(tmp_path, field, value):
    from clinical_agent.api_runtime import ApiSettings

    with pytest.raises(ValidationError):
        ApiSettings(
            model_dir=tmp_path,
            import_root=tmp_path,
            snapshot_dir=tmp_path / "snapshots",
            **{field: value},
        )


@pytest.mark.asyncio
async def test_cancelling_wait_does_not_release_running_work():
    from clinical_agent.api_runtime import BusyError, WorkerPool

    pool = WorkerPool(1)
    entered, release = threading.Event(), threading.Event()

    def work():
        entered.set()
        assert release.wait(5)
        return 1

    future = pool.submit(work)
    try:
        assert await asyncio.to_thread(entered.wait, 3)
        waiter = asyncio.ensure_future(asyncio.wrap_future(future))
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        with pytest.raises(BusyError):
            pool.submit(lambda: 2)
    finally:
        release.set()
        await asyncio.to_thread(pool.close)
    assert future.result() == 1
    with pytest.raises(BusyError):
        pool.submit(lambda: 3)


def test_submit_failure_returns_capacity(monkeypatch):
    from clinical_agent.api_runtime import WorkerPool

    pool = WorkerPool(1)
    submit = pool._executor.submit

    def fail(*args, **kwargs):
        raise RuntimeError("submit failed")

    monkeypatch.setattr(pool._executor, "submit", fail)
    with pytest.raises(RuntimeError):
        pool.submit(lambda: 1)
    monkeypatch.setattr(pool._executor, "submit", submit)
    assert pool.submit(lambda: 2).result(3) == 2
    pool.close()


def test_shared_runtime_one_model_engine_http(monkeypatch, tmp_path):
    from clinical_agent.adapters import deepseek, embedding
    from clinical_agent.adapters.postgres import connection
    from clinical_agent.api_runtime import ApiSettings, open_api_runtime
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.research import ResearchService

    events = []
    monkeypatch.setattr(
        connection, "DatabaseSettings", lambda: events.append("db-config") or object()
    )
    monkeypatch.setattr(
        deepseek, "DeepSeekSettings", lambda: events.append("llm-config") or object()
    )
    monkeypatch.setattr(
        embedding, "load_local_embedder", lambda config: events.append("model") or object()
    )

    @contextmanager
    def engine(settings):
        events.append("db-enter")
        try:
            yield object()
        finally:
            events.append("db-exit")

    @contextmanager
    def llm(settings):
        events.append("http-enter")
        try:
            yield object()
        finally:
            events.append("http-exit")

    monkeypatch.setattr(connection, "database_engine", engine)
    monkeypatch.setattr(deepseek, "deepseek_generator", llm)
    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with open_api_runtime(settings) as services:
        assert isinstance(services.ingestion, IngestionService)
        assert isinstance(services.research, ResearchService)
    assert events == [
        "db-config",
        "llm-config",
        "model",
        "db-enter",
        "http-enter",
        "http-exit",
        "db-exit",
    ]


def test_startup_failure_is_sanitized_and_unwinds(tmp_path):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings

    events = []

    @contextmanager
    def factory(settings):
        try:
            raise RuntimeError("private-startup-secret")
        finally:
            events.append("unwind")
        yield

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with pytest.raises(RuntimeError, match="startup_failed") as error:
        with TestClient(create_app(settings=settings, runtime_factory=factory)):
            pass
    assert "private" not in str(error.value) and events == ["unwind"]


def test_shutdown_failure_is_sanitized(tmp_path):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle

    @contextmanager
    def factory(settings):
        try:
            yield ServiceBundle(ingestion=object(), research=object())
        finally:
            raise RuntimeError("private-shutdown-secret")

    config = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with pytest.raises(RuntimeError, match="shutdown_failed") as error:
        with TestClient(create_app(settings=config, runtime_factory=factory)):
            pass
    assert "private" not in str(error.value)


def test_pool_shutdown_waits_for_actual_work(monkeypatch):
    from clinical_agent.api_runtime import BusyError, WorkerPool

    pool = WorkerPool(1)
    entered, release, closing, closed = [threading.Event() for _ in range(4)]

    def work():
        entered.set()
        assert release.wait(5)

    future = pool.submit(work)
    assert entered.wait(3)
    shutdown = pool._executor.shutdown

    def observed_shutdown(**kwargs):
        closing.set()
        return shutdown(**kwargs)

    monkeypatch.setattr(pool._executor, "shutdown", observed_shutdown)

    def close():
        pool.close()
        closed.set()

    thread = threading.Thread(target=close)
    thread.start()
    try:
        assert closing.wait(3) and not closed.is_set()
        with pytest.raises(BusyError):
            pool.submit(lambda: None)
    finally:
        release.set()
        thread.join(5)
    assert closed.is_set() and future.done()
