"""Exploratory discovery must distinguish optional questions from blocking ambiguity."""

import json
from uuid import uuid4

import pytest

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.pubmed import PubMedSearchRequest
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalResult, retrieval_embedding_info

QUESTION = "我想进行肝脏肿瘤亚区的划分，有没有相关研究？"


def draft(*, anchored=True, blocking=None):
    return {
        "question_type": "uncertain",
        "pico": dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
        "terms": (
            [
                {
                    "text": "肝脏肿瘤亚区",
                    "origin": "user_text",
                    "source_span": {
                        "start": QUESTION.index("肝脏肿瘤亚区"),
                        "end": QUESTION.index("肝脏肿瘤亚区") + len("肝脏肿瘤亚区"),
                    },
                }
            ]
            if anchored
            else []
        )
        + [
            {
                "text": "liver tumor subregion segmentation",
                "origin": "query_expansion",
                "source_span": None,
            }
        ],
        "ambiguities": ["可选：CT还是MRI？", "未提供对照或结局"],
        "blocking_ambiguities": blocking or [],
    }


class Extractor:
    def __init__(self, value):
        self.value = value

    def extract(self, request, **kwargs):
        return json.dumps(self.value)


def planner(value=None):
    return PicoPlanner(extractor=Extractor(value or draft()))


def test_optional_missing_pico_does_not_block_and_expansions_are_candidates():
    plan = planner().plan(ClassificationRequest(question=QUESTION))
    assert plan.structured_question.extraction_status == "partial"
    assert not plan.structured_question.pico.fields()
    assert plan.structured_question.ambiguities
    query = PubMedSearchRequest(question=QUESTION, query_plan=plan).query_text()
    assert query == QUESTION
    assert PubMedSearchRequest(question=QUESTION, query_plan=plan).planning_warnings() == [
        "legacy_terms_without_concept_relationships"
    ]
    assert "MRI" not in query and "CT" not in query
    assert (
        PubMedSearchRequest(
            question=QUESTION, query_plan=plan, options={"query": "explicit query"}
        ).query_text()
        == "explicit query"
    )


@pytest.mark.parametrize("value", [draft(anchored=False), draft(blocking=["主题指什么？"])])
def test_unidentified_topic_or_explicit_blocker_still_clarifies(value):
    plan = planner(value).plan(ClassificationRequest(question=QUESTION))
    assert plan.structured_question.extraction_status == "needs_clarification"


@pytest.mark.parametrize("entry", ["answer", "analyze", "report"])
def test_all_graph_entrypoints_reach_scout_before_downstream_processing(entry):
    from clinical_agent.domain.research import ResearchError

    class StopAtScout:
        calls = 0

        def retrieve(self, request):
            self.calls += 1
            assert request.question == QUESTION and request.scope == "local"
            raise ResearchError("pubmed_failed")

    local = StopAtScout()
    service = ResearchService(retriever=local, generator=object(), planner=planner())
    with pytest.raises(ResearchError, match="pubmed_failed"):
        getattr(service, entry)(QuestionRequest(question=QUESTION, request_id=uuid4()))
    assert local.calls == 1


def test_local_empty_does_not_use_online_and_displays_scope():
    class Local:
        def retrieve(self, request):
            return RetrievalResult(
                options=request.options, embedding_info=retrieval_embedding_info(), hits=[]
            )

    class Online:
        def retrieve(self, *args, **kwargs):
            raise AssertionError("local must never use online")

    service = ResearchService(
        retriever=Local(), online_retriever=Online(), generator=object(), planner=planner()
    )
    result = service.answer(QuestionRequest(question=QUESTION, request_id=uuid4()))
    assert result.status == "insufficient_evidence" and result.retrieval_scope == "local"


def test_user_entry_default_is_hybrid_and_internal_request_stays_compatible():
    from clinical_agent.api.schemas import QuestionBody
    from clinical_agent.channels.feishu.sender import render_answer

    assert QuestionBody(question=QUESTION).scope == "hybrid"
    assert QuestionBody(question=QUESTION, scope="local").scope == "local"
    assert QuestionRequest(question=QUESTION, request_id=uuid4()).scope == "local"
    # CLI/worker default construction is also exercised by existing entrypoint regressions.
    from clinical_agent.domain.research import ResearchAnswer

    text = render_answer(
        ResearchAnswer(
            request_id=uuid4(),
            status="insufficient_evidence",
            claims=[],
            sources=[],
            limitations=["No evidence"],
            generated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    )
    assert "未执行在线 PubMed" in text
