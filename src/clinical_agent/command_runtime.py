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
        from clinical_agent.adapters.postgres.versions import VersionedPostgresStore

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
    import httpx

    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.llm import RESPONSE_BYTE_LIMIT, LLMSettings, open_llm
    from clinical_agent.adapters.oa_fulltext import OAFulltextSource
    from clinical_agent.adapters.openalex import OpenAlexSettings, open_openalex
    from clinical_agent.adapters.pmc_fulltext import PMCSource
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService

    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    llm = cast(Callable[[], LLMSettings], LLMSettings)()
    model = LocalModelConfig(snapshot_dir=model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        postgres_retriever = PostgresRetriever(engine)
        retrieval = RetrievalService(
            embedder=embedder, retriever=postgres_retriever, hybrid_retriever=postgres_retriever
        )
        with (
            open_llm(llm) as generator,
            open_openalex() as openalex,
            httpx.Client(trust_env=False) as pmc_client,
        ):
            yield ResearchService(
                fulltext=FulltextService(
                    PMCSource(pmc_client),
                    PostgresFulltextStore(engine),
                    embedder,
                    oa_source=OAFulltextSource(pmc_client),
                    oa_store=PostgresFulltextStore(engine, openalex=True),
                ),
                retriever=retrieval,
                generator=generator,
                limits=limits,
                planner=PicoPlanner(extractor=generator),
                reporter=ReportBuilder(
                    reviewer=generator,
                    snapshots=SnapshotVerifier(),
                    metadata=None,
                    model_id=getattr(llm, "model", None),
                ),
                analyzer=EvidenceAnalyzer(
                    model=generator,
                    model_id=getattr(llm, "model", None),
                    timeout_seconds=180,
                    limits=ResearchLimits(generation_seconds=180),
                    analysis_max_tokens=getattr(llm, "analysis_max_tokens", 16384),
                    analysis_retry_max_tokens=getattr(llm, "analysis_retry_max_tokens", 32768),
                    max_output_bytes=RESPONSE_BYTE_LIMIT,
                ),
                online_retriever=OpenAlexRetrievalService(
                    openalex, generator, recent_months=OpenAlexSettings().recent_months
                ),
            )
