"""Assemble evidence-bound reports and review them with finite budgets."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Literal, Protocol
from uuid import UUID, uuid4

from clinical_agent.application.pico import _invalid_constant, _unique
from clinical_agent.domain.analysis import AnalysisResult, EvidencePointer
from clinical_agent.domain.pubmed import PubMedRecord
from clinical_agent.domain.report import (
    CitationVerification,
    Reference,
    ReportClaim,
    ResearchReport,
    ReviewDraft,
)
from clinical_agent.domain.research import (
    CitationSource,
    QuestionRequest,
    ResearchError,
    ResearchLimits,
)
from clinical_agent.domain.retrieval import RetrievalResult

CheckStatus = Literal["valid", "invalid", "unavailable"]


class ReviewModel(Protocol):
    def review_claims(self, context: dict[str, object], *, timeout_seconds: float) -> str: ...


class SnapshotPort(Protocol):
    def check(self, source: CitationSource, retrieval: RetrievalResult) -> CheckStatus: ...


class MetadataPort(Protocol):
    def fetch_metadata(self, ids: list[str], *, timeout_seconds: float) -> list[PubMedRecord]: ...


def collect_claims(analysis: AnalysisResult) -> list[ReportClaim]:
    claims: list[ReportClaim] = []

    def add(
        section: Literal[3, 4, 5, 6, 7],
        text: str,
        kind: Literal["reported_fact", "model_inference", "unverified_hypothesis"],
        evidence: list[EvidencePointer],
        verify: str | None = None,
    ) -> None:
        claims.append(
            ReportClaim(
                claim_id=f"c{len(claims) + 1}",
                section=section,
                text=text,
                epistemic_kind=kind,
                evidence=evidence,
                verification_needed=verify,
            )
        )

    for study in analysis.studies:
        add(
            3,
            f"研究设计分类：{study.study_type}；判定来源：{study.type_basis}",
            "model_inference",
            study.type_evidence,
            "核对出版类型与研究设计原文",
        )
        claims[-1].information_missing = study.study_type == "unknown"
        for name, item in sorted(study.fields.items()):
            if item.value is not None:
                add(
                    6 if name in {"limitations", "quality_signals"} else 4,
                    f"{name}：{item.value}",
                    item.epistemic_kind,
                    item.evidence,
                    item.verification_needed,
                )
    for similarity in analysis.idea_similarities:
        for dimension, dimension_item in sorted(similarity.dimensions.items()):
            add(
                5,
                f"{dimension}：{dimension_item.relation}；{dimension_item.reason}",
                "model_inference",
                dimension_item.evidence,
                "结合用户原始约束及文献复核相似性",
            )
            claims[-1].information_missing = dimension_item.relation == "unknown"
    for comparison in analysis.comparisons:
        add(
            6,
            f"{comparison.relation}；可比性：{comparison.comparability}；{comparison.reason}",
            "model_inference",
            comparison.evidence,
            "复核两侧研究设计、人群与结局",
        )
    for gap in analysis.candidate_gaps:
        refs = gap.description.evidence + gap.counter_evidence
        add(
            6,
            f"{gap.description.value}；推理：{gap.reasoning}；范围：{gap.scope}",
            gap.description.epistemic_kind,
            refs,
            gap.description.verification_needed,
        )
        add(
            7,
            f"可供进一步调查的方向：{gap.description.value}",
            "unverified_hypothesis",
            refs,
            gap.description.verification_needed,
        )
    for item in analysis.feasibility:
        judgment = item.assessment
        add(
            6,
            f"可行性（{item.dimension}；{item.status}）："
            f"{judgment.value or '证据不足，条件待确认'}；下一步核查：{item.next_check}",
            judgment.epistemic_kind,
            judgment.evidence,
            judgment.verification_needed,
        )
        claims[-1].information_missing = judgment.value is None
    for experiment in analysis.experiments:
        for name in ("hypothesis", "baseline", "experiment", "metrics", "failure_criterion"):
            item = getattr(experiment, name)
            add(
                7,
                f"候选最小实验（缺口{experiment.gap_index + 1}；{name}）：{item.value}",
                item.epistemic_kind,
                item.evidence,
                item.verification_needed,
            )
    return claims


class ReportBuilder:
    def __init__(
        self,
        *,
        reviewer: ReviewModel,
        snapshots: SnapshotPort,
        metadata: MetadataPort | None = None,
        limits: ResearchLimits | None = None,
        clock: Callable[[], float] = monotonic,
        model_id: str | None = None,
    ) -> None:
        self.reviewer, self.snapshots, self.metadata = reviewer, snapshots, metadata
        self.limits, self.clock, self.model_id = limits or ResearchLimits(), clock, model_id

    def build(
        self,
        request: QuestionRequest,
        analysis: AnalysisResult,
        retrieval: RetrievalResult | None,
        *,
        timeout_seconds: float = 60.0,
        search_started_at: datetime | None = None,
    ) -> ResearchReport:
        from math import isfinite

        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("research_timeout")
        deadline = self.clock() + timeout_seconds
        analysis = AnalysisResult.model_validate(analysis).model_copy(deep=True)
        if analysis.request_id != request.request_id or analysis.original_idea != request.question:
            raise ResearchError("citation_invalid")
        # Rebind all supplied metadata/chunks to the actual retrieval, before any review.
        if retrieval is not None:
            from clinical_agent.domain.citations import build_answer
            from clinical_agent.domain.research import DraftClaim, GenerationDraft

            trusted = build_answer(
                request,
                retrieval,
                GenerationDraft(
                    claims=[
                        DraftClaim(
                            text="Supplied passage.",
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
            ).sources
            if analysis.sources != trusted:
                raise ResearchError("citation_invalid")
        elif analysis.sources or analysis.analysis_status != "needs_clarification":
            raise ResearchError("citation_invalid")
        claims = collect_claims(analysis)
        sources = {s.document_id: s for s in analysis.sources}
        chunks = {e.chunk_id: (s, e) for s in analysis.sources for e in s.evidence}
        used: dict[UUID, CitationSource] = {}
        for claim in claims:
            for pointer in claim.evidence:
                if pointer.chunk_id not in chunks:
                    raise ResearchError("citation_invalid")
                source, evidence = chunks[pointer.chunk_id]
                if pointer.quote not in evidence.text:
                    raise ResearchError("citation_invalid")
                used.setdefault(source.document_id, source)
        verifications = []
        for source in used.values():
            if self.clock() >= deadline:
                raise ResearchError("research_timeout")
            location = (
                self.snapshots.check(source, retrieval) if retrieval is not None else "unavailable"
            )
            verifications.append(
                CitationVerification(
                    source_id=source.document_id,
                    identity_status="unavailable" if source.pmid else "not_applicable",
                    metadata_status="unavailable" if source.pmid else "not_applicable",
                    location_status=location,
                    checked_at=datetime.now(UTC),
                    errors=[] if location == "valid" else ["source_snapshot_" + location],
                )
            )
        notes = ["支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。"]
        pmids = list(dict.fromkeys(s.pmid for s in used.values() if s.pmid))
        if pmids and self.metadata is not None:
            try:
                records = self.metadata.fetch_metadata(
                    pmids, timeout_seconds=min(30.0, max(0.0, deadline - self.clock()))
                )
                by_pmid = {r.pmid: r for r in records}
                for verification in verifications:
                    source = sources[verification.source_id]
                    if not source.pmid:
                        continue
                    record = by_pmid.get(source.pmid)
                    if record is None:
                        verification.errors.append("official_metadata_unavailable")
                        continue

                    def normalize(text: str) -> str:
                        return " ".join(text.split()).casefold()

                    valid = normalize(source.title) == normalize(record.title) and (
                        not source.doi
                        or not record.doi
                        or source.doi.casefold() == record.doi.casefold()
                    )
                    verification.identity_status = "valid" if valid else "invalid"
                    verification.metadata_status = "valid" if valid else "invalid"
                    if valid and (
                        source.authors != record.authors
                        or source.publication_date != record.publication_date
                        or source.journal != record.journal
                        or (source.doi and not record.doi)
                    ):
                        verification.metadata_status = "unavailable"
                        verification.errors.append("metadata_fields_require_review")
                    if not valid:
                        verification.errors.append("official_metadata_mismatch")
                    if any(
                        "retract" in s.casefold() for s in record.notices + record.publication_types
                    ):
                        verification.identity_status = "invalid"
                        verification.errors.append("retracted_source")
                    elif record.notices:
                        verification.metadata_status = "unavailable"
                        verification.errors.append("correction_requires_review")
            except Exception:
                notes.append("官方元数据服务不可用；保留原文献身份，未将其判为无效。")
        if claims:
            context: dict[str, object] = {
                "claims": [c.model_dump(mode="json") for c in claims],
                "sources": [
                    s.model_dump(mode="json", exclude={"snapshot_xml", "openalex_record"})
                    for s in analysis.sources
                ],
                "output_schema": ReviewDraft.model_json_schema(),
            }
            if len(json.dumps(context, ensure_ascii=False)) > self.limits.max_context_characters:
                notes.append("支持度审核上下文超预算，所有条目保持 uncertain。")
            else:
                try:
                    raw = self.reviewer.review_claims(
                        context,
                        timeout_seconds=min(
                            self.limits.generation_seconds, max(0.0, deadline - self.clock())
                        ),
                    )
                    if not isinstance(raw, str) or len(raw.encode()) > self.limits.max_output_bytes:
                        raise ValueError("Review output budget")
                    draft = ReviewDraft.model_validate(
                        json.loads(raw, object_pairs_hook=_unique, parse_constant=_invalid_constant)
                    )
                    reviews = {r.claim_id: r for r in draft.reviews}
                    if set(reviews) != {c.claim_id for c in claims} or len(reviews) != len(
                        draft.reviews
                    ):
                        raise ValueError("Review must cover exactly all claims")
                    for claim in claims:
                        review = reviews[claim.claim_id]
                        claim.support_status = (
                            review.support_status
                            if claim.evidence and not claim.information_missing
                            else "uncertain"
                        )
                        claim.basis = review.basis
                except Exception:
                    notes.append("支持度审核不可用或响应无效，保持 uncertain；未删除原结论。")
        if self.clock() >= deadline:
            raise ResearchError("research_timeout")
        rejected = any(
            v.identity_status == "invalid"
            or v.metadata_status == "invalid"
            or v.location_status == "invalid"
            for v in verifications
        ) or any(c.support_status == "unsupported" for c in claims)
        incomplete = (
            any(
                v.identity_status == "unavailable"
                or v.metadata_status == "unavailable"
                or v.location_status == "unavailable"
                for v in verifications
            )
            or any(c.support_status != "supported" for c in claims)
            or analysis.analysis_status in {"needs_clarification", "not_evaluated"}
        )
        content: Literal["complete", "partial", "insufficient_evidence", "needs_clarification"] = (
            "complete"
            if analysis.analysis_status == "completed"
            else "needs_clarification"
            if analysis.analysis_status == "needs_clarification"
            else "insufficient_evidence"
            if analysis.analysis_status == "insufficient_evidence"
            else "partial"
        )
        return ResearchReport(
            report_id=uuid4(),
            request_id=request.request_id,
            original_idea=request.question,
            question=request.question,
            content_status=content,
            status="rejected"
            if rejected
            else "verification_incomplete"
            if incomplete
            else "verified",
            analysis=analysis,
            search_started_at=search_started_at or analysis.generated_at,
            generated_at=datetime.now(UTC),
            claims=claims,
            references=[Reference(number=i, source=s) for i, s in enumerate(used.values(), 1)],
            verification=verifications,
            review_model_id=self.model_id,
            verification_notes=notes,
        )
