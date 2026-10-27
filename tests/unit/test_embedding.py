"""Embedding boundaries with explicit backend doubles; no model imports/downloads."""

import copy
import json
import threading
from uuid import UUID

import pytest
from pydantic import ValidationError

REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"


class Backend:
    dimension = 768
    max_tokens = 512

    def __init__(self):
        self.inputs = []
        self.counted = []
        self.output = None

    def count_tokens(self, text):
        self.counted.append(text)
        return len(text) + 2

    def encode(self, texts, batch_size):
        self.inputs.append((texts, batch_size))
        if self.output is not None:
            return self.output
        return [[1.0] + [0.0] * 767 for _ in texts]


def instance(backend=None, **limits):
    from clinical_agent.adapters.embedding import EmbeddingLimits, LocalEmbedder

    return LocalEmbedder(
        backend if backend is not None else Backend(), limits=EmbeddingLimits(**limits)
    )


def chunks(texts=("中文 α🙂", "English evidence")):
    from clinical_agent.domain.chunking import ChunkingResult

    profile = instance().tokenizer_profile
    return ChunkingResult.model_validate(
        {
            "profile": profile,
            "policy": {"max_tokens": 512},
            "chunks": [
                {
                    "token_count": len("passage: " + text) + 2,
                    "evidence": {
                        "chunk_id": UUID(int=i + 10),
                        "document_id": UUID(int=1),
                        "text": text,
                        "location": {
                            "kind": "pdf_page",
                            "page": i + 1,
                            "start": 0,
                            "end": len(text),
                        },
                        "embedding_info": None,
                        "source_metadata": {
                            "source_type": "pdf",
                            "source_uri": "file:///fixture.pdf",
                            "source_url": None,
                            "content_hash": "a" * 64,
                            "content_scope": "extracted_text",
                        },
                    },
                }
                for i, text in enumerate(texts)
            ],
        }
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("batch_size", 0),
        ("batch_size", True),
        ("max_chunks", 0),
        ("max_query_characters", "8"),
        ("max_input_characters", -1),
        ("max_seconds", float("inf")),
        ("lock_timeout_seconds", 0.0),
        ("load_max_seconds", -1.0),
        ("max_snapshot_bytes", True),
    ],
)
def test_limits_are_explicit_and_strict(field, value):
    from clinical_agent.adapters.embedding import EmbeddingLimits

    with pytest.raises(ValidationError):
        EmbeddingLimits(**{field: value})


def test_document_identity_order_prefix_and_input_unchanged():
    backend = Backend()
    embedder = instance(backend, batch_size=1)
    source = chunks()
    before = source.model_dump_json()
    result = embedder.embed_chunks(source)
    assert source.model_dump_json() == before
    assert backend.inputs == [(["passage: 中文 α🙂"], 1), (["passage: English evidence"], 1)]
    assert [x.evidence.chunk_id for x in result] == [x.evidence.chunk_id for x in source.chunks]
    for actual, original in zip(result, source.chunks, strict=True):
        info = actual.evidence.embedding_info
        assert info.model_id == "intfloat/multilingual-e5-base"
        assert info.model_revision == info.tokenizer_revision == REVISION
        assert info.dimension == 768 and info.normalized
        assert info.chunking_version == "source-unit-v1"
        restored = actual.evidence.model_dump()
        restored["embedding_info"] = None
        assert restored == original.evidence.model_dump()
        assert len(actual.vector) == 768
        assert type(actual).model_validate_json(actual.model_dump_json()) == actual


def test_query_and_count_prefix_contract():
    backend = Backend()
    embedder = instance(backend)
    assert embedder.count_tokens("passage: A") == 12
    result = embedder.embed_query("中文 query")
    assert backend.inputs == [(["query: 中文 query"], 8)]
    assert len(result.vector) == 768
    assert embedder.tokenizer_profile.document_prefix == "passage: "
    assert embedder.tokenizer_profile.model_max_tokens == 512


@pytest.mark.parametrize("text", ["", " \n ", 123, None])
def test_invalid_query(text):
    with pytest.raises(ValidationError):
        instance().embed_query(text)


def test_empty_batch_does_not_call_backend():
    backend = Backend()
    assert instance(backend).embed_chunks(chunks(())) == []
    assert backend.inputs == backend.counted == []


@pytest.mark.parametrize(
    "kind,code",
    [
        ("identity", "embedding_identity_mismatch"),
        ("count", "embedding_token_count_mismatch"),
        ("encoded", "embedding_identity_mismatch"),
        ("long", "embedding_token_limit"),
    ],
)
def test_preflight_rejects_before_encode(kind, code):
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    source = chunks(("x",)) if kind == "long" else chunks()
    if kind == "identity":
        source.profile.tokenizer_revision = "different"
    elif kind == "count":
        source.chunks[0].token_count += 1
    elif kind == "encoded":
        source.chunks[0].evidence.embedding_info = instance().embed_query("x").embedding_info
    # Long token_count is intentionally fabricated within policy; re-count must catch it.
    elif kind == "long":
        source.chunks[0].evidence.text = "x" * 503
        source.chunks[0].evidence.location.end = 503
        source.chunks[0].token_count = 512
    with pytest.raises(EmbeddingError, match=f"^{code}$"):
        instance(backend).embed_chunks(source)
    assert backend.inputs == []


def test_query_over_model_limit_is_rejected_without_truncation():
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    assert len(instance(backend).embed_query("x" * 503).vector) == 768  # 7 prefix + 503 + 2
    backend.inputs.clear()
    with pytest.raises(EmbeddingError, match="^embedding_token_limit$"):
        instance(backend).embed_query("x" * 504)
    assert backend.inputs == []


@pytest.mark.parametrize(
    "limits,query",
    [
        ({"max_query_characters": 1}, True),
        ({"max_chunks": 1}, False),
        ({"max_input_characters": 1}, False),
    ],
)
def test_request_limits(limits, query):
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    with pytest.raises(EmbeddingError, match="^embedding_input_limit$"):
        embedder = instance(backend, **limits)
        embedder.embed_query("long") if query else embedder.embed_chunks(chunks())
    assert backend.inputs == []


@pytest.mark.parametrize(
    "output",
    [
        [],
        [[1.0]],
        [[0.0] * 768],
        [[float("nan")] * 768],
        [[float("inf")] * 768],
        [[2.0] + [0.0] * 767],
        [[True] + [0.0] * 767],
        [["1"] + [0.0] * 767],
        [[1.0] + [0.0] * 767] * 2,
    ],
)
def test_malformed_backend_vectors_are_rejected(output):
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    backend.output = output
    with pytest.raises(EmbeddingError, match="^embedding_output_invalid$"):
        instance(backend).embed_query("x")


def test_backend_failure_is_sanitized_and_lock_released():
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    original = backend.encode

    def broken(*args, **kwargs):
        raise RuntimeError("secret path/manuscript")

    backend.encode = broken
    embedder = instance(backend)
    with pytest.raises(EmbeddingError, match="^embedding_backend_failed$") as error:
        embedder.embed_query("x")
    assert error.value.__suppress_context__
    backend.encode = original
    assert len(embedder.embed_query("x").vector) == 768


@pytest.mark.parametrize("field,value", [("dimension", 2), ("max_tokens", 128)])
def test_model_shape_checked(field, value):
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    setattr(backend, field, value)
    with pytest.raises(EmbeddingError, match="^embedding_model_mismatch$"):
        instance(backend)


def test_cooperative_timeout_after_inference():
    from clinical_agent.adapters.embedding import EmbeddingError, EmbeddingLimits, LocalEmbedder

    now = [0.0]
    backend = Backend()
    original = backend.encode

    def slow(*args, **kwargs):
        now[0] += 61.0
        return original(*args, **kwargs)

    backend.encode = slow
    embedder = LocalEmbedder(backend, limits=EmbeddingLimits(), clock=lambda: now[0])
    with pytest.raises(EmbeddingError, match="^embedding_timeout$"):
        embedder.embed_query("x")
    backend.encode = original
    assert len(embedder.embed_query("recovered").vector) == 768


def test_same_instance_concurrent_call_is_bounded():
    from clinical_agent.adapters.embedding import EmbeddingError

    entered, release = threading.Event(), threading.Event()
    backend = Backend()
    original = backend.encode

    def wait(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    backend.encode = wait
    embedder = instance(backend, lock_timeout_seconds=0.01)
    errors = []

    def worker():
        try:
            embedder.embed_query("first")
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        assert entered.wait(5)
        with pytest.raises(EmbeddingError, match="^embedding_busy$"):
            embedder.embed_query("second")
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive() and not errors


@pytest.mark.parametrize("case", ["missing", "invalid_json", "identity", "escape", "hash"])
def test_local_snapshot_validation(tmp_path, case):
    from clinical_agent.adapters.embedding import (
        EmbeddingError,
        LocalModelConfig,
        load_local_embedder,
    )

    if case != "missing":
        manifest = {
            "model_id": "intfloat/multilingual-e5-base",
            "revision": REVISION,
            "files": {"../escape": "a" * 64},
        }
        if case == "identity":
            manifest["revision"] = "main"
        if case == "hash":
            names = (
                "config.json",
                "modules.json",
                "sentence_bert_config.json",
                "1_Pooling/config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "sentencepiece.bpe.model",
                "model.safetensors",
            )
            manifest["files"] = {name: "a" * 64 for name in names}
        (tmp_path / "manifest.json").write_text(
            "{" if case == "invalid_json" else json.dumps(manifest), encoding="utf-8"
        )
    with pytest.raises(EmbeddingError, match="^embedding_snapshot_invalid$"):
        load_local_embedder(LocalModelConfig(snapshot_dir=tmp_path))


def test_mutated_input_is_revalidated():
    data = chunks()
    bad = copy.deepcopy(data)
    bad.chunks[0].evidence.location.end = 999
    with pytest.raises(ValidationError):
        instance().embed_chunks(bad)


@pytest.fixture
def local_fixture_snapshot(tmp_path, monkeypatch):
    """Small integrity fixture; explicitly replace only the trusted weight digest."""
    import hashlib

    from clinical_agent.adapters import embedding

    digests = {}
    for name in embedding.SNAPSHOT_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = ("synthetic fixture " + name).encode()
        path.write_bytes(content)
        digests[name] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(embedding, "WEIGHT_HASH", digests["model.safetensors"])
    manifest = {"model_id": embedding.MODEL_ID, "revision": embedding.REVISION, "files": digests}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_validated_snapshot_loader_receives_local_path(local_fixture_snapshot):
    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder

    seen = []
    backend = Backend()
    actual = load_local_embedder(
        LocalModelConfig(snapshot_dir=local_fixture_snapshot),
        loader=lambda path: seen.append(path) or backend,
    )
    assert seen == [local_fixture_snapshot.resolve()]
    assert len(actual.embed_query("fixture").vector) == 768


@pytest.mark.parametrize("case", ["missing_file", "corrupt", "manifest_size", "bytes"])
def test_snapshot_integrity_before_backend_loading(local_fixture_snapshot, case):
    from clinical_agent.adapters.embedding import (
        EmbeddingError,
        EmbeddingLimits,
        LocalModelConfig,
        load_local_embedder,
    )

    root = local_fixture_snapshot
    limits = EmbeddingLimits()
    if case == "missing_file":
        # Move this one known fixture file rather than removing a computed directory.
        (root / "tokenizer.json").rename(root / "missing-tokenizer.json")
    elif case == "corrupt":
        (root / "tokenizer.json").write_bytes(b"modified fixture")
    elif case == "manifest_size":
        (root / "manifest.json").write_bytes(b" " * 65_537)
    else:
        limits = EmbeddingLimits(max_snapshot_bytes=1)
    called = []
    with pytest.raises(EmbeddingError, match="^embedding_snapshot_invalid$"):
        load_local_embedder(
            LocalModelConfig(snapshot_dir=root, limits=limits),
            loader=lambda path: called.append(path) or Backend(),
        )
    assert not called


def test_loader_error_is_sanitized(local_fixture_snapshot):
    from clinical_agent.adapters.embedding import (
        EmbeddingError,
        LocalModelConfig,
        load_local_embedder,
    )

    def broken(path):
        raise RuntimeError("secret local path")

    with pytest.raises(EmbeddingError, match="^embedding_load_failed$") as error:
        load_local_embedder(LocalModelConfig(snapshot_dir=local_fixture_snapshot), loader=broken)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("when", ["before", "after"])
def test_load_cooperative_budget(local_fixture_snapshot, when):
    from clinical_agent.adapters.embedding import (
        EmbeddingError,
        LocalModelConfig,
        load_local_embedder,
    )

    now = [0.0]
    ticks = [0]

    def clock():
        ticks[0] += 1
        return 301.0 if when == "before" and ticks[0] > 1 else now[0]

    def loader(path):
        now[0] = 301.0
        return Backend()

    with pytest.raises(EmbeddingError, match="^embedding_timeout$"):
        load_local_embedder(
            LocalModelConfig(snapshot_dir=local_fixture_snapshot), loader=loader, clock=clock
        )


@pytest.mark.parametrize("value", [True, 0, -1, "3", 1.2])
def test_backend_count_contract(value):
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    backend.count_tokens = lambda _: value
    with pytest.raises(EmbeddingError, match="^embedding_output_invalid$"):
        instance(backend).count_tokens("passage: fixture")


def test_count_budget_checked_before_backend():
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    with pytest.raises(EmbeddingError, match="^embedding_input_limit$"):
        instance(backend, max_input_characters=1).count_tokens("passage: fixture")
    assert backend.counted == []


@pytest.mark.parametrize("method", ["embed_query", "count_tokens"])
def test_input_error_does_not_leak_or_decode_bytes(method):
    backend = Backend()
    embedder = instance(backend)
    for text in (b"sensitive-manuscript", b"\xffsensitive-manuscript"):
        with pytest.raises(ValidationError) as error:
            getattr(embedder, method)(text)
        assert "sensitive-manuscript" not in str(error.value)
        assert "input_value" not in str(error.value)
    assert backend.counted == backend.inputs == []


def test_failure_in_later_batch_leaves_input_unencoded():
    from clinical_agent.adapters.embedding import EmbeddingError

    backend = Backend()
    original = backend.encode
    calls = [0]

    def fail_second(*args, **kwargs):
        calls[0] += 1
        return [] if calls[0] == 2 else original(*args, **kwargs)

    backend.encode = fail_second
    source = chunks()
    before = source.model_dump_json()
    with pytest.raises(EmbeddingError, match="^embedding_output_invalid$"):
        instance(backend, batch_size=1).embed_chunks(source)
    assert calls[0] == 2 and source.model_dump_json() == before
