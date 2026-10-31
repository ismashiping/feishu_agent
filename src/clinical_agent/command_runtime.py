"""Explicit CLI composition; optional libraries are imported only on context entry."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol, cast

from pydantic import Field

from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.chunking import ChunkingPolicy
from clinical_agent.domain.ingestion import BatchIngestionResult, ImportRequest
from clinical_agent.domain.models import DTO
from clinical_agent.domain.report import ReportResult, ResearchReport
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer, ResearchLimits


class IngestionCommand(DTO):
    chunk_max_tokens: int = Field(default=512, strict=True, ge=1, le=512)
    update_existing: bool = False
    model_dir: Path
    snapshot_dir: Path


class IngestionPort(Protocol):
    def ingest(self, request: ImportRequest) -> BatchIngestionResult: ...


class ResearchPort(Protocol):
    def respond(self, request: QuestionRequest) -> ResearchAnswer | ResearchReport: ...

    def report(self, request: QuestionRequest) -> "ReportResult": ...

    def analyze(self, request: QuestionRequest) -> "AnalysisResult": ...

    def answer(self, request: QuestionRequest) -> ResearchAnswer: ...


def _require(*names: str) -> None:
    for name in names:
        if find_spec(name) is None:
            raise ModuleNotFoundError("Required optional dependency is unavailable", name=name)


@contextmanager
def open_ingestion(options: IngestionCommand) -> Iterator[IngestionPort]:
    options = IngestionCommand.model_validate(options)
    _require("sqlalchemy", "psycopg", "pgvector", "sentence_transformers", "transformers", "torch")
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.db.connection import DatabaseSettings, database_engine
    from clinical_agent.db.store import PostgresStore
    from clinical_agent.rag.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.rag.offline import OfflineReader

    # BaseSettings fills required constructor fields from explicit process environment.
    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    model = LocalModelConfig(snapshot_dir=options.model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        from clinical_agent.db.versions import VersionedPostgresStore

        version_store = (
            VersionedPostgresStore(engine) if options.update_existing else PostgresStore(engine)
        )
        yield IngestionService(
            reader=OfflineReader(options.snapshot_dir),
            embedder=embedder,
            store=version_store,
            policy=ChunkingPolicy(max_tokens=options.chunk_max_tokens),
        )


@contextmanager
def open_research(
    model_dir: Path, *, limits: ResearchLimits | None = None
) -> Iterator[ResearchPort]:
    _require(
        "sqlalchemy",
        "psycopg",
        "pgvector",
        "sentence_transformers",
        "transformers",
        "torch",
        "langgraph",
        "langchain_core",
        "langchain_openai",
        "langsmith",
        "httpx",
        "llama_index",
    )
    from clinical_agent.db.connection import DatabaseSettings, database_engine
    from clinical_agent.integrations.llm import LLMSettings
    from clinical_agent.integrations.openalex import OpenAlexSettings
    from clinical_agent.rag.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.research_runtime import open_research_service

    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    llm = cast(Callable[[], LLMSettings], LLMSettings)()
    openalex_settings = OpenAlexSettings()
    embedder = load_local_embedder(LocalModelConfig(snapshot_dir=model_dir))
    with database_engine(database) as engine:
        with open_research_service(
            engine, embedder, llm, openalex_settings, limits=limits
        ) as research:
            yield research
