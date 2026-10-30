"""One bounded analysis call, strict evidence checks, trusted source hydration."""

import json
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError

from clinical_agent.application.openalex import log_evidence_trace
from clinical_agent.application.pico import _invalid_constant, _unique
from clinical_agent.domain.analysis import (
    DIMENSIONS,
    FEASIBILITY_DIMENSIONS,
    METHOD_FIELDS,
    AnalysisDraft,
    AnalysisItem,
    AnalysisResult,
    AnalysisRetrieval,
    AnalysisSelection,
    CandidateExperiment,
    CandidateGap,
    EvidencePointer,
    FeasibilityAssessment,
    IdeaSimilarity,
    SimilarityDimension,
    StudyAssessment,
    StudyComparison,
    consistent_relation,
)
from clinical_agent.domain.citations import build_answer
from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.research import (
    DraftClaim,
    GenerationDraft,
    QuestionRequest,
    ResearchError,
    ResearchLimits,
)
from clinical_agent.domain.retrieval import RetrievalResult

_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_METADATA_STUDY_TYPES = {
    "Clinical Trial": "trial",
    "Randomized Controlled Trial": "trial",
    "Cohort Studies": "cohort",
    "Case-Control Studies": "case_control",
    "Cross-Sectional Studies": "cross_sectional",
    "Systematic Review": "systematic_review",
    "Guideline": "guideline",
    "Practice Guideline": "guideline",
}
_BUSINESS_RULES = frozenset(
    {
        "missing_basis",
        "value_requires_evidence",
        "inference_requires_verification",
        "reported_fact_quote",
        "method_fields_required",
        "unknown_study_type",
        "known_type_basis",
        "study_type_evidence",
        "metadata_basis_required",
        "five_dimensions",
        "overall_relation",
        "candidate_gap_kind",
        "feasibility_status",
        "conditional_inference",
        "reported_barrier_fact",
        "experiment_hypothesis",
        "duplicate_feasibility_dimension",
        "experiment_gap_index",
        "feasibility_dimensions",
        "study_set_mismatch",
        "publication_type_mismatch",
        "similarity_evidence",
        "comparison_identity",
    }
)
_SCHEMA_STATUS = {
    "response": "not_run",
    "json_decode": "not_run",
    "schema_validation": "rejected",
    "business_validation": "accepted",
    "evidence_validation": "accepted",
    "unknown_failure": "not_run",
}
_FIELD_NAMES = frozenset().union(
    *(
        model.model_fields
        for model in (
            EvidencePointer,
            AnalysisItem,
            StudyAssessment,
            SimilarityDimension,
            IdeaSimilarity,
            CandidateGap,
            StudyComparison,
            FeasibilityAssessment,
            CandidateExperiment,
            AnalysisDraft,
        )
    ),
    METHOD_FIELDS,
    DIMENSIONS,
)


class AnalysisFailure(Exception):
    def __init__(
        self, stage: str, rule: str, field_paths: str = "", json_pos: int | None = None
    ) -> None:
        self.stage = stage
        self.rule = rule
        self.field_paths = field_paths
        self.json_pos = json_pos


def _field_path(loc: object) -> str:
    if not isinstance(loc, tuple):
        return ""
    parts: list[str] = []
    for key in loc:
        if type(key) is int and 0 <= key <= 40:
            parts.append(str(key))
        elif isinstance(key, str) and key in _FIELD_NAMES and _TOKEN.fullmatch(key):
            parts.append(key)
        else:
            return ""
    path = ".".join(parts)
    return path if len(path) <= 200 else ""


def _classify(error: ValidationError) -> tuple[str, str, str]:
    items = error.errors(include_input=False, include_context=False, include_url=False)[:8]
    schema: list[tuple[str, str]] = []
    business: list[tuple[str, str]] = []
    for item in items:
        code = item.get("type")
        code = code if isinstance(code, str) else ""
        bucket = business if code in _BUSINESS_RULES else schema
        bucket.append((code, _field_path(item.get("loc"))))
    chosen = schema or business
    codes: list[str] = []
    paths: list[str] = []
    for code, path in chosen:
        if _TOKEN.fullmatch(code) and code not in codes:
            codes.append(code)
        if path and path not in paths:
            paths.append(path)
    kept: list[str] = []
    for path in paths:
        candidate = ",".join([*kept, path])
        if len(candidate) > 200:
            break
        kept.append(path)
    return (
        ("schema_validation" if schema else "business_validation"),
        ",".join(codes),
        ",".join(kept),
    )


def _observed(model: object) -> dict[str, str]:
    raw = getattr(model, "completion_details", None)
    if not isinstance(raw, dict):
        return {}
    safe: dict[str, str] = {}
    for key in ("input_tokens", "output_tokens", "reasoning_tokens", "content_chars"):
        value = raw.get(key)
        if isinstance(value, str) and value.isdigit() and len(value) <= 7:
            safe[key] = value
    reason = raw.get("finish_reason")
    if isinstance(reason, str) and _TOKEN.fullmatch(reason):
        safe["finish_reason"] = reason
    return safe


_SENTENCE_END = re.compile(r"(?<!\d)[.!?。！？](?!\d)|(?<=\d)[.!?。！？](?!\d)")
_GAP_REASON = "Not reported in the supplied evidence."
_NEXT_CHECKS = {
    "data": "确认数据使用权限、样本与标注获取方式。",
    "methods": "定位原方法及可复现基线，核查与目标任务的差异。",
    "compute": "用小规模试验实测显存、时间与成本需求。",
    "validation": "确认独立验证数据、评价指标及实验实施条件。",
}


def quote_catalog(hits: dict[UUID, Any]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for chunk_id, hit in hits.items():
        text = hit.chunk.text
        index = 0
        start = 0
        spans: list[str] = []
        for match in _SENTENCE_END.finditer(text):
            spans.append(text[start : match.end()])
            start = match.end()
        if text[start:].strip():
            spans.append(text[start:])
        for raw in spans:
            sentence = raw.strip()
            if not sentence or sentence not in text or len(sentence) > 2000:
                continue
            quote_id = f"{chunk_id}#{index}"
            catalog[quote_id] = {
                "quote_id": quote_id,
                "document_id": hit.document.document_id,
                "chunk_id": chunk_id,
                "text": sentence,
                "content_scope": hit.document.content_scope,
                "location_kind": hit.chunk.location.kind,
            }
            index += 1
    return catalog


def _missing_item() -> dict[str, Any]:
    return {
        "value": None,
        "epistemic_kind": "reported_fact",
        "evidence": [],
        "basis": "not_reported",
        "verification_needed": None,
    }


def _fact_item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "value": entry["text"],
        "epistemic_kind": "reported_fact",
        "evidence": [{"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]}],
        "basis": "text",
        "verification_needed": None,
    }


def _inference_item(
    value: str, kind: str, verification: str, entry: dict[str, Any]
) -> dict[str, Any]:
    return {
        "value": value,
        "epistemic_kind": kind,
        "evidence": [{"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]}],
        "basis": "model_inference",
        "verification_needed": verification,
    }


def _quote(
    catalog: dict[str, dict[str, Any]], quote_id: str, allowed: set[UUID]
) -> dict[str, Any] | None:
    entry = catalog.get(quote_id)
    if entry is None:
        raise AnalysisFailure("evidence_validation", "unknown_quote", "quotes")
    if entry["document_id"] not in allowed:
        return None
    return entry


def _legacy_draft(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    studies = data.get("studies")
    if not isinstance(studies, list) or not studies or not isinstance(studies[0], dict):
        return False
    return isinstance(studies[0].get("fields"), dict)


def _public_quotes(catalog: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "quote_id": item["quote_id"],
            "document_id": str(item["document_id"]),
            "chunk_id": str(item["chunk_id"]),
            "content_scope": item["content_scope"],
            "location_kind": item["location_kind"],
            "text": item["text"],
        }
        for item in catalog.values()
    ]


def build_draft(
    selection: AnalysisSelection,
    catalog: dict[str, dict[str, Any]],
    question: str,
    document_ids: list[UUID],
    *,
    feasibility: bool,
    publication_types: dict[UUID, list[str]],
) -> dict[str, Any]:
    studies_by: dict[UUID, Any] = {}
    for study in selection.studies:
        studies_by.setdefault(study.document_id, study)
    similarities_by: dict[UUID, Any] = {}
    for similarity in selection.similarities:
        similarities_by.setdefault(similarity.document_id, similarity)
    studies: list[dict[str, Any]] = []
    similarities: list[dict[str, Any]] = []
    for document_id in document_ids:
        chosen = studies_by.get(document_id)
        fields = {name: _missing_item() for name in METHOD_FIELDS}
        study_type, type_basis = "unknown", "unknown"
        type_evidence: list[dict[str, str]] = []
        metadata: list[str] = []
        if chosen is not None:
            reported: set[str] = set()
            for item in chosen.reported:
                if item.role != "reported" or item.field_name in reported:
                    continue
                entry = _quote(catalog, item.quote_id, {document_id})
                if entry is None:
                    continue
                fields[item.field_name] = _fact_item(entry)
                reported.add(item.field_name)
            for item in chosen.inferences:
                if item.field_name in reported:
                    continue
                entry = _quote(catalog, item.quote_id, {document_id})
                if entry is None:
                    continue
                if not item.verification_needed:
                    raise AnalysisFailure(
                        "business_validation",
                        "inference_requires_verification",
                        "studies.fields",
                    )
                fields[item.field_name] = _inference_item(
                    item.value, item.epistemic_kind, item.verification_needed, entry
                )
                reported.add(item.field_name)
            study_type, type_basis = chosen.study_type, chosen.type_basis
            metadata = list(chosen.metadata_basis)
            if type_basis == "text" and chosen.type_quote_id:
                entry = _quote(catalog, chosen.type_quote_id, {document_id})
                if entry is not None:
                    type_evidence = [{"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]}]
                else:
                    study_type, type_basis, metadata = "unknown", "unknown", []
            elif type_basis == "text":
                study_type, type_basis, metadata = "unknown", "unknown", []
            elif type_basis == "model_inference" and chosen.type_quote_id:
                entry = _quote(catalog, chosen.type_quote_id, {document_id})
                if entry is not None:
                    type_evidence = [{"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]}]
                else:
                    study_type, type_basis, metadata = "unknown", "unknown", []
            elif type_basis == "model_inference":
                study_type, type_basis, metadata = "unknown", "unknown", []
            if type_basis == "unknown":
                study_type = "unknown"
                type_evidence = []
                metadata = []
            allowed = set(publication_types.get(document_id, ()))
            metadata = [item for item in metadata if item in allowed]
            if type_basis == "metadata":
                mapped = {_METADATA_STUDY_TYPES.get(item, "other") for item in metadata}
                if not metadata:
                    study_type, type_basis, metadata = "unknown", "unknown", []
                    type_evidence = []
                elif study_type not in mapped:
                    if len(mapped) == 1:
                        study_type = next(iter(mapped))
                    else:
                        study_type, type_basis, metadata = "unknown", "unknown", []
                        type_evidence = []
        studies.append(
            {
                "document_id": str(document_id),
                "study_type": study_type,
                "type_basis": type_basis,
                "type_evidence": type_evidence,
                "metadata_basis": metadata,
                "fields": fields,
            }
        )
        supplied: dict[str, Any] = {}
        similarity = similarities_by.get(document_id)
        if similarity is not None:
            for dimension in similarity.dimensions:
                supplied.setdefault(dimension.name, dimension)
        dimensions: dict[str, Any] = {}
        for name in ("question", "population", "data", "methods", "outcomes"):
            dimension = supplied.get(name)
            relation, idea, evidence, reason = "unknown", None, [], _GAP_REASON
            if dimension is not None:
                reason = dimension.reason
                entry = (
                    _quote(catalog, dimension.quote_id, {document_id})
                    if dimension.quote_id
                    else None
                )
                idea_ok = dimension.idea_quote is not None and dimension.idea_quote in question
                if dimension.relation != "unknown" and entry is not None and idea_ok:
                    relation = dimension.relation
                    idea = dimension.idea_quote
                    evidence = [{"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]}]
            dimensions[name] = {
                "relation": relation,
                "idea_quote": idea,
                "evidence": evidence,
                "reason": reason,
            }
        similarities.append(
            {
                "document_id": str(document_id),
                "dimensions": dimensions,
                "overall_relation": consistent_relation(
                    {item["relation"] for item in dimensions.values()}
                ),
            }
        )
    allowed = set(document_ids)
    gaps = []
    for gap in selection.gaps:
        entry = _quote(catalog, gap.quote_id, allowed)
        if entry is None:
            continue
        counter: list[dict[str, str]] = []
        if gap.counter_quote_id:
            other = _quote(catalog, gap.counter_quote_id, allowed)
            if other is not None:
                counter = [{"chunk_id": str(other["chunk_id"]), "quote": other["text"]}]
        gaps.append(
            {
                "description": _inference_item(
                    gap.value, gap.epistemic_kind, gap.verification_needed, entry
                ),
                "counter_evidence": counter,
                "reasoning": gap.reasoning,
                "scope": gap.scope,
            }
        )
    comparisons = []
    for comparison in selection.comparisons:
        evidence = []
        for quote_id in comparison.quote_ids:
            entry = _quote(catalog, quote_id, set(comparison.document_ids))
            if entry is not None:
                evidence.append({"chunk_id": str(entry["chunk_id"]), "quote": entry["text"]})
        comparisons.append(
            {
                "document_ids": [str(item) for item in comparison.document_ids],
                "relation": comparison.relation,
                "comparability": comparison.comparability,
                "reason": comparison.reason,
                "evidence": evidence,
            }
        )
    feasibility_items = []
    if feasibility:
        chosen = {}
        for item in selection.feasibility:
            chosen.setdefault(item.dimension, item)
        for dimension in FEASIBILITY_DIMENSIONS:
            item = chosen.get(dimension)
            assessment = _missing_item()
            status = "unknown"
            next_check = item.next_check if item is not None else _NEXT_CHECKS[dimension]
            if item is not None and item.status == "reported_barrier" and item.quote_id:
                entry = _quote(catalog, item.quote_id, allowed)
                if entry is not None:
                    assessment = _fact_item(entry)
                    status = "reported_barrier"
            elif item is not None and item.status == "conditional":
                if not item.value or not item.verification_needed or not item.quote_id:
                    raise AnalysisFailure(
                        "business_validation",
                        "inference_requires_verification",
                        "feasibility",
                    )
                entry = _quote(catalog, item.quote_id, allowed)
                if entry is not None:
                    assessment = _inference_item(
                        item.value, "model_inference", item.verification_needed, entry
                    )
                    status = "conditional"
            feasibility_items.append(
                {
                    "dimension": dimension,
                    "status": status,
                    "assessment": assessment,
                    "next_check": next_check,
                }
            )
    return {
        "studies": studies,
        "idea_similarities": similarities,
        "candidate_gaps": gaps,
        "comparisons": comparisons,
        "feasibility": feasibility_items,
        "experiments": [],
    }


class AnalysisModel(Protocol):
    def analyze_evidence(
        self,
        context: dict[str, object],
        *,
        timeout_seconds: float,
        max_output_tokens: int | None = None,
    ) -> str: ...


class EvidenceAnalyzer:
    def __init__(
        self,
        *,
        model: AnalysisModel,
        limits: ResearchLimits | None = None,
        clock: Callable[[], float] = monotonic,
        timeout_seconds: float = 60.0,
        model_id: str | None = None,
        analysis_max_tokens: int = 16384,
        analysis_retry_max_tokens: int = 32768,
        max_output_bytes: int | None = None,
    ) -> None:
        self.model, self.clock = model, clock
        self.model_id = model_id
        self.analysis_max_tokens = analysis_max_tokens
        self.analysis_retry_max_tokens = analysis_retry_max_tokens
        self.limits = ResearchLimits.model_validate(limits or ResearchLimits())
        self.max_output_bytes = (
            self.limits.max_output_bytes if max_output_bytes is None else max_output_bytes
        )
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("generation_timeout")
        self.timeout_seconds = timeout_seconds

    def _log_call(
        self,
        request: QuestionRequest,
        *,
        output_tokens: int,
        retries: int,
        schema: str,
        failure_kind: str,
        hits: int,
        details: dict[str, str] | None = None,
        field_paths: str = "",
        rule_code: str = "",
        raw: object = None,
        json_pos: int | None = None,
    ) -> None:
        counts: dict[str, int | str] = {
            "hits": hits,
            "max_output": output_tokens,
            "configured_max_output": output_tokens,
            "retries": retries,
            "schema": schema,
            "schema_status": schema,
            "content_chars": "unknown",
            "output_character_count": "unknown",
            "input_tokens": "unknown",
            "output_tokens": "unknown",
            "reasoning_tokens": "unknown",
        }
        if type(json_pos) is int and 0 <= json_pos <= 1_000_000:
            counts["json_pos"] = json_pos
        combined = _observed(self.model)
        if isinstance(raw, str):
            combined["content_chars"] = str(len(raw.encode()))
        combined.update(details or {})
        for key in ("content_chars", "input_tokens", "output_tokens", "reasoning_tokens"):
            value = combined.get(key)
            if isinstance(value, str) and (value.isdigit() or value == "unknown"):
                counts[key] = int(value) if value.isdigit() else value
        if counts["content_chars"] != "unknown":
            counts["output_character_count"] = counts["content_chars"]
        finish = combined.get("finish_reason", "")
        log_evidence_trace(
            stage="analyze",
            counts=counts,
            failure_kind=failure_kind,
            request_id=str(request.request_id),
            model_id=self.model_id,
            field_paths=field_paths,
            rule_code=rule_code,
            response_hash=sha256(raw.encode()).hexdigest() if isinstance(raw, str) else "",
            finish_reason=finish if isinstance(finish, str) else "",
        )

    def analyze(
        self,
        request: QuestionRequest,
        retrieval: RetrievalResult,
        *,
        query_plan: QueryPlan | None = None,
        timeout_seconds: float = 60.0,
    ) -> AnalysisResult:
        request = QuestionRequest.model_validate(request).model_copy(deep=True)
        retrieval = RetrievalResult.model_validate(retrieval).model_copy(deep=True)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("generation_timeout")
        budget = min(timeout_seconds, self.timeout_seconds, self.limits.generation_seconds)
        deadline = self.clock() + budget
        if query_plan is not None and query_plan.original_question != request.question:
            raise ResearchError("model_output_invalid")
        # Reuse the existing trusted-source gate, including scope, hash and identity checks.
        try:
            answer = build_answer(
                request,
                retrieval,
                GenerationDraft(
                    claims=[
                        DraftClaim(
                            text="Supplied research passage.",
                            kind="evidence",
                            evidence_chunk_ids=[h.chunk.chunk_id],
                            limitations=[],
                        )
                        for h in retrieval.hits
                    ]
                )
                if retrieval.hits
                else None,
                generated_at=datetime.now(UTC),
            )
        except ResearchError as error:
            log_evidence_trace(
                stage="analyze",
                counts={"hits": len(retrieval.hits)},
                failure_kind=error.code,
                request_id=str(request.request_id),
            )
            raise
        base: dict[str, Any] = dict(
            model_id=self.model_id,
            request_id=request.request_id,
            original_idea=request.question,
            query_plan=query_plan,
            analysis_scope=(
                "Only supplied evidence passages; no full-text or semantic verification is implied."
            ),
            limitations=[
                "Evidence pointers are checked; medical meaning, completeness "
                "and candidate gaps require human review."
            ],
            unresolved_questions=[],
            sources=answer.sources,
            retrieval=AnalysisRetrieval(
                scope=retrieval.scope,
                options=retrieval.options,
                search_provenance=retrieval.search_provenance,
            ),
            generated_at=datetime.now(UTC),
        )
        empty: dict[str, Any] = dict(
            studies=[], idea_similarities=[], candidate_gaps=[], comparisons=[]
        )
        if query_plan and query_plan.task_intent == "feasibility":
            empty["feasibility"] = [
                FeasibilityAssessment(
                    dimension=dimension,
                    status="unknown",
                    assessment=AnalysisItem(
                        value=None,
                        epistemic_kind="reported_fact",
                        evidence=[],
                        basis="unknown",
                        verification_needed=None,
                    ),
                    next_check=question,
                )
                for dimension, question in zip(
                    FEASIBILITY_DIMENSIONS,
                    (
                        "确认数据使用权限、样本与标注获取方式。",
                        "定位原方法及可复现基线，核查与目标任务的差异。",
                        "用小规模试验实测显存、时间与成本需求。",
                        "确认独立验证数据、评价指标及实验实施条件。",
                    ),
                    strict=True,
                )
            ]
        if not retrieval.hits:
            log_evidence_trace(
                stage="analyze",
                counts={"hits": 0, "sources": 0},
                failure_kind="insufficient_evidence",
                request_id=str(request.request_id),
            )
            return AnalysisResult(**base, **empty, analysis_status="insufficient_evidence")
        documents = {s.document_id: s for s in answer.sources}
        eligible = {
            k: v
            for k, v in documents.items()
            if not any("retract" in n.casefold() for n in [*v.source_notices, *v.publication_types])
        }
        if not eligible:
            log_evidence_trace(
                stage="analyze",
                counts={"hits": len(retrieval.hits), "sources": 0},
                failure_kind="not_evaluated",
                request_id=str(request.request_id),
            )
            return AnalysisResult(**base, **empty, analysis_status="not_evaluated")
        hits = {h.chunk.chunk_id: h for h in retrieval.hits if h.document.document_id in eligible}
        catalog = quote_catalog(hits)
        sources = []
        for source in eligible.values():
            dumped = source.model_dump(mode="json", exclude={"snapshot_xml", "openalex_record"})
            dumped["evidence"] = [
                {"chunk_id": item["chunk_id"], "location": item["location"]}
                for item in dumped["evidence"]
            ]
            sources.append(dumped)
        context: dict[str, object] = {
            "original_idea": request.question,
            "query_plan": query_plan.model_dump(mode="json") if query_plan else None,
            "sources": sources,
            "quotes": _public_quotes(catalog),
            "output_schema": AnalysisSelection.model_json_schema(),
        }
        payload = json.dumps(context, ensure_ascii=False)
        if len(payload) > self.limits.max_context_characters:
            raise ResearchError("context_limit")
        output_tokens = self.analysis_max_tokens
        raw: object = None
        correction: dict[str, str] | None = None
        for attempt in (0, 1):
            if self.clock() >= deadline:
                self._log_call(
                    request,
                    output_tokens=output_tokens,
                    retries=attempt,
                    schema="not_run",
                    failure_kind="analysis_output_truncated",
                    hits=len(retrieval.hits),
                )
                raise ResearchError("analysis_output_truncated")
            try:
                call_context = (
                    context if correction is None else {**context, "correction": correction}
                )
                raw = self.model.analyze_evidence(
                    call_context,
                    timeout_seconds=deadline - self.clock(),
                    max_output_tokens=output_tokens,
                )
                if self.clock() >= deadline:
                    raise ResearchError("generation_timeout")
                if not isinstance(raw, str):
                    raise AnalysisFailure("response", "response_type")
                if len(raw.encode()) > self.max_output_bytes:
                    raise AnalysisFailure("response", "response_budget")
                try:
                    parsed = json.loads(
                        raw, object_pairs_hook=_unique, parse_constant=_invalid_constant
                    )
                except json.JSONDecodeError as error:
                    pos = error.pos if type(error.pos) is int else None
                    raise AnalysisFailure(
                        "json_decode", "json_decode_failed", json_pos=pos
                    ) from None
                except ValueError:
                    raise AnalysisFailure("json_decode", "json_decode_failed") from None
                try:
                    if _legacy_draft(parsed):
                        draft = AnalysisDraft.model_validate(parsed)
                    else:
                        selection = AnalysisSelection.model_validate(parsed)
                        draft = AnalysisDraft.model_validate(
                            build_draft(
                                selection,
                                catalog,
                                request.question,
                                list(eligible),
                                feasibility=bool(
                                    query_plan and query_plan.task_intent == "feasibility"
                                ),
                                publication_types={
                                    document_id: list(source.publication_types)
                                    for document_id, source in eligible.items()
                                },
                            )
                        )
                except ValidationError as error:
                    stage, rule, paths = _classify(error)
                    raise AnalysisFailure(stage, rule, paths) from None

                def check(refs: list[EvidencePointer], allowed: set[UUID], path: str) -> set[UUID]:
                    found = set()
                    for ref in refs:
                        hit = hits.get(ref.chunk_id)
                        if (
                            hit is None
                            or hit.document.document_id not in allowed
                            or ref.quote not in hit.chunk.text
                        ):
                            raise AnalysisFailure(
                                "evidence_validation", "evidence_pointer_invalid", path
                            )
                        found.add(hit.document.document_id)
                    return found

                if (
                    query_plan
                    and query_plan.task_intent == "feasibility"
                    and {x.dimension for x in draft.feasibility} != set(FEASIBILITY_DIMENSIONS)
                ):
                    raise AnalysisFailure(
                        "business_validation", "feasibility_dimensions", "feasibility"
                    )
                for item in draft.feasibility:
                    check(
                        item.assessment.evidence, set(eligible), "feasibility.assessment.evidence"
                    )
                for experiment in draft.experiments:
                    for name in (
                        "hypothesis",
                        "baseline",
                        "experiment",
                        "metrics",
                        "failure_criterion",
                    ):
                        check(
                            getattr(experiment, name).evidence,
                            set(eligible),
                            f"experiments.{name}.evidence",
                        )
                ids = [s.document_id for s in draft.studies]
                sims = [s.document_id for s in draft.idea_similarities]
                if (
                    set(ids) != set(eligible)
                    or len(ids) != len(set(ids))
                    or set(sims) != set(ids)
                    or len(sims) != len(ids)
                ):
                    raise AnalysisFailure("business_validation", "study_set_mismatch", "studies")
                for study in draft.studies:
                    check(study.type_evidence, {study.document_id}, "studies.type_evidence")
                    if not set(study.metadata_basis) <= set(
                        eligible[study.document_id].publication_types
                    ):
                        raise AnalysisFailure(
                            "evidence_validation",
                            "source_identity_mismatch",
                            "studies.metadata_basis",
                        )
                    if study.type_basis == "metadata" and study.study_type not in {
                        _METADATA_STUDY_TYPES.get(t, "other") for t in study.metadata_basis
                    }:
                        raise AnalysisFailure(
                            "business_validation", "publication_type_mismatch", "studies.study_type"
                        )
                    metadata_designs = {
                        _METADATA_STUDY_TYPES[t]
                        for t in eligible[study.document_id].publication_types
                        if t in _METADATA_STUDY_TYPES
                    }
                    if metadata_designs and study.study_type not in metadata_designs:
                        base["limitations"].append(
                            "Metadata and text study-design classification differ; "
                            "review the original source."
                        )
                    for item in study.fields.values():
                        check(item.evidence, {study.document_id}, "studies.fields.evidence")
                for similarity in draft.idea_similarities:
                    for dimension in similarity.dimensions.values():
                        check(
                            dimension.evidence,
                            {similarity.document_id},
                            "idea_similarities.dimensions.evidence",
                        )
                        if (
                            dimension.idea_quote is not None
                            and dimension.idea_quote not in request.question
                        ):
                            raise AnalysisFailure(
                                "evidence_validation",
                                "idea_quote_invalid",
                                "idea_similarities.dimensions.idea_quote",
                            )
                        if dimension.relation != "unknown" and (
                            not dimension.idea_quote or not dimension.evidence
                        ):
                            raise AnalysisFailure(
                                "business_validation",
                                "similarity_evidence",
                                "idea_similarities.dimensions",
                            )
                for gap in draft.candidate_gaps:
                    check(gap.description.evidence, set(ids), "candidate_gaps.description.evidence")
                    check(gap.counter_evidence, set(ids), "candidate_gaps.counter_evidence")
                for comparison in draft.comparisons:
                    left, right = comparison.document_ids
                    if left == right or left not in eligible or right not in eligible:
                        raise AnalysisFailure(
                            "business_validation", "comparison_identity", "comparisons.document_ids"
                        )
                    a, b = eligible[left], eligible[right]
                    if (
                        a.content_hash == b.content_hash
                        or (a.pmid and a.pmid == b.pmid)
                        or (a.doi and b.doi and a.doi.casefold() == b.doi.casefold())
                    ):
                        raise AnalysisFailure(
                            "evidence_validation",
                            "source_identity_mismatch",
                            "comparisons.document_ids",
                        )
                    if check(comparison.evidence, {left, right}, "comparisons.evidence") != {
                        left,
                        right,
                    }:
                        raise AnalysisFailure(
                            "evidence_validation", "comparison_evidence", "comparisons.evidence"
                        )
                break
            except AnalysisFailure as failure:
                rules = [item for item in failure.rule.split(",") if _TOKEN.fullmatch(item)]
                revised = {
                    **context,
                    "correction": {"rule_code": failure.rule, "field_paths": failure.field_paths},
                }
                if (
                    attempt == 0
                    and failure.stage == "business_validation"
                    and rules
                    and set(rules) <= _BUSINESS_RULES
                    and self.clock() < deadline
                    and len(json.dumps(revised, ensure_ascii=False))
                    <= self.limits.max_context_characters
                ):
                    correction = revised["correction"]
                    continue
                self._log_call(
                    request,
                    output_tokens=output_tokens,
                    retries=attempt,
                    schema=_SCHEMA_STATUS[failure.stage],
                    failure_kind=failure.stage,
                    hits=len(retrieval.hits),
                    field_paths=failure.field_paths,
                    rule_code=failure.rule,
                    raw=raw,
                    json_pos=failure.json_pos,
                )
                raise ResearchError("model_output_invalid") from None
            except ResearchError as error:
                if (
                    error.code == "analysis_output_truncated"
                    and attempt == 0
                    and self.analysis_retry_max_tokens > output_tokens
                    and self.clock() < deadline
                ):
                    output_tokens = self.analysis_retry_max_tokens
                    continue
                self._log_call(
                    request,
                    output_tokens=output_tokens,
                    retries=attempt,
                    schema="not_run",
                    failure_kind=error.code,
                    hits=len(retrieval.hits),
                    details=error.details,
                    raw=raw,
                )
                raise
            except TimeoutError:
                self._log_call(
                    request,
                    output_tokens=output_tokens,
                    retries=attempt,
                    schema="not_run",
                    failure_kind="generation_timeout",
                    hits=len(retrieval.hits),
                    raw=raw,
                )
                raise ResearchError("generation_timeout") from None
            except Exception:
                self._log_call(
                    request,
                    output_tokens=output_tokens,
                    retries=attempt,
                    schema="not_run",
                    failure_kind="unknown_failure",
                    hits=len(retrieval.hits),
                    rule_code="unknown_failure",
                    raw=raw,
                )
                raise ResearchError("model_output_invalid") from None
        else:
            raise ResearchError("analysis_output_truncated")
        for study in draft.studies:
            missing = sorted(k for k, value in study.fields.items() if value.value is None)
            if missing:
                base["unresolved_questions"].append(
                    f"Study {study.document_id}: not reported/unknown: {', '.join(missing)}"
                )
        if len(eligible) != len(documents):
            base["limitations"].append(
                "Retracted sources were retained for traceability and excluded from analysis."
            )
        partial = (
            len(base["limitations"]) > 1
            or any(x.status == "unknown" for x in draft.feasibility)
            or any(s.study_type == "unknown" for s in draft.studies)
            or len(eligible) != len(documents)
            or any(s.source_notices or s.content_scope == "abstract" for s in documents.values())
            or any(i.value is None for s in draft.studies for i in s.fields.values())
            or any(s.overall_relation == "unknown" for s in draft.idea_similarities)
            or (
                retrieval.search_provenance is not None
                and retrieval.search_provenance.status == "partial"
            )
        )
        status = "partial" if partial else "completed"
        self._log_call(
            request,
            output_tokens=output_tokens,
            retries=attempt,
            schema="accepted",
            failure_kind=status,
            hits=len(retrieval.hits),
        )
        return AnalysisResult(**base, **draft.model_dump(), analysis_status=status)
