"""Bounded source slicing; model tokenization is an injected, non-truncating boundary."""

from collections.abc import Callable, Iterator
from typing import Literal, Self
from uuid import UUID

from pydantic import model_validator

from clinical_agent.domain.models import (
    DTO,
    EvidenceChunk,
    EvidenceLocation,
    MetadataText,
    ParsedPdf,
    ParsedPubmedArticle,
    PositiveInteger,
    SourceMetadata,
)


class TokenizerProfile(DTO):
    model_id: MetadataText
    model_revision: MetadataText
    tokenizer_revision: MetadataText
    document_prefix: str
    model_max_tokens: PositiveInteger


class ChunkingPolicy(DTO):
    max_tokens: PositiveInteger = 512
    max_input_characters: PositiveInteger = 1_000_000
    max_chunk_characters: PositiveInteger = 2_048
    max_tokenizer_calls: PositiveInteger = 100_000
    max_chunks: PositiveInteger = 10_000
    chunking_version: Literal["source-unit-v1"] = "source-unit-v1"


class TokenizedChunk(DTO):
    evidence: EvidenceChunk
    token_count: PositiveInteger


class ChunkingResult(DTO):
    profile: TokenizerProfile
    policy: ChunkingPolicy
    chunks: list[TokenizedChunk]

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        if self.policy.max_tokens > self.profile.model_max_tokens:
            raise ValueError("Chunk budget must not exceed the model limit")
        ids = [item.evidence.chunk_id for item in self.chunks]
        if len(ids) != len(set(ids)) or len(ids) > self.policy.max_chunks:
            raise ValueError("Chunks must have distinct IDs and fit the count budget")
        if any(item.token_count > self.policy.max_tokens for item in self.chunks):
            raise ValueError("Chunk token counts must fit the configured budget")
        return self


class ChunkingError(ValueError):
    """Fixed operational code; never include manuscript text or callback exceptions."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _units(
    parsed: ParsedPdf | ParsedPubmedArticle,
) -> Iterator[tuple[str, Literal["pdf_page", "abstract"], int | None, str | None, int]]:
    if isinstance(parsed, ParsedPdf):
        for page in parsed.source_units:
            yield page.text, "pdf_page", page.page, None, 0
    else:
        for section in parsed.source_units:
            yield section.text, "abstract", None, section.label, section.start


def chunk_source(
    parsed: ParsedPdf | ParsedPubmedArticle,
    *,
    tokenizer: Callable[[str], int],
    profile: TokenizerProfile,
    policy: ChunkingPolicy,
    chunk_id_factory: Callable[[int], UUID],
) -> ChunkingResult:
    """Count prefix + slice including special tokens, without padding or truncation.

    The injected counter must honor this contract; a truncated count cannot be detected
    here. Real tokenizer identity and encoding parity belong to the model adapter.
    Each probe adds one code point; the first over-budget probe closes a chunk.
    """
    parsed = type(parsed).model_validate(parsed)
    profile = TokenizerProfile.model_validate(profile)
    policy = ChunkingPolicy.model_validate(policy)
    if policy.max_tokens > profile.model_max_tokens:
        raise ChunkingError("chunk_model_limit")
    if sum(len(unit[0]) for unit in _units(parsed)) > policy.max_input_characters:
        raise ChunkingError("chunk_input_limit")
    source = SourceMetadata.model_validate(
        parsed.document.model_dump(include=set(SourceMetadata.model_fields))
    )
    chunks: list[TokenizedChunk] = []
    identities: set[UUID] = set()
    calls = 0
    for text, kind, page, section, offset in _units(parsed):
        start = 0
        while start < len(text):
            # Skip only the whitespace preceding a new chunk, never rewrite a slice.
            while start < len(text) and text[start].isspace():
                start += 1
            if start == len(text):
                break
            if len(chunks) >= policy.max_chunks:
                raise ChunkingError("chunk_count_limit")
            end, accepted_count = start, 0
            for candidate in range(
                start + 1, min(len(text), start + policy.max_chunk_characters) + 1
            ):
                if calls >= policy.max_tokenizer_calls:
                    raise ChunkingError("chunk_call_limit")
                calls += 1
                try:
                    count = tokenizer(profile.document_prefix + text[start:candidate])
                except Exception:
                    raise ChunkingError("chunk_tokenizer_failed") from None
                if type(count) is not int or count <= 0:
                    raise ChunkingError("chunk_tokenizer_invalid")
                if count > policy.max_tokens:
                    break
                end, accepted_count = candidate, count
            if end == start:
                raise ChunkingError("chunk_unfit_character")
            identity = chunk_id_factory(len(chunks) + 1)
            if not isinstance(identity, UUID) or identity in identities:
                raise ChunkingError("chunk_id_invalid")
            identities.add(identity)
            chunk = EvidenceChunk(
                chunk_id=identity,
                document_id=parsed.document.document_id,
                text=text[start:end],
                location=EvidenceLocation(
                    kind=kind, page=page, section=section, start=offset + start, end=offset + end
                ),
                embedding_info=None,
                source_metadata=source,
            )
            parsed.validate_chunk(chunk)
            chunks.append(TokenizedChunk(evidence=chunk, token_count=accepted_count))
            start = end
    return ChunkingResult(profile=profile, policy=policy, chunks=chunks)
