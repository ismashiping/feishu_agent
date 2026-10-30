"""Frozen synthetic report labels; do not claim independent medical annotation."""

import json
from uuid import uuid4

import pytest

from tests.unit.test_evidence_analysis import Model
from tests.unit.test_evidence_analysis import case as case  # reused Phase 6 synthetic fixture


class Review:
    def review_claims(self, context, *, timeout_seconds):
        return json.dumps(
            {
                "reviews": [
                    {
                        "claim_id": c["claim_id"],
                        "support_status": "supported",
                        "basis": "Synthetic exact support",
                    }
                    for c in context["claims"]
                ]
            }
        )


class Snapshots:
    def check(self, source, retrieval):
        return "valid"


@pytest.fixture
def report_case(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    analysis = EvidenceAnalyzer(model=Model(case[2])).analyze(case[0], case[1])
    return case, analysis


def build(report_case, **kwargs):
    from clinical_agent.application.report import ReportBuilder

    case, analysis = report_case
    return ReportBuilder(reviewer=Review(), snapshots=Snapshots(), **kwargs).build(
        case[0], analysis, case[1]
    )


def test_citation_report_eight_sections_and_references(report_case):
    from clinical_agent.domain.report import SECTION_TITLES, render_report

    report = build(report_case)
    text = render_report(report)
    assert all(title in text for title in SECTION_TITLES)
    assert report.references[0].number == 1
    assert report.content_status == "partial"
    assert all(
        c.epistemic_kind in {"reported_fact", "model_inference", "unverified_hypothesis"}
        for c in report.claims
    )
    assert "PMID" not in text or "None" not in text
    assert "source_uri" not in report.model_dump_json()


@pytest.mark.parametrize("state", ["supported", "partially_supported", "unsupported", "uncertain"])
def test_citation_report_support_states(report_case, state):
    from clinical_agent.application.report import ReportBuilder

    class Reviewer(Review):
        def review_claims(self, context, **kwargs):
            data = json.loads(super().review_claims(context, **kwargs))
            for item in data["reviews"]:
                item["support_status"] = state
            return json.dumps(data)

    case, analysis = report_case
    report = ReportBuilder(reviewer=Reviewer(), snapshots=Snapshots()).build(
        case[0], analysis, case[1]
    )
    assert report.status == (
        "rejected"
        if state == "unsupported"
        else "verification_incomplete"
        if state != "supported"
        else "verification_incomplete"
    )


@pytest.mark.parametrize("fault", ["chunk", "quote", "title", "hash", "location"])
def test_citation_report_rejects_tampering(report_case, fault):
    from clinical_agent.domain.research import ResearchError

    case, analysis = report_case
    source = analysis.sources[0]
    if fault == "chunk":
        source.evidence[0].chunk_id = uuid4()
    if fault == "quote":
        source.evidence[0].text = "invented"
    if fault == "title":
        source.title = "wrong title"
    if fault == "hash":
        source.content_hash = "f" * 64
    if fault == "location":
        source.evidence[0].location.start += 1
    with pytest.raises(ResearchError):
        build(report_case)


@pytest.mark.parametrize(
    "snapshot,status", [("invalid", "rejected"), ("unavailable", "verification_incomplete")]
)
def test_citation_report_snapshot_failure(report_case, snapshot, status):
    from clinical_agent.application.report import ReportBuilder

    class Snapshot:
        def check(self, *args):
            return snapshot

    case, analysis = report_case
    output = ReportBuilder(reviewer=Review(), snapshots=Snapshot()).build(
        case[0], analysis, case[1]
    )
    assert output.status == status
    assert output.claims


def test_citation_report_complete_graph(report_case):
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService

    case, analysis = report_case

    class Retriever:
        def retrieve(self, request):
            return case[1]

    service = ResearchService(
        retriever=Retriever(),
        generator=object(),
        analyzer=EvidenceAnalyzer(model=Model(case[2])),
        reporter=ReportBuilder(reviewer=Review(), snapshots=Snapshots()),
    )
    result = service.report(case[0])
    assert result.report.request_id == case[0].request_id
    assert result.markdown and result.report.claims


def test_citation_report_empty_no_model(report_case):
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.report import ReportBuilder

    case, _ = report_case
    empty = case[1].model_copy(update={"hits": []})

    class Never:
        def review_claims(self, *args, **kwargs):
            raise AssertionError("No evidence")

    analysis = EvidenceAnalyzer(model=Model(case[2])).analyze(case[0], empty)
    result = ReportBuilder(reviewer=Never(), snapshots=Snapshots()).build(case[0], analysis, empty)
    assert result.content_status == "insufficient_evidence"
    assert not result.claims and not result.references


def test_citation_report_validated_all_claims_can_be_verified(report_case):
    _, analysis = report_case
    for dimension in analysis.idea_similarities[0].dimensions.values():
        dimension.relation = "overlap"
        dimension.evidence = analysis.studies[0].type_evidence
    analysis.idea_similarities[0].overall_relation = "overlap"
    assert build(report_case).status == "verified"


def test_citation_report_actual_pdf_hash_and_location(tmp_path, pdf_factory, prepared_factory):
    from datetime import UTC, datetime

    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.ingestion import ImportRequest
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    path = tmp_path / "sample.pdf"
    pdf_factory(path, texts=("Synthetic cohort of 20.",))
    source = (
        OfflineReader(tmp_path / "snapshots")
        .read(
            ImportRequest(
                source_type="pdf",
                path=path,
                allowed_root=tmp_path,
                ingestion_time=datetime.now(UTC),
            )
        )
        .entries[0]
        .source
    )
    prepared = prepared_factory(source)
    hit = EvidenceHit(
        chunk=prepared.embedded[0].evidence,
        document=DocumentSummary.from_document(source.parsed.document),
        score=1.0,
        rank=1,
    )
    retrieval = RetrievalResult(options={}, embedding_info=retrieval_embedding_info(), hits=[hit])
    request = QuestionRequest(request_id=uuid4(), question="Synthetic cohort")
    draft = GenerationDraft(
        claims=[
            DraftClaim(
                text="Supplied passage",
                kind="evidence",
                evidence_chunk_ids=[hit.chunk.chunk_id],
                limitations=[],
            )
        ]
    )
    citation = build_answer(request, retrieval, draft, generated_at=datetime.now(UTC)).sources[0]
    verifier = SnapshotVerifier()
    assert verifier.check(citation, retrieval) == "valid"
    retrieval.hits[0].chunk.location.start += 1
    assert verifier.check(citation, retrieval) == "invalid"


@pytest.mark.parametrize("fault", ["valid", "doi", "title", "unavailable", "missing"])
def test_citation_report_official_metadata(report_case, fault):
    from datetime import UTC, datetime

    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.application.report import ReportBuilder
    from tests.unit.test_pubmed_online import article, xml

    case, analysis = report_case
    # Rebind both actual retrieval and analysis metadata to one synthetic PMID.
    case[1].hits[0].document.pmid = "123"
    analysis.sources[0].pmid = "123"
    if fault == "doi":
        case[1].hits[0].document.doi = "10.1234/original"
        analysis.sources[0].doi = "10.1234/original"
    record = parse_pubmed_response(xml(article("123")), fetched_at=datetime.now(UTC))[0]
    record = record.model_copy(
        update={"title": analysis.sources[0].title, "notices": [], "publication_types": []}
    )

    class Metadata:
        def fetch_metadata(self, ids, **kwargs):
            assert ids == ["123"]
            if fault == "unavailable":
                raise TimeoutError("private")
            if fault == "missing":
                return []
            return [
                record.model_copy(update={"doi": "10.1234/other"})
                if fault == "doi"
                else record.model_copy(update={"title": "Other"})
                if fault == "title"
                else record
            ]

    report = ReportBuilder(reviewer=Review(), snapshots=Snapshots(), metadata=Metadata()).build(
        case[0], analysis, case[1]
    )
    assert report.status == ("rejected" if fault in {"doi", "title"} else "verification_incomplete")
    verification = report.verification[0]
    assert verification.identity_status == (
        "valid" if fault == "valid" else "invalid" if fault in {"doi", "title"} else "unavailable"
    )


def test_citation_report_bounded_efetch():
    import httpx

    from tests.unit.test_pubmed_online import article, client, xml

    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.path.endswith("efetch.fcgi")
        return httpx.Response(200, content=xml(article("123")))

    records = client(handler).fetch_metadata(["123"], timeout_seconds=20.0)
    assert records[0].pmid == "123" and len(calls) == 1


def test_citation_report_hypothesis_and_complete_feishu_text(report_case):
    from clinical_agent.domain.analysis import CandidateGap
    from clinical_agent.domain.report import render_report
    from feishu.sender import split_report_text

    _, analysis = report_case
    item = (
        analysis.studies[0]
        .fields["design"]
        .model_copy(
            update={
                "value": "Investigate additional cohorts",
                "epistemic_kind": "unverified_hypothesis",
                "basis": "model_inference",
                "verification_needed": "Review more literature",
            }
        )
    )
    analysis.candidate_gaps.append(
        CandidateGap(
            description=item,
            counter_evidence=[],
            reasoning="Only a limited supplied cohort",
            scope="Current passages",
        )
    )
    report = build(report_case)
    directions = [c for c in report.claims if c.section == 7]
    assert directions and all(
        c.epistemic_kind == "unverified_hypothesis" and c.verification_needed for c in directions
    )
    text = render_report(report)
    parts = split_report_text(text * 2)
    combined = "".join(p.split("\n", 1)[1] for p in parts)
    assert combined == (text * 2).replace("<", "＜").replace(">", "＞").replace("&", "＆")


def test_citation_report_review_fault_keeps_claims(report_case):
    from clinical_agent.application.report import ReportBuilder

    class Bad:
        def review_claims(self, *args, **kwargs):
            return '{"reviews":[]}'

    case, analysis = report_case
    report = ReportBuilder(reviewer=Bad(), snapshots=Snapshots()).build(case[0], analysis, case[1])
    assert report.status == "verification_incomplete" and report.claims
    assert all(c.support_status == "uncertain" for c in report.claims)


def test_citation_report_cli_and_api(report_case, tmp_path, capsys):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService
    from clinical_agent.cli import main

    case, _ = report_case

    class Retriever:
        def retrieve(self, request):
            return case[1]

    service = ResearchService(
        retriever=Retriever(),
        generator=object(),
        analyzer=EvidenceAnalyzer(model=Model(case[2])),
        reporter=ReportBuilder(reviewer=Review(), snapshots=Snapshots()),
    )

    @contextmanager
    def factory(*args):
        yield service

    assert (
        main(
            [
                "ask",
                "--scope",
                "local",
                "--report",
                "--question",
                case[0].question,
                "--model-dir",
                str(tmp_path),
            ],
            research_factory=factory,
        )
        == 0
    )
    cli = json.loads(capsys.readouterr().out)

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=service)

    with TestClient(
        create_app(
            settings=ApiSettings(model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path),
            runtime_factory=runtime,
        )
    ) as session:
        response = session.post(
            "/v1/reports", json={"scope": "local", "question": case[0].question}
        )
        assert response.status_code == 200, response.text
        assert response.json()["report"]["claims"] == cli["report"]["claims"]
        assert (
            session.post(
                "/v1/reports", content="invalid", headers={"Content-Type": "text/plain"}
            ).status_code
            == 415
        )


def test_citation_report_feishu_worker_and_sender(report_case):
    from clinical_agent.domain.report import ReportResult, render_report
    from feishu.sender import Sender
    from feishu.worker import Dispatcher
    from tests.unit.test_feishu_sender import Transport
    from tests.unit.test_feishu_worker import Dedup, Sink, envelope

    report = build(report_case)

    class Service:
        def report(self, request):
            assert request.question == "Synthetic question?"
            result = report.model_copy(update={"request_id": request.request_id})
            return ReportResult(report=result, markdown=render_report(result))

    message = envelope().model_copy(update={"text": "/report Synthetic question?"})
    dedup, sink = Dedup(), Sink()
    worker = Dispatcher(research=Service(), dedup=dedup, sink=sink)
    try:
        submission = worker.submit(message)
        assert submission.future.result(3).status == "queued"
        delivery = sink.deliveries[0]
        assert delivery.answer.request_id == message.request_id
    finally:
        assert worker.close(timeout_seconds=3)

    class SendingDedup:
        def check(self, lease):
            return "owned"

        def complete(self, lease):
            return "owned"

        def release(self, lease):
            return "owned"

    transport = Transport()
    sender = Sender(dedup=SendingDedup(), transport=transport)
    assert sender.offer(delivery)
    assert sender.close(timeout_seconds=3)
    text = "".join(part[1].split("\n", 1)[1] for part in transport.calls)
    assert "科研选题现状调研报告" in text and "可追溯文献引用及证据支持状态" in text


def test_citation_report_online_multisection_snapshot():
    from datetime import UTC, datetime

    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.pubmed import PubMedSearchResult
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest
    from tests.unit.test_pubmed_online import article, xml

    record_text = article("123").replace(
        "</Abstract>", '<AbstractText Label="LIMITATIONS">Small sample.</AbstractText></Abstract>'
    )
    now = datetime.now(UTC)
    record = parse_pubmed_response(xml(record_text), fetched_at=now)[0]
    response = PubMedSearchResult(
        query_sent="cohort",
        query_translation=None,
        total_count=1,
        requested_limit=1,
        returned_count=1,
        truncated=False,
        fetched_at=now,
        date_from=None,
        date_to=None,
        date_field="pdat",
        sort="relevance",
        status="complete",
        warnings=[],
        missing_pmids=[],
        records=[record],
    )

    class Search:
        def search(self, *args, **kwargs):
            return response

    request = QuestionRequest(request_id=uuid4(), question="cohort", scope="online")
    from clinical_agent.domain.retrieval import RetrievalRequest

    retrieval = PubMedRetrievalService(Search()).retrieve(
        RetrievalRequest.model_validate(request.model_dump(exclude={"request_id"}))
    )
    draft = GenerationDraft(
        claims=[
            DraftClaim(
                text="Supplied passage",
                kind="evidence",
                evidence_chunk_ids=[retrieval.hits[0].chunk.chunk_id],
                limitations=[],
            )
        ]
    )
    source = build_answer(request, retrieval, draft, generated_at=now).sources[0]
    assert SnapshotVerifier().check(source, retrieval) == "valid"
    retrieval.hits[0].chunk.text = "Wrong abstract"
    assert SnapshotVerifier().check(source, retrieval) == "invalid"


def test_citation_report_local_multirecord_xml(tmp_path, prepared_factory):
    from datetime import UTC, datetime

    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.ingestion import ImportRequest
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )
    from tests.unit.test_pubmed_online import article, xml

    now = datetime.now(UTC)
    path = tmp_path / "batch.xml"
    path.write_bytes(xml(article("123"), article("456")))
    batch = OfflineReader(tmp_path / "snapshots").read(
        ImportRequest(
            source_type="pubmed_xml", path=path, allowed_root=tmp_path, ingestion_time=now
        )
    )
    for entry in batch.entries:
        source = entry.source
        prepared = prepared_factory(source)
        hit = EvidenceHit(
            chunk=prepared.embedded[0].evidence,
            document=DocumentSummary.from_document(source.parsed.document),
            score=1.0,
            rank=1,
        )
        retrieval = RetrievalResult(
            options={}, embedding_info=retrieval_embedding_info(), hits=[hit]
        )
        request = QuestionRequest(request_id=uuid4(), question="Synthetic batch")
        draft = GenerationDraft(
            claims=[
                DraftClaim(
                    text="Supplied passage",
                    kind="evidence",
                    evidence_chunk_ids=[hit.chunk.chunk_id],
                    limitations=[],
                )
            ]
        )
        citation = build_answer(request, retrieval, draft, generated_at=now).sources[0]
        assert SnapshotVerifier().check(citation, retrieval) == "valid"


def test_citation_report_oversize_sends_explicit_whole_notice(report_case):
    from time import monotonic
    from uuid import uuid4

    from feishu.dedup import Lease
    from feishu.sender import Sender
    from feishu.worker import Delivery
    from tests.unit.test_feishu_sender import Transport, message

    report = build(report_case)
    envelope = message()
    report.request_id = envelope.request_id
    report.references[0].source.title = "界" * 100000

    class Dedup:
        def check(self, lease):
            return "owned"

        def complete(self, lease):
            return "owned"

        def release(self, lease):
            return "owned"

    transport = Transport()
    sender = Sender(dedup=Dedup(), transport=transport)
    assert sender.offer(
        Delivery(
            envelope=envelope,
            lease=Lease(identity=envelope.dedup_identity, owner=uuid4()),
            deadline=monotonic() + 10,
            answer=report,
        )
    )
    assert sender.close(timeout_seconds=3)
    assert len(transport.calls) == 1
    assert "未发送任何报告内容或引用" in transport.calls[0][1]


def test_default_report_is_readable_and_audit_retains_details(report_case):
    from clinical_agent.domain.report import render_report

    report = build(report_case)
    text = render_report(report)
    audit = render_report(report, include_audit=True)
    assert "model_inference" not in text and "c1 [" not in text
    assert "推断" in text and "证据范围" in text
    assert "chunk=" not in text and "document=" not in text
    assert "chunk=" in audit and "document=" in audit


def test_default_report_preserves_rejection(report_case):
    from clinical_agent.domain.report import render_report

    report = build(report_case)
    report.status = "rejected"
    assert "拒绝正常发布" in render_report(report)
