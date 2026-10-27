"""Phase acceptance: learning demo and opt-in real Redis / full research pipeline."""

import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Event
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_phase1_learning_demo_and_navigation(tmp_path):
    directory = ROOT / "docs/learning/phase-01"
    for name in (
        "README.md",
        "tutorial.md",
        "code-walkthrough.md",
        "exercises.md",
        "interview.md",
        "troubleshooting.md",
    ):
        assert (directory / name).is_file(), f"Missing phase learning deliverable: {name}"
    result = subprocess.run(
        [sys.executable, str(directory / "demo.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "answered": "answered",
        "empty": "insufficient_evidence",
        "invalid_citation": "citation_invalid",
        "external_calls": 0,
    }


@pytest.mark.integration
@pytest.mark.redis
def test_real_redis_worker_sender_dedup_capacity_and_drain():
    from datetime import UTC, datetime

    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.retrieval import RetrievalResult, retrieval_embedding_info
    from feishu.dedup import DedupPolicy, create_deduplicator
    from feishu.events import MessageEnvelope
    from feishu.sender import Sender
    from feishu.worker import Dispatcher, WorkerPolicy

    url = os.environ.get("CLINICAL_AGENT_TEST_REDIS_URL")
    assert url, "Explicit isolated Redis required"
    entered, finish = Event(), Event()
    calls, sent = [], []

    class Research:
        def answer(self, request):
            calls.append(request)
            entered.set()
            assert finish.wait(10)
            return build_answer(
                request,
                RetrievalResult(
                    options=request.options, embedding_info=retrieval_embedding_info(), hits=[]
                ),
                None,
                generated_at=datetime.now(UTC),
            )

    class Transport:
        def send(self, envelope, text, *, deadline, guard):
            assert guard() is None
            sent.append(text)
            return "sent"

    def envelope(index):
        identity = ("p117", "message", f"om_{index}")
        return MessageEnvelope(
            app_id="p117",
            message_id=identity[2],
            sender_id="ou_test",
            chat_id="oc_test",
            chat_type="p2p",
            text="Synthetic question",
            request_id=uuid5(NAMESPACE_URL, json.dumps(identity, separators=(",", ":"))),
        )

    prefix = "p117-" + uuid4().hex
    dedup = create_deduplicator(url, policy=DedupPolicy(prefix=prefix, lease_ms=120000))
    sender = Sender(dedup=dedup, transport=Transport())
    worker = Dispatcher(
        research=Research(), dedup=dedup, sink=sender, policy=WorkerPolicy(capacity=2)
    )
    try:
        first = worker.submit(envelope(1))
        assert first.status == "accepted" and entered.wait(5)
        assert worker.submit(envelope(1)).status == "duplicate"
        second = worker.submit(envelope(2))
        assert second.status == "accepted"
        assert worker.submit(envelope(3)).status == "busy"
        # Busy admission must not reserve a Redis key.
        lease = dedup.acquire(envelope(3).dedup_identity).lease
        assert lease and dedup.release(lease) == "owned"
        assert worker.close(timeout_seconds=0) is False
        finish.set()
        assert first.future.result(10).status == second.future.result(10).status == "queued"
        assert worker.close(timeout_seconds=10)
        assert sender.close(timeout_seconds=10)
        assert len(calls) == len(sent) == 2
        assert dedup.acquire(envelope(1).dedup_identity).status == "duplicate"
        assert worker.submit(envelope(4)).status == "closed"
    finally:
        finish.set()
        assert worker.close(timeout_seconds=10)
        assert sender.close(timeout_seconds=10)
        for key in dedup.client.scan_iter(match=prefix + ":*"):
            dedup.client.delete(key)
        assert dedup.close()


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.database
@pytest.mark.usefixtures("release_model_memory")
def test_real_e5_postgres_model_api_pipeline(tmp_path, pdf_factory):
    import hashlib
    import shutil
    from datetime import UTC, datetime

    from sqlalchemy import delete, func, select

    from clinical_agent.adapters.embedding import REVISION, LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.llm import LLMSettings, open_llm
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.models import DocumentRecord
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.ingestion import ImportRequest
    from clinical_agent.domain.research import QuestionRequest

    assert os.environ.get("CLINICAL_AGENT_P117_PAID_CALLS") == "1"
    settings = DatabaseSettings()
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    embedder = load_local_embedder(
        LocalModelConfig(
            snapshot_dir=ROOT / "models/multilingual-e5-base" / REVISION,
        )
    )
    llm = LLMSettings()
    with database_engine(settings) as engine, open_llm(llm) as generator:
        with engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(DocumentRecord)) == 0
        retrieval = RetrievalService(embedder=embedder, retriever=PostgresRetriever(engine))
        invocations = []

        class CountedGenerator:
            def generate(self, context, *, timeout_seconds):
                invocations.append(1)
                assert len(invocations) <= 1, "One paid request maximum per test run"
                return generator.generate(context, timeout_seconds=timeout_seconds)

        research = ResearchService(retriever=retrieval, generator=CountedGenerator())
        medical_xml = os.environ.get("CLINICAL_AGENT_P117_MEDICAL_XML")
        question = (
            "根据提供的研究摘要，说明纳入人群、比较的血压目标、主要结果及安全性限制。"
            "保持摘要范围，不给个体治疗建议。"
            if medical_xml
            else "What limitations does this fictional teaching example have?"
        )
        request = QuestionRequest(
            request_id=uuid4(), question=question, options={"top_k": 5, "min_similarity": -1.0}
        )
        assert research.answer(request).status == "insufficient_evidence"
        assert not invocations
        body = (
            "This fictional teaching example included 12 invented participants. "
            "It had no control group and cannot establish treatment efficacy. "
            "It is not real clinical evidence and cannot guide patient care."
        )
        if medical_xml:
            original = Path(medical_xml)
            assert hashlib.sha256(original.read_bytes()).hexdigest() == (
                "c97bdc3443a42c42a3f01ca5c5bff84b70cee1a66819ab1b701b8068417a53c7"
            ), "Expected frozen NCBI snapshot of PMID 26551272"
            path = tmp_path / "sprint.xml"
            shutil.copyfile(original, path)
            source_type = "pubmed_xml"
        else:
            path = pdf_factory(tmp_path / "teaching.pdf", texts=(body,))
            source_type = "pdf"
        ingestion = IngestionService(
            reader=OfflineReader(tmp_path / "snapshots"),
            embedder=embedder,
            store=PostgresStore(engine),
        )
        command = ImportRequest(
            source_type=source_type,
            path=path,
            allowed_root=tmp_path,
            ingestion_time=datetime.now(UTC),
        )
        try:
            first = ingestion.ingest(command).entries[0]
            assert first.status == "imported"
            assert ingestion.ingest(command).entries[0].status == "already_present"
            prepared = PostgresStore(engine).load(first.document_id)
            by_id = {item.evidence.chunk_id: item.evidence for item in prepared.embedded}
            for chunk in by_id.values():
                prepared.source.parsed.validate_chunk(chunk)
            answer = research.answer(request)
            assert answer.status == "answered" and answer.claims and len(invocations) == 1
            if medical_xml:
                assert all(
                    source.pmid == "26551272" and source.content_scope == "abstract"
                    for source in answer.sources
                )
            else:
                assert all(source.pmid is None and source.doi is None for source in answer.sources)
            for source in answer.sources:
                for evidence in source.evidence:
                    assert evidence.text == by_id[evidence.chunk_id].text
                    assert evidence.location == by_id[evidence.chunk_id].location
            directory = Path(os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"])
            (directory / "pipeline-answer.json").write_text(
                answer.model_dump_json(indent=2), encoding="utf-8"
            )
            (directory / "pipeline-result.json").write_text(
                json.dumps(
                    {
                        "embedding": "real fixed E5 CPU",
                        "database": "real PostgreSQL/pgvector",
                        "llm": "real model API",
                        "paid_calls": len(invocations),
                        "empty_calls": 0,
                        "citation_slices": "passed",
                        "medical_review": "pending human review",
                        "sample": "PMID 26551272 abstract" if medical_xml else "synthetic PDF",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        finally:
            with engine.begin() as connection:
                connection.execute(delete(DocumentRecord))
