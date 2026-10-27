"""Explicit local CPU model loading and bounded embedding operations."""

import hashlib
import importlib
import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal, Protocol, cast

from pydantic import ConfigDict, Field, TypeAdapter, ValidationError

from clinical_agent.domain.chunking import ChunkingResult, TokenizerProfile
from clinical_agent.domain.embedding import EmbeddedChunk, QueryEmbedding
from clinical_agent.domain.models import (
    DTO,
    EmbeddingInfo,
    EvidenceChunk,
    PositiveInteger,
    PreservedText,
    SnapshotHash,
)

MODEL_ID = "intfloat/multilingual-e5-base"
REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"
WEIGHT_HASH = "a18a44fad1d0b46ded15928144138cff1135d5cc8233bdd90be5f18822de09a7"
SNAPSHOT_FILES = frozenset(
    {
        "config.json",
        "modules.json",
        "sentence_bert_config.json",
        "1_Pooling/config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
        "model.safetensors",
    }
)
Seconds = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class EmbeddingLimits(DTO):
    batch_size: PositiveInteger = 8
    max_chunks: PositiveInteger = 128
    max_input_characters: PositiveInteger = 1_000_000
    max_query_characters: PositiveInteger = 8_192
    max_seconds: Seconds = 60.0
    lock_timeout_seconds: Seconds = 1.0
    load_max_seconds: Seconds = 300.0
    max_snapshot_bytes: PositiveInteger = 2 * 1024**3


class LocalModelConfig(DTO):
    snapshot_dir: Path
    limits: EmbeddingLimits = Field(default_factory=EmbeddingLimits)


class SnapshotManifest(DTO):
    model_id: Literal["intfloat/multilingual-e5-base"]
    revision: Literal["d128750597153bb5987e10b1c3493a34e5a4502a"]
    files: dict[str, SnapshotHash]


class EmbeddingError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EmbeddingBackend(Protocol):
    dimension: int
    max_tokens: int

    def count_tokens(self, text: str) -> int: ...

    def encode(self, texts: list[str], batch_size: int) -> list[list[float]]: ...


def _verify_snapshot(config: LocalModelConfig) -> Path:
    try:
        root = config.snapshot_dir.resolve(strict=True)
        manifest_path = (root / "manifest.json").resolve(strict=True)
        if not manifest_path.is_relative_to(root):
            raise ValueError("Invalid snapshot")
        with manifest_path.open("rb") as stream:
            data = stream.read(65_537)
        if len(data) > 65_536:
            raise ValueError("Invalid snapshot")
        manifest = SnapshotManifest.model_validate(json.loads(data))
        if (
            set(manifest.files) != SNAPSHOT_FILES
            or manifest.files["model.safetensors"] != WEIGHT_HASH
        ):
            raise ValueError("Invalid snapshot")
        total = 0
        for name, expected in manifest.files.items():
            path = (root / name).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("Invalid snapshot")
            total += path.stat().st_size
            if total > config.limits.max_snapshot_bytes:
                raise ValueError("Invalid snapshot")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError("Invalid snapshot")
        return root
    except (OSError, ValueError):
        raise EmbeddingError("embedding_snapshot_invalid") from None


class _SentenceTransformerBackend:
    def __init__(self, path: Path) -> None:
        # Import and load only when explicitly requested, never during module import.
        library = importlib.import_module("sentence_transformers")
        self._model = library.SentenceTransformer(
            str(path),
            device="cpu",
            local_files_only=True,
            trust_remote_code=False,
            token=False,
            model_kwargs={"use_safetensors": True},
        )
        self.dimension = self._model.get_embedding_dimension()
        self.max_tokens = self._model.max_seq_length

    def count_tokens(self, text: str) -> int:
        encoded = self._model.tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
            padding=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        return len(encoded["input_ids"])

    def encode(self, texts: list[str], batch_size: int) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            precision="float32",
            prompt="",
        )
        return cast(list[list[float]], vectors.tolist())


def load_local_embedder(
    config: LocalModelConfig,
    *,
    loader: Callable[[Path], EmbeddingBackend] | None = None,
    clock: Callable[[], float] = monotonic,
) -> "LocalEmbedder":
    config = LocalModelConfig.model_validate(config)
    start = clock()
    path = _verify_snapshot(config)
    if clock() - start >= config.limits.load_max_seconds:
        raise EmbeddingError("embedding_timeout")
    try:
        backend = (loader or _SentenceTransformerBackend)(path)
    except Exception:
        raise EmbeddingError("embedding_load_failed") from None
    if clock() - start >= config.limits.load_max_seconds:
        raise EmbeddingError("embedding_timeout")
    return LocalEmbedder(backend, limits=config.limits, clock=clock)


class LocalEmbedder:
    def __init__(
        self,
        backend: EmbeddingBackend,
        *,
        limits: EmbeddingLimits,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if backend.dimension != 768 or backend.max_tokens != 512:
            raise EmbeddingError("embedding_model_mismatch")
        self._backend = backend
        self._limits = EmbeddingLimits.model_validate(limits)
        self._clock = clock
        self._lock = threading.Lock()

    @property
    def tokenizer_profile(self) -> TokenizerProfile:
        return TokenizerProfile(
            model_id=MODEL_ID,
            model_revision=REVISION,
            tokenizer_revision=REVISION,
            document_prefix="passage: ",
            model_max_tokens=512,
        )

    def _info(self) -> EmbeddingInfo:
        return EmbeddingInfo(
            model_id=MODEL_ID,
            model_revision=REVISION,
            tokenizer_revision=REVISION,
            dimension=768,
            normalized=True,
            chunking_version="source-unit-v1",
        )

    def _check_time(self, deadline: float) -> None:
        if self._clock() >= deadline:
            raise EmbeddingError("embedding_timeout")

    @contextmanager
    def _operation(self) -> Iterator[float]:
        deadline = self._clock() + self._limits.max_seconds
        if not self._lock.acquire(
            timeout=min(self._limits.lock_timeout_seconds, self._limits.max_seconds)
        ):
            raise EmbeddingError("embedding_busy")
        try:
            self._check_time(deadline)
            yield deadline
            self._check_time(deadline)
        finally:
            self._lock.release()

    def _count(self, text: str, deadline: float) -> int:
        self._check_time(deadline)
        try:
            count = self._backend.count_tokens(text)
        except Exception:
            raise EmbeddingError("embedding_backend_failed") from None
        self._check_time(deadline)
        if type(count) is not int or count <= 0:
            raise EmbeddingError("embedding_output_invalid")
        return count

    def count_tokens(self, text: str) -> int:
        text = TypeAdapter(
            PreservedText, config=ConfigDict(strict=True, hide_input_in_errors=True)
        ).validate_python(text)
        if len(text) > self._limits.max_input_characters:
            raise EmbeddingError("embedding_input_limit")
        with self._operation() as deadline:
            return self._count(text, deadline)

    def _encode(self, texts: list[str], deadline: float) -> list[list[float]]:
        self._check_time(deadline)
        try:
            vectors = self._backend.encode(texts, batch_size=self._limits.batch_size)
        except Exception:
            raise EmbeddingError("embedding_backend_failed") from None
        self._check_time(deadline)
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingError("embedding_output_invalid")
        return vectors

    def embed_query(self, text: str) -> QueryEmbedding:
        text = TypeAdapter(
            PreservedText, config=ConfigDict(strict=True, hide_input_in_errors=True)
        ).validate_python(text)
        if len(text) > self._limits.max_query_characters:
            raise EmbeddingError("embedding_input_limit")
        prepared = "query: " + text
        with self._operation() as deadline:
            if self._count(prepared, deadline) > 512:
                raise EmbeddingError("embedding_token_limit")
            vectors = self._encode([prepared], deadline)
            try:
                result = QueryEmbedding(embedding_info=self._info(), vector=vectors[0])
            except ValidationError:
                raise EmbeddingError("embedding_output_invalid") from None
        return result

    def embed_chunks(self, source: ChunkingResult) -> list[EmbeddedChunk]:
        source = ChunkingResult.model_validate(source)
        if source.profile != self.tokenizer_profile or any(
            item.evidence.embedding_info is not None for item in source.chunks
        ):
            raise EmbeddingError("embedding_identity_mismatch")
        if (
            len(source.chunks) > self._limits.max_chunks
            or sum(len(item.evidence.text) for item in source.chunks)
            > self._limits.max_input_characters
        ):
            raise EmbeddingError("embedding_input_limit")
        if not source.chunks:
            return []
        prepared = ["passage: " + item.evidence.text for item in source.chunks]
        result: list[EmbeddedChunk] = []
        with self._operation() as deadline:
            for text, item in zip(prepared, source.chunks, strict=True):
                count = self._count(text, deadline)
                if count > source.policy.max_tokens:
                    raise EmbeddingError("embedding_token_limit")
                if count != item.token_count:
                    raise EmbeddingError("embedding_token_count_mismatch")
            for start in range(0, len(prepared), self._limits.batch_size):
                vectors = self._encode(prepared[start : start + self._limits.batch_size], deadline)
                try:
                    for index, vector in enumerate(vectors, start):
                        evidence = EvidenceChunk.model_validate(
                            {
                                **source.chunks[index].evidence.model_dump(),
                                "embedding_info": self._info(),
                            }
                        )
                        result.append(EmbeddedChunk(evidence=evidence, vector=vector))
                except ValidationError:
                    raise EmbeddingError("embedding_output_invalid") from None
        return result
