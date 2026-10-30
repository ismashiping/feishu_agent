"""First incremental roles: delegate proven planning and literature discovery."""

from collections.abc import Callable
from time import monotonic
from typing import Any, Protocol

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.openalex import OpenAlexRetrievalService
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.pubmed import PubMedRetrievalService, merge_sources
from clinical_agent.application.report import ReportBuilder
from clinical_agent.application.workflow import AgentPatch, AgentStep, WorkflowState
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.research import ResearchError
from clinical_agent.domain.retrieval import RetrievalError, RetrievalRequest, RetrievalResult


class RetrievalPort(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...


def remaining(state: WorkflowState, now: float) -> float:
    budget = state["deadline"] - now
    if budget <= 0:
        raise ResearchError("research_timeout")
    return budget


def steps(state: WorkflowState, step: AgentStep) -> list[AgentStep]:
    return [*state.get("agent_steps", []), step]


class IdeaPlannerAgent:
    """Owns understanding/search planning; existing planner owns provenance checks."""

    def __init__(self, planner: PicoPlanner, *, clock: Callable[[], float] = monotonic) -> None:
        self.planner, self.clock = planner, clock

    def __call__(self, state: WorkflowState) -> AgentPatch:
        started = self.clock()
        plan = self.planner.plan(
            ClassificationRequest(question=state["request"].question),
            timeout_seconds=remaining(state, started),
        )
        finished = self.clock()
        remaining(state, finished)
        return {
            "query_plan": plan,
            "agent_steps": steps(
                state, {"role": "idea_planner", "elapsed_seconds": finished - started}
            ),
        }


class LiteratureScoutAgent:
    """Owns source discovery; reuses local FTS/RRF and official PubMed modules."""

    def __init__(
        self,
        retriever: RetrievalPort,
        *,
        online: PubMedRetrievalService | OpenAlexRetrievalService | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.retriever, self.online, self.clock = retriever, online, clock

    def __call__(self, state: WorkflowState) -> AgentPatch:
        started = self.clock()
        remaining(state, started)
        request = state["request"]
        try:
            data = request.model_dump(exclude={"request_id"})
            if request.scope == "local":
                retrieval = self.retriever.retrieve(RetrievalRequest.model_validate(data))
            else:
                if self.online is None:
                    raise ResearchError("pubmed_failed")
                local = None
                if request.scope == "hybrid":
                    local = self.retriever.retrieve(
                        RetrievalRequest.model_validate(
                            {**data, "scope": "local", "pubmed": None, "openalex": None}
                        )
                    )
                if isinstance(self.online, OpenAlexRetrievalService):
                    retrieval = self.online.retrieve(
                        RetrievalRequest.model_validate(data),
                        query_plan=state.get("query_plan"),
                        timeout_seconds=remaining(state, self.clock()),
                        local=local,
                        request_id=str(request.request_id),
                    )
                else:
                    online = self.online.retrieve(
                        RetrievalRequest.model_validate(data),
                        query_plan=state.get("query_plan"),
                        timeout_seconds=remaining(state, self.clock()),
                    )
                    retrieval = (
                        merge_sources(local, online, state.get("query_plan"))
                        if local is not None
                        else online
                    )
            retrieval = RetrievalResult.model_validate(retrieval).model_copy(deep=True)
            if retrieval.options != request.options or retrieval.scope != request.scope:
                raise ValueError("Mismatched query options or source scope")
        except ResearchError as error:
            raise ResearchError(error.code) from None
        except RetrievalError as error:
            raise RetrievalError(error.code) from None
        except Exception:
            raise RetrievalError("retrieval_failed") from None
        finished = self.clock()
        remaining(state, finished)
        return {
            "retrieval": retrieval,
            "agent_steps": steps(
                state, {"role": "literature_scout", "elapsed_seconds": finished - started}
            ),
        }


class MethodsAnalystAgent:
    """Reuse the validated joint extraction; do not call another identical LLM."""

    def __init__(
        self, analyzer: EvidenceAnalyzer, *, clock: Callable[[], float] = monotonic
    ) -> None:
        self.analyzer, self.clock = analyzer, clock

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        started = self.clock()
        analysis = self.analyzer.analyze(
            state["request"],
            state["retrieval"],
            query_plan=state.get("query_plan"),
            timeout_seconds=remaining(state, started),
        )
        finished = self.clock()
        remaining(state, finished)
        return {
            "analysis": analysis,
            "agent_steps": steps(state, {"role": "methods", "elapsed_seconds": finished - started}),
        }


class PriorArtGapAnalystAgent:
    """Independent deterministic comparison/gap gate over the joint draft."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        from clinical_agent.domain.analysis import AnalysisResult

        started = self.clock()
        remaining(state, started)
        analysis = AnalysisResult.model_validate(state["analysis"].model_dump()).model_copy(
            deep=True
        )
        sources = {s.document_id: s for s in analysis.sources}
        chunks = {e.chunk_id: (s.document_id, e.text) for s in analysis.sources for e in s.evidence}
        for similarity in analysis.idea_similarities:
            if similarity.document_id not in sources:
                raise ResearchError("citation_invalid")
            for dimension in similarity.dimensions.values():
                if dimension.idea_quote and dimension.idea_quote not in analysis.original_idea:
                    raise ResearchError("citation_invalid")
                for ref in dimension.evidence:
                    if (
                        ref.chunk_id not in chunks
                        or chunks[ref.chunk_id][0] != similarity.document_id
                        or ref.quote not in chunks[ref.chunk_id][1]
                    ):
                        raise ResearchError("citation_invalid")
        for gap in analysis.candidate_gaps:
            for ref in gap.description.evidence + gap.counter_evidence:
                if ref.chunk_id not in chunks or ref.quote not in chunks[ref.chunk_id][1]:
                    raise ResearchError("citation_invalid")
        finished = self.clock()
        remaining(state, finished)
        return {
            "analysis": analysis,
            "agent_steps": steps(
                state, {"role": "prior_art", "elapsed_seconds": finished - started}
            ),
        }


class ResearchDesignAgent:
    """Conservative candidate plans; explicitly pending data/feasibility review."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        started = self.clock()
        remaining(state, started)
        designs = [
            {
                "candidate_gap_index": i,
                "hypothesis": gap.description.value,
                "epistemic_kind": "unverified_hypothesis",
                "scope": gap.scope,
                "evidence_chunk_ids": [str(p.chunk_id) for p in gap.description.evidence],
                "counter_evidence_chunk_ids": [str(p.chunk_id) for p in gap.counter_evidence],
                "verification_needed": gap.description.verification_needed,
                "data_and_methods": (
                    "待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。"
                ),
                "reference_method_profiles": [
                    {
                        "document_id": str(study.document_id),
                        "reported_options": {
                            name: study.fields[name].model_dump(mode="json")
                            for name in [
                                "design",
                                "data_sources",
                                "technical_methods",
                                "evaluation_metrics",
                            ]
                            if study.fields[name].value is not None
                        },
                    }
                    for study in state["analysis"].studies
                ],
            }
            for i, gap in enumerate(state["analysis"].candidate_gaps)
        ]
        finished = self.clock()
        remaining(state, finished)
        return {
            "research_designs": designs,
            "agent_steps": steps(
                state, {"role": "research_design", "elapsed_seconds": finished - started}
            ),
        }


class EvidenceReviewerAgent:
    def __init__(self, reporter: ReportBuilder, *, clock: Callable[[], float] = monotonic) -> None:
        self.reporter, self.clock = reporter, clock

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        started = self.clock()
        report = self.reporter.build(
            state["request"],
            state["analysis"],
            state.get("retrieval"),
            timeout_seconds=remaining(state, started),
            search_started_at=state.get("started_at"),
        )
        report.research_designs = state.get("research_designs", [])
        finished = self.clock()
        remaining(state, finished)
        return {
            "report": report,
            "agent_steps": steps(
                state, {"role": "evidence_reviewer", "elapsed_seconds": finished - started}
            ),
        }

    @staticmethod
    def feedback(state: WorkflowState) -> str:
        report = state["report"]
        if any(
            v.identity_status == "invalid"
            or v.location_status == "invalid"
            or v.metadata_status == "invalid"
            for v in report.verification
        ):
            return "stop"
        if any(c.support_status == "unsupported" for c in report.claims):
            return "methods"
        if report.content_status == "insufficient_evidence" or (
            report.analysis.retrieval
            and report.analysis.retrieval.search_provenance
            and report.analysis.retrieval.search_provenance.status == "partial"
        ):
            return "scout"
        return "stop"
