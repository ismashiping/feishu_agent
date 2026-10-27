"""Synchronous offline ingestion; all infrastructure dependencies are explicit ports."""

from collections.abc import Callable
from time import monotonic
from typing import Protocol, TypeVar

from clinical_agent.domain.chunking import (
    ChunkingPolicy,
    ChunkingResult,
    TokenizerProfile,
    chunk_source,
)
from clinical_agent.domain.embedding import EmbeddedChunk
from clinical_agent.domain.ingestion import (
    BatchIngestionResult,
    ImportRequest,
    IngestionError,
    IngestionLimits,
    IngestionResult,
    OperationCode,
    ParsedBatch,
    ParsedSource,
    PreparedIngestion,
    StoreResult,
    chunk_id_for,
)

T = TypeVar("T")


class SourceReader(Protocol):
    def read(self, request: ImportRequest) -> ParsedBatch: ...


class Embedder(Protocol):
    @property
    def tokenizer_profile(self) -> TokenizerProfile: ...

    def count_tokens(self, text: str) -> int: ...

    def embed_chunks(self, source: ChunkingResult) -> list[EmbeddedChunk]: ...


class IngestionStore(Protocol):
    def save(self, prepared: PreparedIngestion) -> StoreResult: ...


class IngestionService:
    def __init__(
        self,
        *,
        reader: SourceReader,
        embedder: Embedder,
        store: IngestionStore,
        policy: ChunkingPolicy | None = None,
        limits: IngestionLimits | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._reader, self._embedder, self._store = reader, embedder, store
        self._policy = ChunkingPolicy.model_validate(policy or ChunkingPolicy())
        self._limits = IngestionLimits.model_validate(limits or IngestionLimits())
        self._clock = clock

    def _call(self, deadline: float, code: OperationCode, operation: Callable[[], T]) -> T:
        if self._clock() >= deadline:
            raise IngestionError("ingestion_timeout")
        try:
            return operation()
        except Exception as error:
            if (
                code == "source_failed"
                and isinstance(error, IngestionError)
                and error.code == "batch_limit"
            ):
                raise IngestionError("batch_limit") from None
            raise IngestionError(code) from None

    def ingest(self, request: ImportRequest) -> BatchIngestionResult:
        request = ImportRequest.model_validate(request)
        deadline = self._clock() + self._limits.max_seconds
        try:
            batch = self._call(
                deadline,
                "source_failed",
                lambda: ParsedBatch.model_validate(self._reader.read(request)),
            )
        except IngestionError as error:
            return BatchIngestionResult(entries=[], error_code=error.code)
        if len(batch.entries) > self._limits.max_documents:
            return BatchIngestionResult(entries=[], error_code="batch_limit")
        results = []
        for entry in batch.entries:
            if entry.source is None:
                results.append(
                    IngestionResult(
                        index=entry.index,
                        status="rejected",
                        document_id=None,
                        chunk_count=0,
                        error_code=entry.error_code,
                    )
                )
                continue
            results.append(self._ingest_source(entry.source, entry.index, deadline))
        return BatchIngestionResult(entries=results)

    def _ingest_source(self, source: ParsedSource, index: int, deadline: float) -> IngestionResult:
        try:
            profile = self._call(
                deadline, "chunking_failed", lambda: self._embedder.tokenizer_profile
            )
            chunks = self._call(
                deadline,
                "chunking_failed",
                lambda: chunk_source(
                    source.parsed,
                    tokenizer=self._embedder.count_tokens,
                    profile=profile,
                    policy=self._policy,
                    chunk_id_factory=lambda i: chunk_id_for(
                        source.parsed.document.document_id, profile, self._policy, i
                    ),
                ),
            )
            prepared = self._call(
                deadline,
                "embedding_failed",
                lambda: PreparedIngestion(
                    source=source, chunking=chunks, embedded=self._embedder.embed_chunks(chunks)
                ),
            )
            outcome = self._call(
                deadline,
                "storage_failed",
                lambda: StoreResult.model_validate(self._store.save(prepared)),
            )
            return IngestionResult(index=index, **outcome.model_dump(), error_code=None)
        except IngestionError as error:
            return IngestionResult(
                index=index, status="failed", document_id=None, chunk_count=0, error_code=error.code
            )
