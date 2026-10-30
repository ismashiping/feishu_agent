"""Text-to-evidence orchestration, independent of model libraries and PostgreSQL."""

from collections.abc import Callable
from time import monotonic
from typing import Protocol

from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.hybrid import keyword_text
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


class HybridEvidenceRetriever(Protocol):
    def search_hybrid(
        self,
        question: str,
        query: QueryEmbedding | None,
        options: RetrievalOptions,
        *,
        timeout_seconds: float,
    ) -> RetrievalResult: ...


class RetrievalService:
    def __init__(
        self,
        *,
        embedder: QueryEmbedder,
        retriever: EvidenceRetriever,
        limits: RetrievalLimits | None = None,
        hybrid_retriever: HybridEvidenceRetriever | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._embedder, self._retriever = embedder, retriever
        self._hybrid_retriever = hybrid_retriever
        self._limits = RetrievalLimits.model_validate(limits or RetrievalLimits())
        self._clock = clock

    def _check_time(self, deadline: float) -> None:
        if self._clock() >= deadline:
            raise RetrievalError("retrieval_timeout")

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        request = RetrievalRequest.model_validate(request)
        if request.scope != "local":
            raise RetrievalError("retrieval_failed")
        deadline = self._clock() + self._limits.max_seconds
        self._check_time(deadline)
        terms = (
            keyword_text(request.question, request.options)
            if request.options.mode != "vector"
            else request.question
        )
        query: QueryEmbedding | None = None
        if request.options.mode != "keyword":
            try:
                query = validate_query_embedding(
                    QueryEmbedding.model_validate(self._embedder.embed_query(request.question))
                )
            except RetrievalError:
                raise
            except Exception:
                raise RetrievalError("retrieval_embedding_failed") from None
        self._check_time(deadline)
        try:
            if request.options.mode == "vector":
                assert query is not None
                result = self._retriever.search(query, request.options)
            else:
                if self._hybrid_retriever is None:
                    raise RetrievalError("retrieval_failed")
                result = self._hybrid_retriever.search_hybrid(
                    terms, query, request.options, timeout_seconds=deadline - self._clock()
                )
            result = RetrievalResult.model_validate(result).model_copy(deep=True)
            if (
                result.options != request.options
                or result.scope != "local"
                or query is not None
                and result.embedding_info != query.embedding_info
            ):
                raise ValueError("Retriever returned a different query contract")
        except RetrievalError as error:
            raise RetrievalError(error.code) from None
        except Exception:
            raise RetrievalError("retrieval_failed") from None
        self._check_time(deadline)
        return result
