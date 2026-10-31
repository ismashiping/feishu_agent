"""API resource composition; legacy contracts and execution imports stay available."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import find_spec
from typing import cast

from clinical_agent.api.schemas import ApiSettings
from clinical_agent.command_runtime import IngestionPort, ResearchPort


@dataclass(frozen=True)
class ServiceBundle:
    ingestion: IngestionPort
    research: ResearchPort


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
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.db.connection import DatabaseSettings, database_engine
    from clinical_agent.db.store import PostgresStore
    from clinical_agent.integrations.llm import LLMSettings
    from clinical_agent.integrations.openalex import OpenAlexSettings
    from clinical_agent.rag.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.rag.offline import OfflineReader
    from clinical_agent.research_runtime import open_research_service

    database = cast(Callable[[], DatabaseSettings], DatabaseSettings)()
    llm = cast(Callable[[], LLMSettings], LLMSettings)()
    openalex_settings = OpenAlexSettings()
    model = LocalModelConfig(snapshot_dir=settings.model_dir)
    embedder = load_local_embedder(model)
    with database_engine(database) as engine:
        ingestion = IngestionService(
            reader=OfflineReader(settings.snapshot_dir),
            embedder=embedder,
            store=PostgresStore(engine),
        )
        with open_research_service(engine, embedder, llm, openalex_settings) as research:
            yield ServiceBundle(ingestion=ingestion, research=research)
