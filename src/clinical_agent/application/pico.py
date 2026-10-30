"""One bounded extraction call, then deterministic provenance validation and planning."""

import json
import logging
import math
import re
from collections.abc import Callable
from hashlib import sha256
from time import monotonic
from typing import Protocol

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from clinical_agent.domain.openalex import ResearchConstraints
from clinical_agent.domain.pico import (
    PICO,
    ClassificationRequest,
    ConceptMapping,
    ConceptRelation,
    ExtractedField,
    ExtractionDraft,
    PaperTarget,
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


_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
_FIELD_NAMES = frozenset().union(
    *(
        model.model_fields
        for model in (
            ExtractionDraft,
            QueryPlan,
            ResearchConstraints,
            PaperTarget,
            ConceptRelation,
            ConceptMapping,
            PICO,
            ExtractedField,
            SourceSpan,
            StructuredQuestion,
            ClassificationRequest,
        )
    )
)
_RULE_FIELDS = {
    "paper_target_quote": "paper_target.source_text",
    "constraint_quote": "research_constraints",
    "relation_quote": "concept_relations.source_text",
    "expansion_not_anchor": "concept_relations.required",
    "relation_anchor": "concept_relations.concept_id",
    "mapping_quote": "concept_mappings.source_text",
    "search_intent": "search_intent",
    "source_span": "source_span",
    "preserved_constraints": "preserved_constraints",
    "source_mapping": "concept_mappings.source_text",
    "optional_mapping_group": "concept_mappings",
    "origin_span": "source_span",
    "nonempty_span": "source_span",
    "expanded_pico": "pico",
    "doi_invalid": "paper_target.source_text",
    "status_branch": "extraction_status",
    "relative_years_required": "research_constraints.years",
    "explicit_years_required": "research_constraints.year_from",
    "unexpected_year_bounds": "research_constraints.year_from",
    "time_text_required": "research_constraints.time_text",
    "task_intent_required": "task_intent",
}
_VALIDATION_KIND = {
    "schema": "schema_validation",
    "status": "status_validation",
    "plan": "plan_validation",
}


def _field_path(loc: object) -> str:
    if not isinstance(loc, tuple):
        return ""
    parts: list[str] = []
    for key in loc:
        if type(key) is int and 0 <= key <= 30:
            parts.append(str(key))
        elif isinstance(key, str) and key in _FIELD_NAMES and _NAME.fullmatch(key):
            parts.append(key)
        else:
            return ""
    path = ".".join(parts)
    return path if len(path) <= 200 else ""


def _rejection_details(error: Exception) -> tuple[str, str]:
    items: list[tuple[str, str]] = []
    if isinstance(error, PydanticCustomError) and isinstance(error.type, str):
        items.append((error.type, _RULE_FIELDS.get(error.type, "")))
    elif isinstance(error, ValidationError):
        for item in error.errors(include_input=False, include_context=False, include_url=False)[
            :10
        ]:
            code = item.get("type")
            code = code if isinstance(code, str) else ""
            path = _field_path(item.get("loc")) or _RULE_FIELDS.get(code, "")
            items.append((code, path))
    rules = ",".join(code for code, _path in items)
    paths = ",".join(path for _code, path in items if path)
    return rules, paths


def _failure_kind(error: Exception, stage: str) -> str:
    if isinstance(error, ResearchError):
        return error.code
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ValidationError):
        return _VALIDATION_KIND.get(stage, "schema_validation")
    return stage


def log_extraction_rejection(
    *,
    stage: str,
    failure_kind: str,
    rule_code: str = "",
    field_paths: str = "",
    response_hash: str | None = None,
) -> None:
    """Log closed diagnostic tokens. Callers must not pass payloads or exception text."""
    stage_text = stage if _TOKEN.fullmatch(stage) else "unknown"
    kind_text = failure_kind if _TOKEN.fullmatch(failure_kind) else "unknown"
    rules = [item for item in rule_code.split(",") if _TOKEN.fullmatch(item)][:10]
    paths: list[str] = []
    for item in field_paths.split(","):
        if (
            item
            and len(item) <= 200
            and all(
                part.isdigit() or (part in _FIELD_NAMES and _NAME.fullmatch(part))
                for part in item.split(".")
            )
        ):
            paths.append(item)
        if len(paths) == 10:
            break
    digest = (
        response_hash
        if isinstance(response_hash, str) and re.fullmatch(r"[0-9a-f]{64}", response_hash)
        else ""
    )
    rule_text = ",".join(rules)
    path_text = ",".join(paths)
    extra = {"stage": stage_text, "failure_kind": kind_text}
    if rule_text:
        extra["rule_code"] = rule_text
    if path_text:
        extra["field_paths"] = path_text
    if digest:
        extra["response_hash"] = digest
    message = (
        "QueryPlan extraction rejected "
        f"stage={stage_text} failure_kind={kind_text} rule_code={rule_text} "
        f"field_paths={path_text} response_hash={digest}"
    )
    logging.getLogger(__name__).warning(message, extra=extra)


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
        stage = "provider"
        response_hash = None
        try:
            raw = self._extractor.extract(request.model_copy(deep=True), timeout_seconds=budget)
            if self._clock() >= deadline:
                raise ResearchError("extraction_timeout")
            stage = "response_size"
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > self._max_output_bytes:
                raise ValueError("Invalid extraction output size")
            response_hash = sha256(raw.encode("utf-8")).hexdigest()
            stage = "empty_response"
            if not raw.strip():
                raise ValueError("Empty extraction response")
            stage = "json"
            data = json.loads(raw, object_pairs_hook=_unique, parse_constant=_invalid_constant)
            stage = "schema"
            draft = ExtractionDraft.model_validate(data)
            stage = "span"
            for field in [*draft.pico.fields(), *draft.terms]:
                # The exact quote is evidence; model-generated offsets are not.
                # Resolve only a unique verbatim occurrence, never fuzzy-match text.
                if field.origin == "user_text" and request.question.count(field.text) == 1:
                    start = request.question.index(field.text)
                    field.source_span = SourceSpan(start=start, end=start + len(field.text))
                field.validate_source(request.question)
            stage = "mapping"
            for mapping in draft.concept_mappings:
                if mapping.source_text not in request.question:
                    raise PydanticCustomError("source_mapping", "source_mapping")
                if not mapping.required and mapping.english_terms in draft.concept_groups:
                    raise PydanticCustomError("optional_mapping_group", "optional_mapping_group")
            stage = "status"
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
            stage = "plan"
            return QueryPlan(
                task_intent=draft.task_intent,
                paper_target=draft.paper_target,
                research_constraints=draft.research_constraints,
                original_question=request.question,
                structured_question=structured,
                terms=draft.terms,
                concept_relations=draft.concept_relations,
                concept_groups=draft.concept_groups,
                concept_mappings=draft.concept_mappings,
                research_intent=draft.research_intent,
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
            rule_code, field_paths = _rejection_details(error)
            log_extraction_rejection(
                stage=stage,
                failure_kind=_failure_kind(error, stage),
                rule_code=rule_code,
                field_paths=field_paths,
                response_hash=response_hash,
            )
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
