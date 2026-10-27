"""One compiled LangGraph, with request-local state and injected external ports."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import TYPE_CHECKING, NotRequired, Protocol, TypedDict

from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.research import (
    GenerationDraft,
    GenerationEvidence,
    GenerationInput,
    QuestionRequest,
    ResearchAnswer,
    ResearchError,
    ResearchLimits,
)
from clinical_agent.domain.retrieval import RetrievalError, RetrievalRequest, RetrievalResult

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


class RetrievalPort(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...


class AnswerGenerator(Protocol):
    def generate(self, context: GenerationInput, *, timeout_seconds: float) -> str: ...


class State(TypedDict):
    request: QuestionRequest
    deadline: float
    retrieval: NotRequired[RetrievalResult]
    context: NotRequired[GenerationInput]
    draft: NotRequired[GenerationDraft]
    answer: NotRequired[ResearchAnswer]


class ResearchService:
    def __init__(
        self,
        *,
        retriever: RetrievalPort,
        generator: AnswerGenerator,
        limits: ResearchLimits | None = None,
        clock: Callable[[], float] = monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        from langgraph.graph import END, START, StateGraph

        self._retriever, self._generator = retriever, generator
        self._limits = ResearchLimits.model_validate(limits or ResearchLimits())
        self._clock, self._now = clock, now
        graph = StateGraph(State)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("prepare", self._prepare)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("empty", self._empty)
        graph.add_edge(START, "retrieve")
        graph.add_conditional_edges(
            "retrieve", self._route, {"empty": "empty", "prepare": "prepare"}
        )
        graph.add_edge("prepare", "generate")
        graph.add_edge("generate", "validate")
        graph.add_edge("validate", END)
        graph.add_edge("empty", END)
        self._graph: CompiledStateGraph[State, None, State, State] = graph.compile()

    def _remaining(self, state: State) -> float:
        remaining = state["deadline"] - self._clock()
        if remaining <= 0:
            raise ResearchError("research_timeout")
        return remaining

    def _retrieve(self, state: State) -> dict[str, object]:
        self._remaining(state)
        request = state["request"]
        try:
            retrieval = self._retriever.retrieve(
                RetrievalRequest.model_validate(request.model_dump(exclude={"request_id"}))
            )
            retrieval = RetrievalResult.model_validate(retrieval).model_copy(deep=True)
            if retrieval.options != request.options:
                raise ValueError("Mismatched query options")
        except RetrievalError as error:
            raise RetrievalError(error.code) from None
        except Exception:
            raise RetrievalError("retrieval_failed") from None
        self._remaining(state)
        return {"retrieval": retrieval}

    def _route(self, state: State) -> str:
        return "prepare" if state["retrieval"].hits else "empty"

    def _prepare(self, state: State) -> dict[str, object]:
        self._remaining(state)
        context = GenerationInput(
            question=state["request"].question,
            evidence=[
                GenerationEvidence(
                    chunk_id=h.chunk.chunk_id,
                    text=h.chunk.text,
                    location=h.chunk.location,
                    content_scope=h.document.content_scope,
                )
                for h in state["retrieval"].hits
            ],
        )
        if len(context.model_dump_json()) > self._limits.max_context_characters:
            raise ResearchError("context_limit")
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

    def answer(self, request: QuestionRequest) -> ResearchAnswer:
        from langsmith import tracing_context

        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        state: State = {"request": request, "deadline": self._clock() + self._limits.max_seconds}
        with tracing_context(enabled=False):
            try:
                output = self._graph.invoke(state, config={"recursion_limit": 8, "callbacks": []})
                self._remaining(state)
                return ResearchAnswer.model_validate(output["answer"])
            except RetrievalError as error:
                raise RetrievalError(error.code) from None
            except ResearchError as error:
                raise ResearchError(error.code) from None
            except Exception:
                raise ResearchError("research_failed") from None
