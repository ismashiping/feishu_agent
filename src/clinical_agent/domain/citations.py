"""Deterministic citation gate; it checks identity, not medical entailment."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from clinical_agent.domain.research import (
    CitationEvidence,
    CitationSource,
    EvidenceClaim,
    GenerationDraft,
    QuestionRequest,
    ResearchAnswer,
    ResearchError,
)
from clinical_agent.domain.retrieval import DocumentSummary, RetrievalResult

BASE_LIMITATIONS = [
    "仅检索本地已导入文献，不保证覆盖最新或全部研究。",
    "已检查引用标识与来源关联，尚未自动验证结论的医学语义支持关系，需人工复核。",
    "本结果用于医学科研辅助，不用于个体诊断或治疗决策。",
]


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("Non-JSON constant")


def parse_draft(raw: str, *, max_bytes: int) -> GenerationDraft:
    try:
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > max_bytes:
            raise ValueError("Invalid output size or type")
        data = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        result = GenerationDraft.model_validate(data)
    except (ValueError, TypeError, RecursionError):
        raise ResearchError("model_output_invalid") from None
    for claim in result.claims:
        if len(set(claim.evidence_chunk_ids)) != len(claim.evidence_chunk_ids):
            raise ResearchError("citation_invalid")
    return result


def build_answer(
    request: QuestionRequest,
    retrieval: RetrievalResult,
    draft: GenerationDraft | None,
    *,
    generated_at: datetime,
) -> ResearchAnswer:
    request = QuestionRequest.model_validate(request)
    try:
        retrieval = RetrievalResult.model_validate(retrieval).model_copy(deep=True)
        if retrieval.options != request.options:
            raise ValueError("Mismatched retrieval options")
        limitations = list(BASE_LIMITATIONS)
        if not retrieval.hits:
            if draft is not None:
                raise ValueError("Empty retrieval cannot have a draft")
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                generated_at=generated_at,
                limitations=[*limitations, "未检索到符合条件的证据，不代表证据证明无效。"],
            )
        if draft is None:
            raise ValueError("A nonempty retrieval requires a draft")
        draft = GenerationDraft.model_validate(draft)
        by_id = {hit.chunk.chunk_id: hit for hit in retrieval.hits}
        summaries: dict[UUID, DocumentSummary] = {}
        for hit in retrieval.hits:
            previous = summaries.setdefault(hit.document.document_id, hit.document)
            if previous != hit.document:
                raise ValueError("Conflicting document snapshots")
        sources: dict[UUID, CitationSource] = {}
        claims = []
        used = set()
        for index, claim in enumerate(draft.claims, 1):
            if len(set(claim.evidence_chunk_ids)) != len(claim.evidence_chunk_ids):
                raise ValueError("Duplicate claim citations")
            for identity in claim.evidence_chunk_ids:
                if identity not in by_id:
                    raise ValueError("Unknown evidence identity")
                hit = by_id[identity]
                if identity in used:
                    continue
                used.add(identity)
                document_id = hit.document.document_id
                if document_id not in sources:
                    data = hit.document.model_dump(
                        include=set(CitationSource.model_fields) - {"evidence"}
                    )
                    # Construct only after the first evidence is available.
                    data["evidence"] = [
                        CitationEvidence(
                            chunk_id=identity, text=hit.chunk.text, location=hit.chunk.location
                        )
                    ]
                    sources[document_id] = CitationSource.model_validate(data)
                else:
                    sources[document_id].evidence.append(
                        CitationEvidence(
                            chunk_id=identity, text=hit.chunk.text, location=hit.chunk.location
                        )
                    )
            claims.append(EvidenceClaim(claim_id=f"c{index}", **claim.model_dump()))
        scopes = {source.content_scope for source in sources.values()}
        if "abstract" in scopes:
            limitations.append("部分来源仅包含摘要，不能视为已阅读全文。")
        if "extracted_text" in scopes:
            limitations.append("部分来源为PDF文本层提取，未验证版面、表格或全文完整性。")
        return ResearchAnswer(
            request_id=request.request_id,
            status="answered",
            claims=claims,
            sources=list(sources.values()),
            limitations=limitations,
            generated_at=generated_at,
        )
    except (ValueError, ValidationError):
        raise ResearchError("citation_invalid") from None
