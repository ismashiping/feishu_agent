"""Command assembly uses real services and bounded injected resource managers."""

from contextlib import contextmanager
from pathlib import Path

import pytest


def patch_components(monkeypatch):
    from clinical_agent.adapters import embedding
    from clinical_agent.adapters.postgres import connection

    events = []

    def config():
        events.append("db-config")
        return object()

    def model(config):
        events.append(("model", config.snapshot_dir))
        return object()

    @contextmanager
    def engine(config):
        events.append("engine-enter")
        try:
            yield object()
        finally:
            events.append("engine-exit")

    monkeypatch.setattr(connection, "DatabaseSettings", config)
    monkeypatch.setattr(connection, "database_engine", engine)
    monkeypatch.setattr(embedding, "load_local_embedder", model)
    return events


def test_ingestion_assembly_has_no_llm(monkeypatch):
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.command_runtime import IngestionCommand, open_ingestion

    events = patch_components(monkeypatch)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with open_ingestion(
        IngestionCommand(model_dir=Path("model"), snapshot_dir=Path("snapshots"))
    ) as service:
        assert isinstance(service, IngestionService)
        assert service._reader._directory == Path("snapshots")
    assert events == ["db-config", ("model", Path("model")), "engine-enter", "engine-exit"]


@pytest.mark.parametrize("fail", [False, True])
def test_research_assembly_closes_http_before_engine(monkeypatch, fail):
    from clinical_agent.adapters import llm as llm_api
    from clinical_agent.application.research import ResearchService
    from clinical_agent.command_runtime import open_research

    events = patch_components(monkeypatch)

    def settings():
        events.append("llm-config")
        return object()

    @contextmanager
    def http(config):
        events.append("http-enter")
        try:
            yield object()
        finally:
            events.append("http-exit")

    monkeypatch.setattr(llm_api, "LLMSettings", settings)
    monkeypatch.setattr(llm_api, "open_llm", http)
    with pytest.raises(RuntimeError) if fail else __import__("contextlib").nullcontext():
        with open_research(Path("model")) as service:
            assert isinstance(service, ResearchService)
            assert service._planner is not None
            if fail:
                raise RuntimeError("request failed")
    assert events == [
        "db-config",
        "llm-config",
        ("model", Path("model")),
        "engine-enter",
        "http-enter",
        "http-exit",
        "engine-exit",
    ]


def test_configuration_failure_precedes_model_loading(monkeypatch):
    from clinical_agent.adapters import llm as llm_api
    from clinical_agent.command_runtime import open_research

    events = patch_components(monkeypatch)

    def settings():
        raise ValueError("invalid config")

    monkeypatch.setattr(llm_api, "LLMSettings", settings)
    with pytest.raises(ValueError):
        with open_research(Path("model")):
            pytest.fail("Must not enter")
    assert events == ["db-config"]
