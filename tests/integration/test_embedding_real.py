"""Explicit external acceptance using the fixed local E5 CPU snapshot, never a fake."""

import ctypes
import json
import math
import os
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.external]
ROOT = Path(__file__).resolve().parents[2]
REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"


def _peak_memory_bytes():
    if sys.platform != "win32":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    function = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    function.restype = wintypes.BOOL
    assert function(wintypes.HANDLE(-1), ctypes.byref(counters), counters.cb)
    return counters.PeakWorkingSetSize


@pytest.mark.usefixtures("release_model_memory")
def test_fixed_e5_cpu_snapshot_tokenizer_chunk_and_vectors(tmp_path, monkeypatch):
    from clinical_agent.adapters.embedding import (
        EmbeddingError,
        EmbeddingLimits,
        LocalModelConfig,
        load_local_embedder,
    )
    from clinical_agent.adapters.pubmed_xml import parse_pubmed_xml
    from clinical_agent.domain.chunking import ChunkingPolicy, chunk_source

    attempts = []

    def no_network(*args, **kwargs):
        attempts.append("network")
        raise AssertionError("Real model acceptance must stay offline")

    for name in ("create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, no_network)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, no_network)
    snapshot = ROOT / "models/multilingual-e5-base" / REVISION
    assert (snapshot / "manifest.json").is_file(), "Prepare the fixed snapshot and install extra ml"
    start = perf_counter()
    embedder = load_local_embedder(
        LocalModelConfig(snapshot_dir=snapshot, limits=EmbeddingLimits(max_seconds=120.0))
    )
    load_seconds = perf_counter() - start
    assert load_seconds < 300.0
    inference_start = perf_counter()
    query_text = "随机对照研究中 intervention 的证据局限是什么？"
    query = embedder.embed_query(query_text)
    repeated = embedder.embed_query(query_text)
    assert max(abs(a - b) for a, b in zip(query.vector, repeated.vector, strict=True)) < 1e-6
    # Build exact boundaries using actual tokenization, never a character estimate.
    boundary = {}
    for size in range(1, 600):
        text = "test " * size
        count = embedder.count_tokens("query: " + text)
        if count in (512, 513):
            boundary[count] = text
        if len(boundary) == 2:
            break
    assert set(boundary) == {512, 513}
    accepted = embedder.embed_query(boundary[512])
    with pytest.raises(EmbeddingError, match="^embedding_token_limit$"):
        embedder.embed_query(boundary[513])
    path = tmp_path / "synthetic.xml"
    path.write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
    <Article><ArticleTitle>Synthetic tokenizer fixture</ArticleTitle><Abstract>
    <AbstractText Label="BACKGROUND">中文 α🙂 evidence only.</AbstractText>
    <AbstractText Label="RESULTS">"""
        + "test 治疗 " * 200
        + """</AbstractText>
    </Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
    )
    batch = parse_pubmed_xml(
        path,
        allowed_root=tmp_path,
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        document_id_factory=lambda _: UUID(int=1),
    )
    parsed = batch.entries[0].article
    assert parsed is not None
    chunk_start = perf_counter()
    source = chunk_source(
        parsed,
        tokenizer=embedder.count_tokens,
        profile=embedder.tokenizer_profile,
        policy=ChunkingPolicy(),
        chunk_id_factory=lambda i: UUID(int=i + 100),
    )
    chunk_seconds = perf_counter() - chunk_start
    assert len(source.chunks) >= 3
    # Compare our untruncated lengths to the actual SentenceTransformer input masks.
    backend_model = embedder._backend._model
    prepared = ["passage: " + item.evidence.text for item in source.chunks]
    actual_lengths = backend_model.tokenize(prepared)["attention_mask"].sum(dim=1).tolist()
    assert actual_lengths == [item.token_count for item in source.chunks]
    assert backend_model.device.type == "cpu"
    result = embedder.embed_chunks(source)
    assert len(result) == len(source.chunks)
    for item in result:
        parsed.validate_chunk(item.evidence)
        assert item.evidence.embedding_info.dimension == 768
        assert abs(math.sqrt(sum(x * x for x in item.vector)) - 1.0) < 1e-4
    assert len(accepted.vector) == len(query.vector) == 768
    assert not attempts
    seconds = perf_counter() - inference_start
    peak = _peak_memory_bytes()
    assert seconds < 120.0 and peak < 6 * 1024**3
    from importlib.metadata import version

    report = {
        "model_id": "intfloat/multilingual-e5-base",
        "revision": REVISION,
        "device": "cpu",
        "dimension": 768,
        "normalized": True,
        "load_seconds": load_seconds,
        "inference_and_chunk_seconds": seconds,
        "chunk_seconds": chunk_seconds,
        "chunk_token_counts": actual_lengths,
        "query_boundary": {"512": "accepted", "513": "rejected"},
        "peak_working_set_bytes": peak,
        "network_attempts": attempts,
        "python": sys.version,
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "packages": {
            name: version(name)
            for name in ("sentence-transformers", "transformers", "torch", "tokenizers")
        },
    }
    output = ROOT / ".artifacts/p1-05-20261027-01/real-model-result.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
