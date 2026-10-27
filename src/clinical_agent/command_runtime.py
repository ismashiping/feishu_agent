"""Explicit CLI composition; optional libraries are imported only on context entry."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol, cast

from clinical_agent.domain.ingestion import BatchIngestionResult, ImportRequest
from clinical_agent.domain.models import DTO
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer


class IngestionCommand(DTO):
    model_dir: Path
    snapshot_dir: Path


class IngestionPort(Protocol):
    def ingest(self, request: ImportRequest) -> BatchIngestionResult: ...


class ResearchPort(Protocol):
    def answer(self, request: QuestionRequest) -> ResearchAnswer: ...


def _require(*names: str) -> None:
    for name in names:
        if find_spec(name) is None:
            raise ModuleNotFoundError("Required optional dependency is unavailable", name=name)


@contextmanager
def open_ingestion(options: IngestionCommand) -> Iterator[IngestionPort]:
    options = IngestionCommand.model_validate(options)
    _require("sqlalchemy", "psycopg", "pgvector", "sentence_transformers", "transformers", "torch")
    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.application.ingestion import IngestionService

    # BaseSettings fills required constructor fields from explicit process environment.
    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    model = LocalModelConfig(snapshot_dir=options.model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        yield IngestionService(
            reader=OfflineReader(options.snapshot_dir),
            embedder=embedder,
            store=PostgresStore(engine),
        )


@contextmanager
def open_research(model_dir: Path) -> Iterator[ResearchPort]:
    _require(
        "sqlalchemy",
        "psycopg",
        "pgvector",
        "sentence_transformers",
        "transformers",
        "torch",
        "langgraph",
        "langsmith",
        "httpx",
    )
    from clinical_agent.adapters.deepseek import DeepSeekSettings, deepseek_generator
    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService

    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    llm = cast(Callable[[], DeepSeekSettings], DeepSeekSettings)()
    model = LocalModelConfig(snapshot_dir=model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        retrieval = RetrievalService(embedder=embedder, retriever=PostgresRetriever(engine))
        with deepseek_generator(llm) as generator:
            yield ResearchService(retriever=retrieval, generator=generator)
