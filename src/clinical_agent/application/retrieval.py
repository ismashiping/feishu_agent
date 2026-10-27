"""Text-to-evidence orchestration, independent of model libraries and PostgreSQL."""

from collections.abc import Callable
from time import monotonic
from typing import Protocol

from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.retrieval import (
    RetrievalError,
    RetrievalLimits,
    RetrievalOptions,
    RetrievalRequest,
    RetrievalResult,
    validate_query_embedding,
)


class QueryEmbedder(Protocol):
    def embed_query(self, text: str) -> QueryEmbedding: ...


class EvidenceRetriever(Protocol):
    def search(self, query: QueryEmbedding, options: RetrievalOptions) -> RetrievalResult: ...


class RetrievalService:
    def __init__(
        self,
        *,
        embedder: QueryEmbedder,
        retriever: EvidenceRetriever,
        limits: RetrievalLimits | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._embedder, self._retriever = embedder, retriever
        self._limits = RetrievalLimits.model_validate(limits or RetrievalLimits())
        self._clock = clock

    def _check_time(self, deadline: float) -> None:
        if self._clock() >= deadline:
            raise RetrievalError("retrieval_timeout")

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        request = RetrievalRequest.model_validate(request)
        deadline = self._clock() + self._limits.max_seconds
        self._check_time(deadline)
        try:
            query = QueryEmbedding.model_validate(self._embedder.embed_query(request.question))
        except Exception:
            raise RetrievalError("retrieval_embedding_failed") from None
        query = validate_query_embedding(query)
        self._check_time(deadline)
        try:
            result = RetrievalResult.model_validate(self._retriever.search(query, request.options))
            if result.options != request.options or result.embedding_info != query.embedding_info:
                raise ValueError("Retriever returned a different query contract")
        except RetrievalError as error:
            # Rebuild controlled errors; never publish an external exception's message.
            raise RetrievalError(error.code) from None
        except Exception:
            raise RetrievalError("retrieval_failed") from None
        self._check_time(deadline)
        return result
