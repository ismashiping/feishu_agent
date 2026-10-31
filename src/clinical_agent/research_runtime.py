"""Shared research composition for API, CLI and Feishu; owns HTTP resources only."""

from contextlib import contextmanager

from clinical_agent.domain.research import ResearchLimits


@contextmanager
def open_research_service(engine, embedder, llm, openalex_settings, *, limits=None):
    import httpx

    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService
    from clinical_agent.db.fulltext import PostgresFulltextStore
    from clinical_agent.integrations.llm import RESPONSE_BYTE_LIMIT, open_llm
    from clinical_agent.integrations.oa_fulltext import OAFulltextSource
    from clinical_agent.integrations.openalex import open_openalex
    from clinical_agent.integrations.report_snapshot import SnapshotVerifier

    with (
        open_llm(llm) as generator,
        open_openalex() as openalex,
        httpx.Client(trust_env=False) as fulltext_client,
    ):
        yield ResearchService(
            fulltext=FulltextService(
                OAFulltextSource(
                    fulltext_client,
                    api_key=openalex_settings.api_key.get_secret_value()
                    if openalex_settings.api_key
                    else None,
                ),
                PostgresFulltextStore(engine, openalex=True),
                embedder,
            ),
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
                openalex, generator, recent_months=openalex_settings.recent_months
            ),
        )
