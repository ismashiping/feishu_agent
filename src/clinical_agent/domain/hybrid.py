"""Rank-only fusion; evidence identity is preserved independently of channel scores."""

from uuid import UUID

from clinical_agent.domain.retrieval import (
    EvidenceHit,
    RetrievalError,
    RetrievalOptions,
    RetrievalResult,
    retrieval_embedding_info,
)


def keyword_text(question: str, options: RetrievalOptions) -> str:
    value = options.keyword_query or question
    if not value.isascii() or not value.strip():
        raise RetrievalError("retrieval_language_unsupported")
    return value


def rank_fusion(
    keyword: list[EvidenceHit], vector: list[EvidenceHit], options: RetrievalOptions
) -> RetrievalResult:
    options = RetrievalOptions.model_validate(options)
    if options.mode != "hybrid":
        raise RetrievalError("retrieval_failed")
    sources: dict[str, EvidenceHit] = {}
    channels: dict[str, list[UUID]] = {"keyword": [], "vector": []}
    for channel, candidates in [("keyword", keyword), ("vector", vector)]:
        seen: set[str] = set()
        for candidate in candidates:
            candidate = EvidenceHit.model_validate(candidate)
            identity = str(candidate.chunk.chunk_id)
            if identity in sources and (
                sources[identity].chunk != candidate.chunk
                or sources[identity].document != candidate.document
            ):
                raise RetrievalError("retrieval_corrupt")
            if identity in seen:
                continue
            seen.add(identity)
            if len(seen) > options.candidate_limit:
                break
            sources[identity] = candidate
            channels[channel].append(candidate.chunk.chunk_id)
    hits: list[EvidenceHit] = []
    for chunk_id, keyword_rank, vector_rank, score in rank_candidates(
        channels["keyword"], channels["vector"], options
    ):
        data = sources[str(chunk_id)].model_dump()
        data.update(
            score=score,
            score_type="rrf",
            keyword_rank=keyword_rank,
            vector_rank=vector_rank,
            fusion_score=score,
        )
        hits.append(EvidenceHit.model_validate(data))
    hits.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id.int))
    return RetrievalResult(
        options=options,
        embedding_info=retrieval_embedding_info(),
        hits=[
            hit.model_copy(update={"rank": index})
            for index, hit in enumerate(hits[: options.top_k], 1)
        ],
        channel_status={"keyword": "ok", "vector": "ok"},
        strategy_version="rrf-v1",
    )


def rank_candidates(
    keyword: list[UUID], vector: list[UUID], options: RetrievalOptions
) -> list[tuple[UUID, int | None, int | None, float]]:
    ranks: dict[UUID, dict[str, int]] = {}
    for channel, candidates in [("keyword", keyword), ("vector", vector)]:
        unique = list(dict.fromkeys(candidates))[: options.candidate_limit]
        for rank, identity in enumerate(unique, 1):
            ranks.setdefault(identity, {})[channel] = rank
    values = [
        (
            identity,
            positions.get("keyword"),
            positions.get("vector"),
            sum(1.0 / (60 + rank) for rank in positions.values()),
        )
        for identity, positions in ranks.items()
    ]
    return sorted(values, key=lambda item: (-item[3], item[0].int))[: options.top_k]
