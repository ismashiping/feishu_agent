"""One compiled LangGraph, with request-local state and injected external ports."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol, TypeVar

from clinical_agent.agents.graph import build_research_graph
from clinical_agent.agents.nodes import (
    EvidenceReviewerAgent,
    IdeaPlannerAgent,
    LiteratureScoutAgent,
    MethodsAnalystAgent,
    PriorArtGapAnalystAgent,
    ResearchDesignAgent,
    RetrievalPort,
)
from clinical_agent.agents.state import WorkflowState as State
from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.openalex import OpenAlexRetrievalService
from clinical_agent.application.pico import PicoPlanner, log_extraction_rejection
from clinical_agent.application.report import ReportBuilder
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.report import ReportResult, ResearchReport, render_report
from clinical_agent.domain.research import (
    INSTRUCTIONS,
    OPENALEX_FULLTEXT_INSTRUCTIONS,
    GenerationEvidence,
    GenerationInput,
    QuestionRequest,
    ResearchAnswer,
    ResearchError,
    ResearchLimits,
)
from clinical_agent.domain.retrieval import RetrievalError
from clinical_agent.logging_config import log_unexpected

T = TypeVar("T")


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
        online_retriever: OpenAlexRetrievalService | None = None,
        fulltext=None,
        clock: Callable[[], float] = monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
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
        self._graph = build_research_graph(self, with_planner=planner is not None)

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
        if self._fulltext is not None:
            try:
                patch["retrieval"] = self._fulltext.enrich(
                    state["request"].question,
                    patch["retrieval"],
                    deadline=min(state["deadline"] - 30.0, self._clock() + 60.0),
                )
            except Exception as error:
                # Degrades to insufficient_evidence; the cause must stay diagnosable.
                log_unexpected("fulltext", error)
                patch["retrieval"].warnings.append("fulltext_unavailable")
        return patch

    def _route(self, state: State) -> str:
        from clinical_agent.domain.openalex import OpenAlexProvenance

        if state.get("analysis_requested"):
            return "analyze"
        retrieval = state["retrieval"]
        if isinstance(retrieval.search_provenance, OpenAlexProvenance) and not any(
            hit.fulltext for hit in retrieval.hits
        ):
            return "empty"
        return "prepare" if retrieval.hits else "empty"

    def _prepare(self, state: State) -> dict[str, object]:
        self._remaining(state)
        from clinical_agent.domain.models import EvidenceLocation
        from clinical_agent.domain.openalex import OpenAlexProvenance

        retrieval = state["retrieval"].model_copy(deep=True)
        provenance = retrieval.search_provenance
        evidence_groups = {}
        study_roles = {}
        openalex = isinstance(provenance, OpenAlexProvenance)
        hits = [hit for hit in retrieval.hits if hit.fulltext] if openalex else retrieval.hits
        if openalex and not hits:
            raise ResearchError("research_failed")
        if openalex:
            by_identity = {
                (
                    h.document.openalex_record.openalex_id
                    if h.document.openalex_record
                    else str(h.document.document_id)
                ): h
                for h in hits
            }
            for assessment in provenance.assessments:
                hit = by_identity.get(assessment.id)
                if hit is None:
                    continue
                study_roles[hit.chunk.chunk_id] = assessment.study_role
                anchor = hit.fulltext[0].chunk_id
                for dimension in assessment.covered_dimensions:
                    evidence_groups.setdefault(dimension, []).append(anchor)
            # Raw snapshots belong to audit/citations, not to the model context.
            provenance = provenance.model_copy(
                update={
                    "records": [],
                    "assessments": [],
                    "query_rounds": [],
                    "candidate_outcomes": {},
                }
            )

        def generation_evidence(hit):
            if openalex:
                passage = hit.fulltext[0]
                return GenerationEvidence(
                    study_role=study_roles.get(hit.chunk.chunk_id, "other"),
                    fulltext=hit.fulltext,
                    title=hit.document.title,
                    pmid=hit.document.pmid,
                    chunk_id=passage.chunk_id,
                    text=passage.text,
                    location=EvidenceLocation(
                        kind="fulltext",
                        page=passage.page,
                        section=passage.section,
                        start=passage.start,
                        end=passage.end,
                    ),
                    content_scope="full_text",
                )
            return GenerationEvidence(
                study_role=study_roles.get(hit.chunk.chunk_id, "other"),
                fulltext=hit.fulltext,
                title=hit.document.title,
                pmid=hit.document.pmid,
                chunk_id=hit.chunk.chunk_id,
                text=hit.chunk.text,
                location=hit.chunk.location,
                content_scope=hit.document.content_scope,
            )

        context = GenerationInput(
            evidence_groups=evidence_groups,
            query_plan=state.get("query_plan"),
            search_provenance=provenance,
            question=state["request"].question,
            evidence=[generation_evidence(hit) for hit in hits],
            instructions=OPENALEX_FULLTEXT_INSTRUCTIONS if openalex else INSTRUCTIONS,
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
            # The anchor passage stays in context as item.text and stays citable.
            if removed.chunk_id != item.chunk_id:
                for hit in retrieval.hits:
                    hit.fulltext = [p for p in hit.fulltext if p.chunk_id != removed.chunk_id]
            retrieval.warnings.append("fulltext_context_trimmed")
        return {"context": context, "retrieval": retrieval}

    def _generate(self, state: State) -> dict[str, object]:
        remaining = min(self._remaining(state), self._limits.generation_seconds)
        try:
            raw = self._generator.generate(
                state["context"].model_copy(deep=True), timeout_seconds=remaining
            )
        except ResearchError as error:
            raise ResearchError(error.code) from None
        except Exception as error:
            log_unexpected("generate", error)
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
        """Build the report and decide the bounded feedback step in the node, not the router."""
        if self._review_agent is None:
            raise ResearchError("generation_failed")
        patch = self._review_agent(state)
        report = patch["report"]
        target = EvidenceReviewerAgent.feedback(report)
        exhausted = state.get("feedback_rounds", 0) >= self._max_feedback_rounds
        if target != "stop" and exhausted and report.status != "rejected":
            report.status = "verification_incomplete"
        report.feedback_history = list(state.get("feedback_history", []))
        report.feedback_stop = (
            "round_limit" if target != "stop" and exhausted else "no_actionable_feedback"
        )
        if target == "stop" or exhausted or report.content_status == "needs_clarification":
            patch["feedback_target"] = "stop"
        else:
            patch["feedback_target"] = target
        return patch

    def _feedback(self, state: State) -> dict[str, object]:
        self._remaining(state)
        return {
            "feedback_rounds": state.get("feedback_rounds", 0) + 1,
            "feedback_history": [
                *state.get("feedback_history", []),
                {"target": state["feedback_target"], "reason": "evidence_review"},
            ],
            "research_designs": [],
        }

    def _run(self, request: QuestionRequest, finish: Callable[[Any], T], **flags: bool) -> T:
        """Invoke the graph once under one deadline and convert unknown failures to a code."""
        from langsmith import tracing_context

        state: State = {
            "request": QuestionRequest.model_validate(request).model_copy(deep=True),
            "deadline": self._clock() + self._limits.max_seconds,
            "started_at": self._now(),
            **flags,  # type: ignore[typeddict-item]
        }
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(
                    state,
                    config={"recursion_limit": 12 + 8 * self._max_feedback_rounds, "callbacks": []},
                )
                self._remaining(state)
                return finish(output)
            # Re-raise clean copies: LangGraph attaches task notes to node exceptions.
            except RetrievalError as error:
                raise RetrievalError(error.code) from None
            except ResearchError as error:
                raise ResearchError(error.code, error.details) from None
            except Exception as error:
                log_unexpected("graph", error)
                raise ResearchError("research_failed") from None

    @staticmethod
    def _answer_output(output: Any) -> ResearchAnswer:
        answer = output["answer"].model_dump()
        if "query_plan" in output:
            answer["query_plan"] = output["query_plan"]
        return ResearchAnswer.model_validate(answer)

    def respond(self, request: QuestionRequest) -> ResearchAnswer | ResearchReport:
        """Route natural language within one graph run and one planning budget."""
        if self._planner is None:
            raise ValueError("Natural-language routing requires a planner")

        def finish(output: Any) -> ResearchAnswer | ResearchReport:
            if output.get("report_requested"):
                return ResearchReport.model_validate(output["report"])
            return self._answer_output(output)

        return self._run(request, finish, auto_route=True)

    def report(self, request: QuestionRequest) -> ReportResult:
        def finish(output: Any) -> ReportResult:
            report = ResearchReport.model_validate(output["report"])
            return ReportResult(report=report, markdown=render_report(report))

        return self._run(request, finish, analysis_requested=True, report_requested=True)

    def analyze(self, request: QuestionRequest) -> AnalysisResult:
        return self._run(
            request,
            lambda output: AnalysisResult.model_validate(output["analysis"]),
            analysis_requested=True,
        )

    def answer(self, request: QuestionRequest) -> ResearchAnswer:
        return self._run(request, self._answer_output)
