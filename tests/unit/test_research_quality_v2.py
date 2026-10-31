"""Frozen quality controls; synthetic metadata are not scientific evidence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

from clinical_agent.application.oa_fulltext import rerank_passages
from clinical_agent.application.openalex import (
    OpenAlexRetrievalService,
    compile_queries,
    record_hit,
)
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.fulltext import FulltextUnit
from clinical_agent.domain.openalex import OpenAlexRecord
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalRequest, RetrievalResult
from tests.unit.test_openalex import FIXTURES, Screening, plan

POLICY = json.loads(Path("tests/fixtures/answer_quality/policy.json").read_text())


def synthetic_record(index, *, duplicate_of=None):
    work = json.loads((FIXTURES / "organ.json").read_text())["results"][0]
    work["id"] = f"https://openalex.org/W90000000{index}"
    work["doi"] = f"https://doi.org/10.5555/synthetic-quality-{index}"
    study = duplicate_of or index
    work["title"] = f"Synthetic independent study {study}"
    work["abstract_inverted_index"] = {"Synthetic": [0], "study": [1], str(study): [2]}
    return OpenAlexRecord.from_work(work)


def test_one_paper_covering_all_dimensions_still_seeks_independent_evidence():
    class Search:
        calls = 0

        def search(self, query, **kwargs):
            self.calls += 1
            n = 1 if self.calls <= 2 else POLICY["second_round_independent_papers"]
            return [synthetic_record(i) for i in range(1, n + 1)], 100, []

    search = Search()
    result = OpenAlexRetrievalService(search, Screening(covered=["methods"])).retrieve(
        RetrievalRequest(question="segmentation", scope="online"),
        query_plan=plan(answer_dimensions=["methods"]),
    )
    assert search.calls == 4
    assert len(result.hits) == 5
    assert len(compile_queries(plan())) == 2


def test_same_title_and_abstract_different_doi_do_not_count_twice():
    class Search:
        def search(self, query, **kwargs):
            return [synthetic_record(1), synthetic_record(2, duplicate_of=1)], 2, []

    result = OpenAlexRetrievalService(Search(), Screening()).retrieve(
        RetrievalRequest(question="segmentation", scope="online"), query_plan=plan()
    )
    assert len(result.hits) == 1
    assert "duplicate_study" in result.search_provenance.candidate_outcomes.values()
    assert "limited_independent_evidence" in result.search_provenance.evidence_gaps


def test_comparison_searches_both_methods_and_keeps_origin_studies():
    p = plan(answer_dimensions=["AlphaNet evidence", "BetaNet evidence"]).model_copy(
        update={"research_intent": "comparison", "concept_groups": [["AlphaNet"], ["BetaNet"]]}
    )
    queries = compile_queries(p)
    assert len(queries) == 3 and "AlphaNet" in queries[0] and "BetaNet" in queries[0]
    assert "AlphaNet" in queries[1] and "BetaNet" not in queries[1]
    assert "BetaNet" in queries[2] and "AlphaNet" not in queries[2]

    class Origins(Screening):
        def screen_candidates(self, context, **kwargs):
            data = json.loads(super().screen_candidates(context, **kwargs))
            for item in data["assessments"]:
                item["study_role"] = (
                    "method_origin" if item["id"].endswith(("3", "4")) else "comparison"
                )
                if item["study_role"] == "method_origin":
                    item["relevance"] = "partial"  # supports one side, not head-to-head
                    item["covered_dimensions"] = [
                        "AlphaNet evidence" if item["id"].endswith("3") else "BetaNet evidence"
                    ]
            return json.dumps(data)

    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(i) for i in range(1, 5)], 4, [])),
        Origins(),
    ).retrieve(
        RetrievalRequest(
            question="segmentation", scope="online", options=RetrievalOptions(top_k=2)
        ),
        query_plan=p,
    )
    assert {h.document.openalex_record.openalex_id for h in result.hits} == {
        synthetic_record(3).openalex_id,
        synthetic_record(4).openalex_id,
    }

    class WrongScope(Origins):
        def screen_candidates(self, context, **kwargs):
            data = json.loads(super().screen_candidates(context, **kwargs))
            for item in data["assessments"]:
                item["constraints_match"] = False
            return json.dumps(data)

    rejected = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(3)], 1, [])),
        WrongScope(),
    ).retrieve(RetrievalRequest(question="segmentation", scope="online"), query_plan=p)
    assert not rejected.hits


def test_supplemental_new_papers_are_screened_before_old_budget_leftovers():
    old = []
    for index in range(1, 7):
        work = json.loads(synthetic_record(index).snapshot_json)
        work["abstract_inverted_index"] = {"Synthetic": list(range(1100))}
        old.append(OpenAlexRecord.from_work(work))
    new = synthetic_record(99)

    class Search:
        calls = 0

        def search(self, *args, **kwargs):
            self.calls += 1
            return (old if self.calls <= 2 else [*old, new]), 100, []

    screening = Screening()
    result = OpenAlexRetrievalService(Search(), screening).retrieve(
        RetrievalRequest(question="segmentation", scope="online"), query_plan=plan()
    )
    assert screening.calls[1]["candidates"][0]["id"] == new.openalex_id
    assert any(a.id == new.openalex_id for a in result.search_provenance.assessments)


def test_analysis_focus_is_not_a_mandatory_topic_but_endpoint_survives():
    from clinical_agent.domain.pico import ConceptRelation

    p = plan("segmentation invasion technical bottlenecks", task=["segmentation"])
    p.concept_relations = [
        ConceptRelation(
            source_text=text,
            english_term=term,
            concept_id=str(index),
            relation="exact_synonym",
            required=True,
        )
        for index, (text, term) in enumerate(
            [
                ("segmentation", "segmentation"),
                ("invasion", "invasion"),
                ("segmentation invasion technical bottlenecks", "technical challenges"),
            ]
        )
    ]
    for query in compile_queries(p):
        assert "segmentation" in query and "invasion" in query
        assert "technical challenges" not in query


def test_chinese_acquisition_prefers_actual_protocol_to_patient_cohort():
    candidates = [
        SimpleNamespace(section=POLICY["distractor_section"], text="CT MRI patients cohort."),
        SimpleNamespace(section=POLICY["distractor_section"], text="CT MRI external validation."),
        SimpleNamespace(section=POLICY["preferred_section"], text="CT scanners contrast protocol."),
        SimpleNamespace(
            section=POLICY["preferred_section"], text="MRI acquisition sequence contrast."
        ),
    ]
    selected = rerank_passages(candidates, POLICY["acquisition_question"])
    assert selected[:2] == candidates[2:]
    assert len(selected) == POLICY["fulltext_passages_per_paper"]


def test_comparison_still_selects_the_side_without_official_content():
    def titled(index, title, *, content):
        work = json.loads(synthetic_record(index).snapshot_json)
        work["title"] = title
        work["has_content"] = {"pdf": content, "grobid_xml": False}
        location = {
            "is_oa": content,
            "license": "cc-by" if content else None,
            "pdf_url": (
                "https://content.openalex.org/works/official.pdf"
                if content
                else "https://arxiv.org/pdf/1904.08128"
            ),
        }
        work["content_urls"] = {"pdf": location["pdf_url"]} if content else None
        work["best_oa_location"] = location
        work["locations"] = [location]
        return OpenAlexRecord.from_work(work)

    papers = [
        titled(1, "MedSAM segment anything in medical images", content=True),
        titled(2, "MedSAM prompt encoder for medical images", content=True),
        titled(3, "MedSAM mask decoder training setup", content=True),
        titled(
            4,
            "nnU-Net a self-configuring method for biomedical image segmentation",
            content=False,
        ),
    ]
    question = "MedSAM与nnU-Net有什么区别？"
    planned = plan(question, answer_dimensions=["MedSAM", "nnU-Net"]).model_copy(
        update={"research_intent": "comparison", "concept_groups": [["MedSAM"], ["nnU-Net"]]}
    )

    class BothDimensions(Screening):
        def screen_candidates(self, context, **kwargs):
            data = json.loads(super().screen_candidates(context, **kwargs))
            for item in data["assessments"]:
                item["covered_dimensions"] = ["MedSAM", "nnU-Net"]
                item["study_role"] = "comparison"
            return json.dumps(data)

    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *args, **kwargs: (papers, len(papers), [])),
        BothDimensions(covered=["MedSAM", "nnU-Net"]),
    ).retrieve(
        RetrievalRequest(question=question, scope="online", options=RetrievalOptions(top_k=2)),
        query_plan=planned,
    )
    titles = [hit.document.title for hit in result.hits]
    assert any(title.startswith("MedSAM") for title in titles)
    assert any(title.startswith("nnU-Net") for title in titles)


def test_comparison_includes_model_architecture_not_only_baseline_training():
    candidates = [
        SimpleNamespace(
            section="Methods / Training protocol", text="AlphaNet BetaNet baseline training."
        ),
        SimpleNamespace(
            section="Methods / Network architecture", text="Proposed model image encoder."
        ),
        SimpleNamespace(
            section="Methods / Network architecture", text="Proposed model prompt encoder."
        ),
    ]
    assert rerank_passages(candidates, "AlphaNet与BetaNet有哪些区别？")[:2] == candidates[1:]


def test_denied_licenses_do_not_consume_actual_download_paper_budget():
    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_fulltext_rag import Embedder

    records = [synthetic_record(i) for i in range(1, 7)]

    class Source:
        fetched = []

        def fetch_record(self, record, deadline, count):
            if record in records[:3]:
                raise ValueError("fulltext_license_not_allowed")
            count[0] += 1
            self.fetched.append(record.openalex_id)
            return (
                "CC BY",
                "https://pmc.ncbi.nlm.nih.gov/",
                b"synthetic",
                [
                    FulltextUnit(section=section, text="Synthetic method evidence.", start=i * 40)
                    for i, section in enumerate(["Methods", "Results", "Discussion"])
                ],
            )

    class Store:
        payloads = {}

        def load(self, key, signature):
            return self.payloads.get(key)

        def reuse_content(self, *args):
            return False

        def publish(self, key, signature, payload, vectors):
            self.payloads[key] = payload

        def search(self, key, vector, limit):
            return self.payloads[key]["passages"][:limit]

    result = RetrievalResult(
        options=RetrievalOptions(top_k=8),
        scope="online",
        embedding_info=None,
        hits=[
            record_hit(r, datetime.now(UTC)).model_copy(update={"score": 1.0 / i, "rank": i})
            for i, r in enumerate(records, 1)
        ],
        search_provenance={
            "endpoint": "https://api.openalex.org/works",
            "query_sent": "synthetic",
            "fetched_at": datetime.now(UTC),
            "date_from": None,
            "date_to": None,
        },
    )
    source, store = Source(), Store()
    service = FulltextService(source, store, Embedder())
    enriched = service.enrich("methods", result, deadline=monotonic() + 30)
    assert len(source.fetched) == POLICY["fulltext_download_papers"]
    assert sum(bool(h.fulltext) for h in enriched.hits) == 3
    assert len(enriched.hits[-1].fulltext) == 3
    RetrievalResult.model_validate(enriched)


def test_generation_groups_are_grounded_in_screened_papers():
    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(1), synthetic_record(2)], 2, [])),
        Screening(covered=["methods"]),
    ).retrieve(
        RetrievalRequest(question="segmentation", scope="online"),
        query_plan=plan(answer_dimensions=["methods"]),
    )
    request = QuestionRequest(question="segmentation", scope="online", request_id=uuid4())
    result.search_provenance.query_rounds = [{"synthetic_trace": "x" * 32000}]
    result.search_provenance.assessments[0].study_role = "method_origin"
    from hashlib import sha256

    from clinical_agent.domain.fulltext import FulltextPassage, paper_key

    passages = []
    for hit in result.hits:
        text = "Synthetic method evidence."
        record = hit.document.openalex_record
        passage = FulltextPassage(
            chunk_id=uuid4(),
            paper_key=paper_key(record),
            openalex_id=record.openalex_id,
            title=record.title,
            doi=record.doi,
            section="Methods",
            start=0,
            end=len(text),
            text=text,
            content_hash=sha256(text.encode()).hexdigest(),
            representation_hash=sha256(record.openalex_id.encode()).hexdigest(),
            source_url="https://pmc.ncbi.nlm.nih.gov/api/oai",
            license="cc-by",
        )
        hit.fulltext = [passage]
        passages.append(passage)
    context = ResearchService(retriever=object(), generator=object())._prepare(
        {
            "request": request,
            "retrieval": result,
            "query_plan": plan(),
            "deadline": monotonic() + 30,
        }
    )["context"]
    assert set(context.evidence_groups["methods"]) == {passage.chunk_id for passage in passages}
    assert context.search_provenance.query_rounds == []
    role_by_id = {e.chunk_id: e.study_role for e in context.evidence}
    assert role_by_id[passages[0].chunk_id] == "method_origin"
    assert result.hits[0].chunk.text not in context.model_dump_json()
    assert "Abstract text is withheld" in context.instructions
    assert result.search_provenance.query_rounds  # audit record remains intact


def test_openalex_readable_output_groups_sections_without_internal_counts():
    from clinical_agent.channels.feishu.sender import render_answer
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.research import GenerationDraft

    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(1)], 100, [])), Screening()
    ).retrieve(RetrievalRequest(question="segmentation", scope="online"), query_plan=plan())
    request = QuestionRequest(question="segmentation", scope="online", request_id=uuid4())
    from hashlib import sha256

    from clinical_agent.domain.fulltext import FulltextPassage, paper_key

    hit = result.hits[0]
    text = "Synthetic comparison evidence."
    passage = FulltextPassage(
        chunk_id=uuid4(),
        paper_key=paper_key(hit.document.openalex_record),
        openalex_id=hit.document.openalex_record.openalex_id,
        title=hit.document.title,
        doi=hit.document.doi,
        section="Discussion",
        start=0,
        end=len(text),
        text=text,
        content_hash=sha256(text.encode()).hexdigest(),
        representation_hash=sha256(b"rep").hexdigest(),
        source_url="https://pmc.ncbi.nlm.nih.gov/api/oai",
        license="cc-by",
    )
    hit.fulltext = [passage]
    answer = build_answer(
        request,
        result,
        GenerationDraft.model_validate(
            {
                "claims": [
                    {
                        "text": "Synthetic comparison only.",
                        "kind": "evidence",
                        "section": "技术路线",
                        "evidence_chunk_ids": [str(passage.chunk_id)],
                        "limitations": ["独立外部验证不足"],
                    }
                ]
            }
        ),
        generated_at=datetime.now(UTC),
    )
    text = render_answer(answer)
    assert (
        answer.search_provenance.candidate_outcomes[
            result.hits[0].document.openalex_record.openalex_id
        ]
        == "cited"
    )
    assert "技术路线" in text and "独立外部验证不足" in text
    assert "检索范围：" not in text and "候选" not in text
    assert "https://doi.org/" in text
    assert text.count("不用于个体诊断或治疗决策") == 1
    assert "100" in render_answer(answer, include_audit=True)


def test_openalex_without_fulltext_skips_generation():
    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(1)], 1, [])), Screening()
    ).retrieve(RetrievalRequest(question="segmentation", scope="online"), query_plan=plan())
    request = QuestionRequest(question="segmentation", scope="online", request_id=uuid4())

    class Generator:
        def generate(self, *args, **kwargs):
            raise AssertionError("abstract must not be sent to generation")

    service = ResearchService(retriever=object(), generator=Generator())
    state = {"request": request, "retrieval": result, "deadline": monotonic() + 30}
    assert service._route(state) == "empty"
    answer = service._empty(state)["answer"]
    assert answer.status == "insufficient_evidence"
    assert answer.claims == [] and answer.sources == []
    assert answer.unobtained_works[0].title == result.hits[0].document.title


def test_context_trim_keeps_the_cited_anchor_passage():
    from hashlib import sha256

    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.fulltext import FulltextPassage, paper_key
    from clinical_agent.domain.research import GenerationDraft, ResearchLimits

    result = OpenAlexRetrievalService(
        SimpleNamespace(search=lambda *a, **k: ([synthetic_record(1)], 1, [])), Screening()
    ).retrieve(RetrievalRequest(question="segmentation", scope="online"), query_plan=plan())
    request = QuestionRequest(question="segmentation", scope="online", request_id=uuid4())
    record = result.hits[0].document.openalex_record
    text = "Synthetic anchor method evidence. " * 100
    anchor = FulltextPassage(
        chunk_id=uuid4(),
        paper_key=paper_key(record),
        openalex_id=record.openalex_id,
        title=record.title,
        doi=record.doi,
        section="Methods",
        start=0,
        end=len(text),
        text=text,
        content_hash=sha256(text.encode()).hexdigest(),
        representation_hash=sha256(b"rep").hexdigest(),
        source_url="https://pmc.ncbi.nlm.nih.gov/api/oai",
        license="cc-by",
    )
    result.hits[0].fulltext = [anchor]
    state = {"request": request, "retrieval": result, "deadline": monotonic() + 30}
    full = ResearchService(retriever=object(), generator=object())._prepare(state)["context"]
    limit = len(full.model_dump_json()) - len(text) // 2
    service = ResearchService(
        retriever=object(),
        generator=object(),
        limits=ResearchLimits(max_context_characters=limit),
    )

    patch = service._prepare(state)

    assert patch["context"].evidence[0].chunk_id == anchor.chunk_id
    assert patch["context"].evidence[0].text == text
    assert patch["context"].evidence[0].fulltext == []
    assert "fulltext_context_trimmed" in patch["retrieval"].warnings
    assert result.hits[0].fulltext == [anchor] and not result.warnings
    draft = GenerationDraft.model_validate(
        {
            "claims": [
                {
                    "text": "Synthetic method only.",
                    "kind": "evidence",
                    "evidence_chunk_ids": [str(anchor.chunk_id)],
                    "limitations": [],
                }
            ]
        }
    )
    answer = build_answer(request, patch["retrieval"], draft, generated_at=datetime.now(UTC))
    assert answer.status == "answered"
