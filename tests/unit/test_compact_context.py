import json
from pathlib import Path

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.report import ReportBuilder
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalResult
from clinical_agent.integrations.report_snapshot import SnapshotVerifier

ROOT = Path("docs/acceptance/live-report-budget-20261101")


def test_real_context_replay_fits_and_reaches_models():
    report = json.loads((ROOT / "repeat-report.json").read_text(encoding="utf8"))["report"]
    original = AnalysisResult.model_validate(report["analysis"])
    retrieval = RetrievalResult.model_validate_json(
        (ROOT / "repeat-fulltext_rag.json").read_text(encoding="utf8")
    )
    request = QuestionRequest(
        request_id=original.request_id, question=original.original_idea, scope="online"
    )

    class Model:
        analysis_calls = 0
        review_calls = 0
        reviewed_ids = []

        def analyze_evidence(self, context, **kwargs):
            self.analysis_calls += 1
            assert len(json.dumps(context, ensure_ascii=False)) <= 32000
            assert {q["chunk_id"] for q in context["quotes"]} == {
                str(p.chunk_id) for h in retrieval.hits for p in h.fulltext
            }
            return original.model_dump_json(
                include={
                    "studies",
                    "idea_similarities",
                    "candidate_gaps",
                    "comparisons",
                    "feasibility",
                    "experiments",
                }
            )

        def review_claims(self, context, **kwargs):
            self.review_calls += 1
            assert len(context["claims"]) <= 6
            self.reviewed_ids.extend(c["claim_id"] for c in context["claims"])
            assert len(json.dumps(context, ensure_ascii=False)) <= 32000
            return json.dumps(
                {
                    "reviews": [
                        {
                            "claim_id": c["claim_id"],
                            "support_status": "uncertain",
                            "basis": "Offline transport test",
                        }
                        for c in context["claims"]
                    ]
                }
            )

    model = Model()
    analysis = EvidenceAnalyzer(model=model).analyze(
        request, retrieval, query_plan=original.query_plan
    )
    result = ReportBuilder(reviewer=model, snapshots=SnapshotVerifier()).build(
        request, analysis, retrieval
    )
    assert model.analysis_calls == 1 and model.review_calls > 1
    assert len(model.reviewed_ids) == len(set(model.reviewed_ids)) == len(result.claims)
    assert set(model.reviewed_ids) == {c.claim_id for c in result.claims}
    assert result.status == "verification_incomplete"
    assert analysis.sources == original.sources


def test_real_three_paper_input_reaches_analysis():
    import pytest

    from clinical_agent.domain.research import ResearchError

    retrieval = RetrievalResult.model_validate_json(
        (ROOT / "warm-fulltext_rag.json").read_text(encoding="utf8")
    )
    original = json.loads((ROOT / "repeat-report.json").read_text(encoding="utf8"))["report"][
        "analysis"
    ]

    class Model:
        calls = 0

        def analyze_evidence(self, context, **kwargs):
            self.calls += 1
            assert len(json.dumps(context, ensure_ascii=False)) <= 32000
            assert {q["document_id"] for q in context["quotes"]} == {
                str(h.document.document_id) for h in retrieval.hits if h.fulltext
            }
            passages = {str(p.chunk_id): p.text for h in retrieval.hits for p in h.fulltext}
            assert all(q["text"] in passages[q["chunk_id"]] for q in context["quotes"])
            return "{}"

    model = Model()
    request = QuestionRequest(
        request_id=original["request_id"], question=original["original_idea"], scope="online"
    )
    with pytest.raises(ResearchError):
        EvidenceAnalyzer(model=model).analyze(
            request, retrieval, query_plan=AnalysisResult.model_validate(original).query_plan
        )
    assert model.calls > 0
