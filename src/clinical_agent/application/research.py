"""One compiled LangGraph, with request-local state and injected external ports."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import TYPE_CHECKING, Protocol

from clinical_agent.application.agents import (
    EvidenceReviewerAgent,
    IdeaPlannerAgent,
    LiteratureScoutAgent,
    MethodsAnalystAgent,
    PriorArtGapAnalystAgent,
    ResearchDesignAgent,
    RetrievalPort,
)
from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.openalex import OpenAlexRetrievalService, log_evidence_trace
from clinical_agent.application.pico import PicoPlanner, log_extraction_rejection
from clinical_agent.application.pubmed import PubMedRetrievalService
from clinical_agent.application.report import ReportBuilder
from clinical_agent.application.workflow import WorkflowState as State
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.report import ReportResult, ResearchReport, render_report
from clinical_agent.domain.research import (
    GenerationEvidence,
    GenerationInput,
    QuestionRequest,
    ResearchAnswer,
    ResearchError,
    ResearchLimits,
)
from clinical_agent.domain.retrieval import RetrievalError

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


class AnswerGenerator(Protocol):
    def generate(self, context: GenerationInput, *, timeout_seconds: float) -> str: ...


class ResearchService:
    def __init__(
        self,
        *,
        retriever: RetrievalPort,
        generator: AnswerGenerator,
        limits: ResearchLimits | None = None,
        planner: PicoPlanner | None = None,
        max_feedback_rounds: int = 1,
        analyzer: EvidenceAnalyzer | None = None,
        reporter: ReportBuilder | None = None,
        online_retriever: PubMedRetrievalService | OpenAlexRetrievalService | None = None,
        fulltext=None,
        clock: Callable[[], float] = monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        from langgraph.graph import END, START, StateGraph

        if type(max_feedback_rounds) is not int or not 0 <= max_feedback_rounds <= 2:
            raise ValueError("Feedback rounds must be an integer from 0 to 2")
        self._fulltext = fulltext
        self._max_feedback_rounds = max_feedback_rounds
        self._methods_agent = MethodsAnalystAgent(analyzer, clock=clock) if analyzer else None
        self._prior_agent = PriorArtGapAnalystAgent(clock=clock)
        self._design_agent = ResearchDesignAgent(clock=clock)
        self._review_agent = EvidenceReviewerAgent(reporter, clock=clock) if reporter else None
        self._retriever, self._generator = retriever, generator
        self._reporter = reporter
        self._analyzer = analyzer
        self._planner = planner
        self._online_retriever = online_retriever
        self._limits = ResearchLimits.model_validate(limits or ResearchLimits())
        self._clock, self._now = clock, now
        self._idea_agent = IdeaPlannerAgent(planner, clock=clock) if planner is not None else None
        self._scout_agent = LiteratureScoutAgent(retriever, online=online_retriever, clock=clock)
        graph = StateGraph(State)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("prepare", self._prepare)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("empty", self._empty)
        graph.add_node("analyze", self._analyze)
        graph.add_node("report", self._report)
        graph.add_node("prior_art", self._prior_agent)
        graph.add_node("design", self._design_agent)
        graph.add_node("feedback", self._feedback)
        graph.add_edge("analyze", "prior_art")
        graph.add_conditional_edges(
            "prior_art",
            lambda state: "design" if state.get("report_requested") else "end",
            {"design": "design", "end": END},
        )
        graph.add_edge("design", "report")
        graph.add_conditional_edges(
            "report", self._feedback_route, {"feedback": "feedback", "end": END}
        )
        graph.add_conditional_edges(
            "feedback",
            lambda state: state["feedback_history"][-1]["target"],
            {"methods": "analyze", "scout": "retrieve"},
        )
        if planner is not None:
            graph.add_node("plan", self._plan)
            graph.add_node("clarify", self._clarify)
            graph.add_edge(START, "plan")
            graph.add_conditional_edges(
                "plan", self._plan_route, {"retrieve": "retrieve", "clarify": "clarify"}
            )
            graph.add_conditional_edges(
                "clarify",
                lambda state: "report" if state.get("report_requested") else "end",
                {"report": "report", "end": END},
            )
        else:
            graph.add_edge(START, "retrieve")
        graph.add_conditional_edges(
            "retrieve", self._route, {"empty": "empty", "prepare": "prepare", "analyze": "analyze"}
        )
        graph.add_edge("prepare", "generate")
        graph.add_edge("generate", "validate")
        graph.add_edge("validate", END)
        graph.add_edge("empty", END)
        self._graph: CompiledStateGraph[State, None, State, State] = graph.compile()

    def _plan(self, state: State) -> dict[str, object]:
        assert self._idea_agent is not None
        patch = dict(self._idea_agent(state))
        if state.get("auto_route"):
            plan = patch["query_plan"]
            if plan.task_intent is None:
                log_extraction_rejection(
                    stage="route",
                    failure_kind="task_intent_required",
                    rule_code="task_intent_required",
                    field_paths="task_intent",
                )
                raise ResearchError("extraction_failed")
            if (
                plan.task_intent == "feasibility"
                and plan.structured_question.extraction_status != "needs_clarification"
            ):
                patch.update(analysis_requested=True, report_requested=True)
        return patch

    def _plan_route(self, state: State) -> str:
        return (
            "clarify"
            if state["query_plan"].structured_question.extraction_status == "needs_clarification"
            else "retrieve"
        )

    def _clarify(self, state: State) -> dict[str, object]:
        self._remaining(state)
        if state.get("analysis_requested"):
            return {
                "analysis": AnalysisResult(
                    request_id=state["request"].request_id,
                    original_idea=state["request"].question,
                    query_plan=state["query_plan"],
                    analysis_status="needs_clarification",
                    analysis_scope="No retrieval performed",
                    limitations=["Clarify the research idea first."],
                    unresolved_questions=(
                        state["query_plan"].structured_question.blocking_ambiguities
                        or state["query_plan"].structured_question.ambiguities
                    ),
                    sources=[],
                    retrieval=None,
                    generated_at=self._now(),
                    studies=[],
                    idea_similarities=[],
                    candidate_gaps=[],
                    comparisons=[],
                )
            }
        return {
            "answer": ResearchAnswer(
                request_id=state["request"].request_id,
                status="needs_clarification",
                query_plan=state["query_plan"],
                retrieval_scope=state["request"].scope,
                claims=[],
                sources=[],
                limitations=["问题需要澄清，本次尚未检索或生成医学结论。"],
                generated_at=self._now(),
            )
        }

    def _remaining(self, state: State) -> float:
        remaining = state["deadline"] - self._clock()
        if remaining <= 0:
            raise ResearchError("research_timeout")
        return remaining

    def _retrieve(self, state: State) -> dict[str, object]:
        patch = dict(self._scout_agent(state))
        if state.get("analysis_requested"):
            log_evidence_trace(
                stage="fulltext",
                counts={"calls": 0},
                failure_kind="not_requested",
                request_id=str(state["request"].request_id),
            )
        if self._fulltext is not None and not state.get("analysis_requested"):
            try:
                patch["retrieval"] = self._fulltext.enrich(
                    state["request"].question,
                    patch["retrieval"],
                    deadline=min(state["deadline"] - 25.0, self._clock() + 35.0),
                )
            except Exception:
                patch["retrieval"].warnings.append("fulltext_unavailable")
        return patch

    def _route(self, state: State) -> str:
        if state.get("analysis_requested"):
            return "analyze"
        return "prepare" if state["retrieval"].hits else "empty"

    def _prepare(self, state: State) -> dict[str, object]:
        self._remaining(state)
        from clinical_agent.domain.openalex import OpenAlexProvenance

        provenance = state["retrieval"].search_provenance
        evidence_groups = {}
        study_roles = {}
        if isinstance(provenance, OpenAlexProvenance):
            by_identity = {
                (
                    h.document.openalex_record.openalex_id
                    if h.document.openalex_record
                    else str(h.document.document_id)
                ): h.chunk.chunk_id
                for h in state["retrieval"].hits
            }
            for assessment in provenance.assessments:
                if assessment.id in by_identity:
                    study_roles[by_identity[assessment.id]] = assessment.study_role
                    for dimension in assessment.covered_dimensions:
                        evidence_groups.setdefault(dimension, []).append(by_identity[assessment.id])
            # Raw snapshots belong to audit/citations, not to the model context.
            provenance = provenance.model_copy(
                update={
                    "records": [],
                    "assessments": [],
                    "query_rounds": [],
                    "candidate_outcomes": {},
                }
            )
        context = GenerationInput(
            evidence_groups=evidence_groups,
            query_plan=state.get("query_plan"),
            search_provenance=provenance,
            question=state["request"].question,
            evidence=[
                GenerationEvidence(
                    study_role=study_roles.get(h.chunk.chunk_id, "other"),
                    fulltext=h.fulltext,
                    title=h.document.title,
                    pmid=h.document.pmid,
                    chunk_id=h.chunk.chunk_id,
                    text=h.chunk.text,
                    location=h.chunk.location,
                    content_scope=h.document.content_scope,
                )
                for h in state["retrieval"].hits
            ],
        )
        while len(context.model_dump_json()) > self._limits.max_context_characters:
            item = max(
                (e for e in context.evidence if e.fulltext),
                key=lambda e: len(e.fulltext),
                default=None,
            )
            if item is None:
                raise ResearchError("context_limit")
            removed = item.fulltext.pop()
            for hit in state["retrieval"].hits:
                hit.fulltext = [p for p in hit.fulltext if p.chunk_id != removed.chunk_id]
            state["retrieval"].warnings.append("fulltext_context_trimmed")
        return {"context": context}

    def _generate(self, state: State) -> dict[str, object]:
        remaining = min(self._remaining(state), self._limits.generation_seconds)
        try:
            raw = self._generator.generate(
                state["context"].model_copy(deep=True), timeout_seconds=remaining
            )
        except ResearchError as error:
            raise ResearchError(error.code) from None
        except Exception:
            raise ResearchError("generation_failed") from None
        self._remaining(state)
        return {"draft": parse_draft(raw, max_bytes=self._limits.max_output_bytes)}

    def _validate(self, state: State) -> dict[str, object]:
        self._remaining(state)
        return {
            "answer": build_answer(
                state["request"], state["retrieval"], state["draft"], generated_at=self._now()
            )
        }

    def _empty(self, state: State) -> dict[str, object]:
        self._remaining(state)
        return {
            "answer": build_answer(
                state["request"], state["retrieval"], None, generated_at=self._now()
            )
        }

    def _analyze(self, state: State) -> dict[str, object]:
        if self._methods_agent is None:
            raise ResearchError("generation_failed")
        return self._methods_agent(state)

    def _report(self, state: State) -> dict[str, object]:
        if self._review_agent is None:
            raise ResearchError("generation_failed")
        return self._review_agent(state)

    def _feedback_route(self, state: State) -> str:
        report = state["report"]
        target = EvidenceReviewerAgent.feedback(state)
        exhausted = state.get("feedback_rounds", 0) >= self._max_feedback_rounds
        if target != "stop" and exhausted and report.status != "rejected":
            report.status = "verification_incomplete"
        report.feedback_history = list(state.get("feedback_history", []))
        report.feedback_stop = (
            "round_limit" if target != "stop" and exhausted else "no_actionable_feedback"
        )
        if target == "stop" or exhausted or report.content_status == "needs_clarification":
            return "end"
        self._remaining(state)
        return "feedback"

    def _feedback(self, state: State) -> dict[str, object]:
        self._remaining(state)
        target = EvidenceReviewerAgent.feedback(state)
        return {
            "feedback_rounds": state.get("feedback_rounds", 0) + 1,
            "feedback_history": [
                *state.get("feedback_history", []),
                {"target": target, "reason": "evidence_review"},
            ],
            "research_designs": [],
        }

    def respond(self, request: QuestionRequest) -> ResearchAnswer | ResearchReport:
        """Route natural language within one graph run and one planning budget."""
        from langsmith import tracing_context

        if self._planner is None:
            raise ValueError("Natural-language routing requires a planner")
        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        state: State = {
            "request": request,
            "deadline": self._clock() + self._limits.max_seconds,
            "started_at": self._now(),
            "auto_route": True,
        }
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(
                    state,
                    config={"recursion_limit": 12 + 8 * self._max_feedback_rounds, "callbacks": []},
                )
                self._remaining(state)
                if output.get("report_requested"):
                    return ResearchReport.model_validate(output["report"])
                answer = output["answer"].model_dump()
                answer["query_plan"] = output["query_plan"]
                return ResearchAnswer.model_validate(answer)
            except (RetrievalError, ResearchError):
                raise
            except Exception:
                raise ResearchError("research_failed") from None

    def report(self, request: QuestionRequest) -> ReportResult:
        from langsmith import tracing_context

        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        state: State = {
            "request": request,
            "deadline": self._clock() + self._limits.max_seconds,
            "analysis_requested": True,
            "report_requested": True,
            "started_at": self._now(),
        }
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(
                    state,
                    config={"recursion_limit": 12 + 8 * self._max_feedback_rounds, "callbacks": []},
                )
                self._remaining(state)
                report = ResearchReport.model_validate(output["report"])
                return ReportResult(report=report, markdown=render_report(report))
            except (RetrievalError, ResearchError):
                raise
            except Exception:
                raise ResearchError("research_failed") from None

    def analyze(self, request: QuestionRequest) -> AnalysisResult:
        """Use the existing graph with an explicit Phase 6 branch."""
        from langsmith import tracing_context

        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        state: State = {
            "request": request,
            "deadline": self._clock() + self._limits.max_seconds,
            "analysis_requested": True,
        }
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(
                    state,
                    config={"recursion_limit": 12 + 8 * self._max_feedback_rounds, "callbacks": []},
                )
                self._remaining(state)
                return AnalysisResult.model_validate(output["analysis"])
            except (RetrievalError, ResearchError):
                raise
            except Exception:
                raise ResearchError("research_failed") from None

    def answer(self, request: QuestionRequest) -> ResearchAnswer:
        from langsmith import tracing_context

        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        state: State = {"request": request, "deadline": self._clock() + self._limits.max_seconds}
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(
                    state,
                    config={"recursion_limit": 12 + 8 * self._max_feedback_rounds, "callbacks": []},
                )
                self._remaining(state)
                answer = output["answer"].model_dump()
                if "query_plan" in output:
                    answer["query_plan"] = output["query_plan"]
                return ResearchAnswer.model_validate(answer)
            except RetrievalError as error:
                raise RetrievalError(error.code) from None
            except ResearchError as error:
                raise ResearchError(error.code) from None
            except Exception:
                raise ResearchError("research_failed") from None
