"""CLI contracts with application ports; no external resources required."""

import json
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

ID = "12345678-1234-4234-8234-123456789abc"


def ingest_args():
    return [
        "ingest",
        "--source-type",
        "pdf",
        "--path",
        "input.pdf",
        "--allowed-root",
        ".",
        "--snapshot-dir",
        "snapshots",
        "--model-dir",
        "model",
        "--request-id",
        ID,
    ]


def ask_args():
    return ["ask", "--question", "  中文问题  ", "--model-dir", "model", "--request-id", ID]


def batch(status="imported"):
    from clinical_agent.domain.ingestion import BatchIngestionResult

    failed = status in {"failed", "rejected"}
    return BatchIngestionResult(
        entries=[
            dict(
                index=1,
                status=status,
                document_id=None if failed else UUID(ID),
                chunk_count=0 if failed else 1,
                error_code="source_failed" if failed else None,
            )
        ]
    )


@pytest.mark.parametrize(
    "status,code",
    [
        ("imported", 0),
        ("already_present", 0),
        ("needs_update", 3),
        ("conflict", 3),
        ("rejected", 3),
        ("failed", 3),
    ],
)
def test_ingest_status_output_and_lifecycle(status, code, capsys):
    from clinical_agent.cli import main

    events = []

    class Service:
        def ingest(self, request):
            assert request.source_type == "pdf" and request.path.name == "input.pdf"
            assert request.ingestion_time.utcoffset() is not None
            events.append("call")
            return batch(status)

    @contextmanager
    def factory(options):
        assert options.model_dir.name == "model" and options.snapshot_dir.name == "snapshots"
        events.append("enter")
        try:
            yield Service()
        finally:
            events.append("exit")

    assert main(ingest_args(), ingestion_factory=factory) == code
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert payload["request_id"] == ID and payload["result"]["entries"][0]["status"] == status
    assert events == ["enter", "call", "exit"]
    assert "input.pdf" not in output.out + output.err


@pytest.mark.parametrize("error", [None, "source_failed"])
def test_empty_or_batch_failure_exit_three(error, capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.ingestion import BatchIngestionResult

    class Service:
        def ingest(self, request):
            return BatchIngestionResult(entries=[], error_code=error)

    @contextmanager
    def factory(options):
        yield Service()

    assert main(ingest_args(), ingestion_factory=factory) == 3
    assert json.loads(capsys.readouterr().out)["result"]["entries"] == []


def test_ask_reuses_dto_and_preserves_unicode(capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.research import ResearchAnswer

    class Service:
        def answer(self, request):
            assert request.question == "中文问题" and request.request_id == UUID(ID)
            assert request.options.top_k == 3 and request.options.min_similarity == 0.6
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                limitations=["未检索到证据"],
                generated_at=datetime.now(UTC),
            )

    @contextmanager
    def factory(path):
        assert path.name == "model"
        yield Service()

    assert (
        main(ask_args() + ["--top-k", "3", "--min-similarity", "0.6"], research_factory=factory)
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "insufficient_evidence" and payload["limitations"] == [
        "未检索到证据"
    ]


@pytest.mark.parametrize(
    "extra",
    [
        ["--top-k", "0"],
        ["--top-k", "21"],
        ["--top-k", "private"],
        ["--min-similarity", "nan"],
        ["--min-similarity", "inf"],
        ["--min-similarity", "1.1"],
        ["--request-id", "private"],
        ["--question", " "],
        ["--question", "x" * 4001],
    ],
)
def test_invalid_input_never_assembles_resources(extra, capsys):
    from clinical_agent.cli import main

    def forbidden(*args):
        pytest.fail("Invalid input assembled resources")

    try:
        code = main(ask_args() + extra, research_factory=forbidden)
    except SystemExit as error:
        code = error.code
    assert code == 2
    output = capsys.readouterr()
    assert output.out == "" and "private" not in output.err and "中文问题" not in output.err


@pytest.mark.parametrize("command", ["ingest", "ask"])
def test_help_precedes_configuration(command, capsys):
    from clinical_agent.cli import main

    def forbidden(*args):
        pytest.fail("Help assembled resources")

    with pytest.raises(SystemExit) as error:
        main([command, "--help"], ingestion_factory=forbidden, research_factory=forbidden)
    assert error.value.code == 0
    assert "--model-dir" in capsys.readouterr().out


@pytest.mark.parametrize("failure,code", [("call", 1), ("close", 1), ("interrupt", 130)])
def test_failure_and_close_do_not_publish_success(failure, code, capsys):
    from clinical_agent.cli import main

    closed = []

    class Service:
        def ingest(self, request):
            if failure == "call":
                raise RuntimeError("private-raw-error")
            if failure == "interrupt":
                raise KeyboardInterrupt()
            return batch()

    @contextmanager
    def factory(options):
        try:
            yield Service()
        finally:
            closed.append(True)
            if failure == "close":
                raise RuntimeError("private-close-error")

    assert main(ingest_args(), ingestion_factory=factory) == code
    output = capsys.readouterr()
    assert output.out == "" and "private" not in output.err and closed == [True]
    assert json.loads(output.err.splitlines()[-1])["request_id"] == ID


@pytest.mark.parametrize("fault", ["retrieval", "generation", "unknown"])
def test_ask_errors_are_closed_and_sanitized(fault, capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalError

    class Service:
        def answer(self, request):
            if fault == "retrieval":
                raise RetrievalError("retrieval_failed")
            if fault == "generation":
                raise ResearchError("citation_invalid")
            raise RuntimeError("private-raw-error")

    @contextmanager
    def factory(path):
        yield Service()

    assert main(ask_args(), research_factory=factory) == 1
    output = capsys.readouterr()
    assert output.out == "" and "private" not in output.err
    assert json.loads(output.err.splitlines()[-1])["error_code"] in {
        "retrieval_failed",
        "citation_invalid",
        "command_failed",
    }


def test_wrong_request_answer_rejected(capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.research import ResearchAnswer

    class Service:
        def answer(self, request):
            return ResearchAnswer(
                request_id=uuid4(),
                status="insufficient_evidence",
                claims=[],
                sources=[],
                limitations=["wrong request"],
                generated_at=datetime.now(UTC),
            )

    @contextmanager
    def factory(path):
        yield Service()

    assert main(ask_args(), research_factory=factory) == 1
    assert capsys.readouterr().out == ""


def test_answered_cli_preserves_all_claim_and_citation_fields(
    source_factory, prepared_factory, capsys
):
    from clinical_agent.cli import main
    from clinical_agent.domain.citations import build_answer, parse_draft
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory(kind="pubmed"))

    class Service:
        def answer(self, request):
            hit = EvidenceHit(
                chunk=prepared.embedded[0].evidence,
                document=DocumentSummary.from_document(prepared.source.parsed.document),
                score=1.0,
                rank=1,
            )
            retrieval = RetrievalResult(
                options=request.options, embedding_info=retrieval_embedding_info(), hits=[hit]
            )
            raw = json.dumps(
                {
                    "claims": [
                        dict(
                            text="合成片段中的不确定性",
                            kind="uncertainty",
                            evidence_chunk_ids=[str(hit.chunk.chunk_id)],
                            limitations=["仅摘要"],
                        )
                    ]
                }
            )
            return build_answer(
                request,
                retrieval,
                parse_draft(raw, max_bytes=32000),
                generated_at=datetime.now(UTC),
            )

    @contextmanager
    def factory(path):
        yield Service()

    assert main(ask_args(), research_factory=factory) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["claims"][0]["kind"] == "uncertainty"
    assert output["claims"][0]["limitations"] == ["仅摘要"]
    assert output["sources"][0]["content_scope"] == "abstract"
    assert output["sources"][0]["evidence"][0]["location"]["kind"] == "abstract"
    assert "source_uri" not in json.dumps(output)


def test_mixed_batch_keeps_every_entry(capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.ingestion import BatchIngestionResult

    entries = [batch("imported").entries[0], batch("rejected").entries[0]]
    entries[1].index = 2

    class Service:
        def ingest(self, request):
            return BatchIngestionResult(entries=entries)

    @contextmanager
    def factory(options):
        yield Service()

    assert main(ingest_args(), ingestion_factory=factory) == 3
    assert len(json.loads(capsys.readouterr().out)["result"]["entries"]) == 2


@pytest.mark.parametrize("name,expected", [("sqlalchemy", 2), ("unrelated_internal_module", 1)])
def test_missing_dependency_is_only_for_known_optional_modules(name, expected, capsys):
    from clinical_agent.cli import main

    @contextmanager
    def factory(options):
        raise ModuleNotFoundError("private-module-detail", name=name)
        yield

    assert main(ingest_args(), ingestion_factory=factory) == expected
    output = capsys.readouterr()
    assert output.out == "" and "private-module-detail" not in output.err
