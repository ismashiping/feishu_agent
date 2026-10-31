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
        if retrieval.options != request.options or retrieval.scope != request.scope:
            raise ValueError("Mismatched retrieval options")
        limitations = list(BASE_LIMITATIONS)
        if retrieval.scope != "local":
            limitations[0] = (
                "已按记录查询 PubMed；结果有查询、日期、数量和摘要范围限制，"
                "不保证检全或覆盖全部最新研究。"
            )
            if retrieval.scope == "hybrid":
                limitations.append(
                    "按来源保留名额合并本地与在线结果；在线排名不参与本地关键词/向量排序。"
                )
            if retrieval.search_provenance and retrieval.search_provenance.status == "partial":
                limitations.append("PubMed 仅部分获取成功，回答不能视为完整检索结果。")
            if retrieval.search_provenance and retrieval.search_provenance.returned_count > len(
                retrieval.hits
            ):
                limitations.append("部分检索条目没有摘要或未进入回答证据范围。")
            if any(hit.document.source_notices for hit in retrieval.hits):
                limitations.append("部分来源有更正/关联出版记录标记，需核查原文及来源状态。")
        local_notes = []
        if retrieval.scope != "online" and retrieval.options.mode != "vector":
            local_notes.append("本地关键词通道为 simple ASCII 匹配，分数不代表医学可靠性。")
        if retrieval.options.date_from is not None:
            local_notes.append("本地日期过滤仅接纳已知完整出版日期，未知或年/月精度条目被排除。")
        if local_notes:
            limitations.append(" ".join(local_notes))
        if not retrieval.hits:
            if draft is not None:
                raise ValueError("Empty retrieval cannot have a draft")
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                generated_at=generated_at,
                local_channel_status=retrieval.channel_status
                if retrieval.scope != "online"
                else None,
                local_retrieval_mode=retrieval.options.mode,
                local_retrieval_strategy=retrieval.strategy_version,
                retrieval_warnings=retrieval.warnings,
                retrieval_scope=retrieval.scope,
                search_provenance=retrieval.search_provenance,
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
                        mode="json", include=set(CitationSource.model_fields) - {"evidence"}
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
            local_channel_status=retrieval.channel_status if retrieval.scope != "online" else None,
            local_retrieval_mode=retrieval.options.mode,
            local_retrieval_strategy=retrieval.strategy_version,
            retrieval_warnings=retrieval.warnings,
            retrieval_scope=retrieval.scope,
            search_provenance=retrieval.search_provenance,
        )
    except (ValueError, ValidationError):
        raise ResearchError("citation_invalid") from None
