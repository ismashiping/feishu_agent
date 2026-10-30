"""One bounded extraction call, then deterministic provenance validation and planning."""

import json
import math
from collections.abc import Callable
from time import monotonic
from typing import Protocol

from clinical_agent.domain.pico import (
    ClassificationRequest,
    ExtractedField,
    ExtractionDraft,
    QueryPlan,
    SourceSpan,
    StructuredQuestion,
)
from clinical_agent.domain.research import ResearchCode, ResearchError


class PicoExtractor(Protocol):
    def extract(self, request: ClassificationRequest, *, timeout_seconds: float) -> str: ...


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("Non-JSON constant")


class PicoPlanner:
    def __init__(
        self,
        *,
        extractor: PicoExtractor,
        max_seconds: float = 20.0,
        max_output_bytes: int = 32000,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not math.isfinite(max_seconds) or max_seconds <= 0 or max_output_bytes <= 0:
            raise ValueError("Invalid extraction budget")
        self._extractor, self._clock = extractor, clock
        self._max_seconds, self._max_output_bytes = max_seconds, max_output_bytes

    def plan(self, request: ClassificationRequest, *, timeout_seconds: float = 20.0) -> QueryPlan:
        request = ClassificationRequest.model_validate(request).model_copy(deep=True)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("extraction_timeout")
        budget = min(timeout_seconds, self._max_seconds)
        deadline = self._clock() + budget
        try:
            raw = self._extractor.extract(request.model_copy(deep=True), timeout_seconds=budget)
            if self._clock() >= deadline:
                raise ResearchError("extraction_timeout")
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > self._max_output_bytes:
                raise ValueError("Invalid extraction output size")
            data = json.loads(raw, object_pairs_hook=_unique, parse_constant=_invalid_constant)
            draft = ExtractionDraft.model_validate(data)
            status = "complete" if len(draft.pico.fields()) == 4 else "partial"
            blocking = draft.blocking_ambiguities
            if blocking == [] and not (
                draft.pico.fields() or any(term.origin == "user_text" for term in draft.terms)
            ):
                blocking = ["请提供希望检索的具体研究主题。"]
            if blocking or (
                blocking is None and draft.question_type == "uncertain" and draft.ambiguities
            ):
                status = "needs_clarification"
            structured = StructuredQuestion.model_validate(
                {
                    "question_type": draft.question_type,
                    "pico": draft.pico,
                    "ambiguities": draft.ambiguities,
                    "extraction_status": status,
                    "blocking_ambiguities": blocking,
                }
            )
            return QueryPlan(
                original_question=request.question,
                structured_question=structured,
                terms=draft.terms,
                concept_groups=draft.concept_groups,
                search_intent=draft.question_type,
                preserved_constraints=[
                    ExtractedField(
                        text=request.question,
                        origin="user_text",
                        source_span=SourceSpan(start=0, end=len(request.question)),
                    )
                ],
            )
        except Exception as error:
            code: ResearchCode = (
                "extraction_timeout"
                if (
                    isinstance(error, TimeoutError)
                    or isinstance(error, ResearchError)
                    and error.code in {"generation_timeout", "extraction_timeout"}
                )
                else "extraction_failed"
            )
            raise ResearchError(code) from None
