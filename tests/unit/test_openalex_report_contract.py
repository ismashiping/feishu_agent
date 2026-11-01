"""Offline OpenAlex evidence contract through the production graph."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.openalex import record_hit
from clinical_agent.application.report import ReportBuilder
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.fulltext import FulltextPassage, paper_key
from clinical_agent.domain.research import QuestionRequest, ResearchError
from clinical_agent.domain.retrieval import RetrievalResult
from clinical_agent.integrations.report_snapshot import SnapshotVerifier
from tests.unit.test_oa_fulltext import _nnunet


def service_case(index=0, mode="full", fault=None):
    hits = []
    for number in range(2):
        record = _nnunet(id=f"https://openalex.org/W{900001 + number}", doi=None)
        hit = record_hit(record, datetime.now(UTC))
        hit.rank = number + 1
        hit.score = 1.0 / (number + 1)
        if mode == "full" or mode == "mixed" and number == 0:
            for i in range(3):
                text = f"Synthetic study {number} method {i}."
                hit.fulltext.append(
                    FulltextPassage(
                        chunk_id=uuid4(),
                        paper_key=paper_key(record),
                        openalex_id=record.openalex_id,
                        representation_hash="a" * 64,
                        title=record.title,
                        section="Methods",
                        start=i * 100,
                        end=i * 100 + len(text),
                        text=text,
                        content_hash="b" * 64,
                        source_url="https://example.org/paper.pdf",
                        license="cc-by",
                    )
                )
        hits.append(hit)
    if mode == "empty":
        hits = []
    retrieval = RetrievalResult(
        scope="online",
        options={},
        embedding_info=None,
        hits=hits,
        search_provenance=dict(
            endpoint="https://api.openalex.org/works",
            query_sent="methods",
            fetched_at=datetime.now(UTC),
            date_from=None,
            date_to=None,
        ),
    )
    request = QuestionRequest(request_id=uuid4(), question="Study methods", scope="online")

    class Online:
        def retrieve(self, *args, **kwargs):
            return retrieval

    class Model:
        def analyze_evidence(self, context, **kwargs):
            studies, similarities = [], []
            for source in context["sources"]:
                quotes = [q for q in context["quotes"] if q["document_id"] == source["document_id"]]
                chosen = quotes[index]
                quote_id = chosen["quote_id"]
                if fault == "missing":
                    quote_id = f"{uuid4()}#0"
                elif fault == "other":
                    quote_id = next(
                        q["quote_id"]
                        for q in context["quotes"]
                        if q["document_id"] != source["document_id"]
                    )
                studies.append(
                    dict(
                        document_id=source["document_id"],
                        study_type="other",
                        type_basis="text",
                        type_quote_id=chosen["quote_id"],
                        reported=[
                            dict(field_name="technical_methods", role="reported", quote_id=quote_id)
                        ],
                    )
                )
                similarities.append(
                    dict(
                        document_id=source["document_id"],
                        dimensions=[
                            dict(
                                name="methods",
                                relation="overlap",
                                idea_quote="methods",
                                quote_id=chosen["quote_id"],
                                reason="Synthetic comparison",
                            )
                        ],
                    )
                )
            return json.dumps(dict(studies=studies, similarities=similarities))

        def review_claims(self, context, **kwargs):
            return json.dumps(
                dict(
                    reviews=[
                        dict(
                            claim_id=c["claim_id"],
                            support_status="uncertain",
                            basis="Offline reviewer; no semantic certification",
                        )
                        for c in context["claims"]
                    ]
                )
            )

    model = Model()
    service = ResearchService(
        generator=model,
        online_retriever=Online(),
        analyzer=EvidenceAnalyzer(model=model),
        max_feedback_rounds=0,
        reporter=ReportBuilder(reviewer=model, snapshots=SnapshotVerifier()),
    )
    return service, request, retrieval


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("mode", ["full", "mixed"])
def test_fulltext_report_graph(index, mode):
    service, request, retrieval = service_case(index, mode)
    analysis = service.analyze(request)
    expected = {p.chunk_id for h in retrieval.hits for p in h.fulltext}
    assert {e.chunk_id for s in analysis.sources for e in s.evidence} == expected
    result = service.report(request)
    assert result.markdown and result.report.claims
    assert result.report.status != "rejected"
    assert all(v.location_status == "valid" for v in result.report.verification)
    for study in result.report.analysis.studies:
        pointer = study.fields["technical_methods"].evidence[0]
        hit = next(h for h in retrieval.hits if h.document.document_id == study.document_id)
        assert pointer.chunk_id == hit.fulltext[index].chunk_id


@pytest.mark.parametrize("mode", ["none", "empty"])
def test_no_evidence_report_graph(mode):
    service, request, _ = service_case(mode=mode)
    result = service.report(request)
    assert result.report.content_status == "insufficient_evidence"
    assert not result.report.claims
    assert not result.report.analysis.sources


def test_unknown_quote_rejected():
    service, request, _ = service_case(fault="missing")
    with pytest.raises(ResearchError):
        service.report(request)


def test_other_paper_quote_not_accepted():
    service, request, _ = service_case(fault="other")
    result = service.report(request)
    assert all(s.fields["technical_methods"].value is None for s in result.report.analysis.studies)

@pytest.mark.parametrize("fault", ["missing", "other", "abstract"])
def test_report_rejects_tampered_evidence(fault):
    service, request, retrieval = service_case()
    analysis = service.analyze(request)
    pointer = analysis.studies[0].fields["technical_methods"].evidence[0]
    if fault == "missing":
        pointer.chunk_id = uuid4()
    elif fault == "other":
        pointer.chunk_id = retrieval.hits[1].fulltext[0].chunk_id
    else:
        pointer.chunk_id = retrieval.hits[0].chunk.chunk_id
    with pytest.raises(ResearchError, match="citation_invalid"):
        service._reporter.build(request, analysis, retrieval)
