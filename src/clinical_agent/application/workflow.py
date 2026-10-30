"""Request-local shared state; roles return patches, never global conversation state."""

from datetime import datetime
from typing import Literal, NotRequired, TypedDict

from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.report import ResearchReport
from clinical_agent.domain.research import (
    GenerationDraft,
    GenerationInput,
    QuestionRequest,
    ResearchAnswer,
)
from clinical_agent.domain.retrieval import RetrievalResult


class AgentStep(TypedDict):
    role: Literal[
        "idea_planner",
        "literature_scout",
        "methods",
        "prior_art",
        "research_design",
        "evidence_reviewer",
    ]
    elapsed_seconds: float


class WorkflowState(TypedDict):
    auto_route: NotRequired[bool]
    feedback_rounds: NotRequired[int]
    feedback_history: NotRequired[list[dict[str, str]]]
    research_designs: NotRequired[list[dict[str, object]]]
    agent_steps: NotRequired[list[AgentStep]]
    report_requested: NotRequired[bool]
    report: NotRequired[ResearchReport]
    started_at: NotRequired[datetime]
    analysis_requested: NotRequired[bool]
    analysis: NotRequired[AnalysisResult]
    request: QuestionRequest
    deadline: float
    query_plan: NotRequired[QueryPlan]
    retrieval: NotRequired[RetrievalResult]
    context: NotRequired[GenerationInput]
    draft: NotRequired[GenerationDraft]
    answer: NotRequired[ResearchAnswer]


class AgentPatch(TypedDict, total=False):
    query_plan: QueryPlan
    retrieval: RetrievalResult
    agent_steps: list[AgentStep]
