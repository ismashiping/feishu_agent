"""API contracts, bounded standard worker pool and explicit shared resource ownership."""

from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Annotated, Literal, TypeVar, cast
from uuid import UUID

from pydantic import DirectoryPath, Field, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.command_runtime import IngestionPort, ResearchPort
from clinical_agent.domain.ingestion import BatchIngestionResult
from clinical_agent.domain.models import DTO
from clinical_agent.domain.retrieval import RetrievalRequest

T = TypeVar("T")


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINICAL_AGENT_API_",
        env_file=None,
        hide_input_in_errors=True,
        extra="forbid",
        revalidate_instances="always",
    )
    model_dir: DirectoryPath
    import_root: DirectoryPath
    snapshot_dir: Path
    max_in_flight: Annotated[int, Field(strict=True, ge=1, le=4)] = 2
    max_request_bytes: Annotated[int, Field(strict=True, ge=1, le=65536)] = 16384

    @field_validator("max_in_flight", "max_request_bytes", mode="before")
    @classmethod
    def parse_environment_integer(cls, value: object) -> object:
        return (
            int(value)
            if isinstance(value, str) and value.isascii() and value.isdecimal()
            else value
        )


class ImportBody(DTO):
    source_type: Literal["pdf", "pubmed_xml"]
    relative_path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if (
            value.startswith("/")
            or any(char in value for char in ("\\", ":", "\0"))
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ValueError("Only bounded relative source paths are accepted")
        return value


class QuestionBody(RetrievalRequest):
    scope: Literal["local", "online", "hybrid"] = "hybrid"


class ImportResponse(DTO):
    request_id: UUID
    result: BatchIngestionResult


class ApiError(DTO):
    request_id: UUID
    error_code: str
    message: str
    retryable: bool


class HealthReport(DTO):
    request_id: UUID
    status: Literal["ok", "not_ready"]
    scope: Literal["process", "runtime"]


@dataclass(frozen=True)
class ServiceBundle:
    ingestion: IngestionPort
    research: ResearchPort


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


@contextmanager
def open_api_runtime(settings: ApiSettings) -> Iterator[ServiceBundle]:
    settings = ApiSettings.model_validate(settings)
    for name in (
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
    ):
        if find_spec(name) is None:
            raise ModuleNotFoundError("Optional dependency unavailable", name=name)
    import httpx

    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.llm import RESPONSE_BYTE_LIMIT, LLMSettings, open_llm
    from clinical_agent.adapters.oa_fulltext import OAFulltextSource
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.openalex import OpenAlexSettings, open_openalex
    from clinical_agent.adapters.pmc_fulltext import PMCSource
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.research import ResearchLimits

    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    llm = cast(Callable[[], LLMSettings], LLMSettings)()
    model = LocalModelConfig(snapshot_dir=settings.model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        ingestion = IngestionService(
            reader=OfflineReader(settings.snapshot_dir),
            embedder=embedder,
            store=PostgresStore(engine),
        )
        postgres_retriever = PostgresRetriever(engine)
        retrieval = RetrievalService(
            embedder=embedder, retriever=postgres_retriever, hybrid_retriever=postgres_retriever
        )
        with (
            open_llm(llm) as generator,
            open_openalex() as openalex,
            httpx.Client(trust_env=False) as pmc_client,
        ):
            yield ServiceBundle(
                ingestion=ingestion,
                research=ResearchService(
                    fulltext=FulltextService(
                        PMCSource(pmc_client),
                        PostgresFulltextStore(engine),
                        embedder,
                        oa_source=OAFulltextSource(pmc_client),
                        oa_store=PostgresFulltextStore(engine, openalex=True),
                    ),
                    retriever=retrieval,
                    generator=generator,
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
                ),
            )
