"""Single-plan routing contracts; synthetic planning is not live LLM acceptance."""

import json
import logging
from uuid import uuid4

import pytest

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer, ResearchError
from tests.unit.test_evidence_analysis import case as case
from tests.unit.test_feedback_agents import service

CASES = [
    ("MedSAM与nnU-Net用于医学图像分割有什么区别？", "comparison"),
    ("肝脏亚区分割这个方向怎么样", "feasibility"),
    ("unet原始论文解释一下", "paper_explanation"),
    ("什么是nnunet", "definition"),
]


class Extractor:
    def __init__(self, intent, blocking=False):
        self.intent, self.blocking, self.calls = intent, blocking, 0

    def extract(self, request, **kwargs):
        self.calls += 1
        return json.dumps(
            {
                "task_intent": self.intent,
                "question_type": "uncertain",
                "pico": dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
                "terms": [
                    {
                        "text": request.question,
                        "origin": "user_text",
                        "source_span": {"start": 0, "end": len(request.question)},
                    }
                ],
                "ambiguities": [],
                "blocking_ambiguities": ["请明确亚区所指对象"] if self.blocking else [],
            }
        )


def routed(case, intent, blocking=False, statuses=None):
    if intent == "feasibility":
        from tests.unit.test_feasibility_analysis import payload

        case[2].update(payload(case))
    original, reviewer, model, retriever = service(case, statuses or ["supported"])
    extractor = Extractor(intent, blocking)
    svc = ResearchService(
        retriever=retriever,
        generator=object(),
        planner=PicoPlanner(extractor=extractor),
        analyzer=original._analyzer,
        reporter=original._reporter,
    )
    return svc, extractor, retriever, model


@pytest.mark.parametrize("question,intent", CASES)
def test_four_intents_use_one_plan(case, question, intent):
    svc, extractor, retriever, _ = routed(case, intent)
    request = case[0].model_copy(update={"question": question})
    if intent != "feasibility":
        empty = case[1].model_copy(update={"hits": []})
        retriever.retrieve = lambda request: empty
    result = svc.respond(request)
    assert extractor.calls == 1
    assert result.request_id == request.request_id
    if intent == "feasibility":
        assert result.analysis.query_plan.task_intent == intent
        assert result.claims
    else:
        assert isinstance(result, ResearchAnswer)
        assert result.query_plan.task_intent == intent


def test_blocking_ambiguity_does_not_retrieve(case):
    svc, extractor, retriever, model = routed(case, "feasibility", blocking=True)
    result = svc.respond(case[0])
    assert result.status == "needs_clarification"
    assert extractor.calls == 1 and retriever.calls == model.calls == 0


def test_feedback_reuses_plan(case):
    svc, extractor, retriever, model = routed(
        case, "feasibility", statuses=["unsupported", "supported"]
    )
    result = svc.respond(case[0])
    assert extractor.calls == 1 and model.calls == 2
    assert retriever.calls == 1 and result.feedback_history


def test_explicit_entries_keep_their_semantics(case):
    svc, extractor, retriever, _ = routed(case, "feasibility")
    empty = case[1].model_copy(update={"hits": []})
    retriever.retrieve = lambda request: empty
    assert isinstance(svc.answer(case[0]), ResearchAnswer)
    svc, extractor, _, _ = routed(case, "definition")
    assert svc.report(case[0]).report.analysis.query_plan.task_intent == "definition"
    assert extractor.calls == 1


@pytest.mark.parametrize("intent", [None, "invalid"])
def test_missing_or_invalid_intent_fails_auto(case, intent, caplog):
    svc, _, retriever, _ = routed(case, intent)
    with caplog.at_level(logging.WARNING), pytest.raises(ResearchError) as caught:
        svc.respond(case[0])
    assert caught.value.code == "extraction_failed"
    assert retriever.calls == 0
    if intent is None:
        assert any(
            getattr(record, "rule_code", "") == "task_intent_required" for record in caplog.records
        )


def test_auto_requires_planner(case):
    svc, _, _, _ = service(case, ["supported"])
    with pytest.raises(ValueError):
        svc.respond(case[0])


def test_legacy_explicit_plan_remains_readable():
    plan = PicoPlanner(extractor=Extractor(None)).plan(ClassificationRequest(question="test topic"))
    assert plan.task_intent is None


def test_planning_does_not_reset_deadline(case):
    svc, extractor, retriever, _ = routed(case, "feasibility")
    now = [0.0]
    svc._clock = svc._idea_agent.clock = lambda: now[0]
    original = extractor.extract

    def expire(request, **kwargs):
        now[0] = 1000.0
        return original(request, **kwargs)

    extractor.extract = expire
    with pytest.raises(ResearchError) as caught:
        svc.respond(QuestionRequest(question="test topic", request_id=uuid4()))
    assert caught.value.code == "research_timeout"
    assert retriever.calls == 0 and extractor.calls == 1
