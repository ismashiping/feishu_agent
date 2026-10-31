"""Role isolation and compatibility against frozen real observations."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evaluation/minimal-v1/evidence"


@pytest.mark.parametrize("number,valid", [(1, False), (2, True), (3, True), (4, True)])
def test_agent_planner_preserves_frozen_provenance_gates(number, valid):
    from clinical_agent.agents.nodes import IdeaPlannerAgent
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.domain.research import QuestionRequest, ResearchError

    samples = json.loads((EVIDENCE / "samples.json").read_text(encoding="utf-8"))
    case = samples[(number - 1) % 2]

    class Replay:
        calls = 0

        def extract(self, request, **kwargs):
            self.calls += 1
            return (EVIDENCE / f"model-response-{number}.txt").read_text(encoding="utf-8")

    replay = Replay()
    agent = IdeaPlannerAgent(PicoPlanner(extractor=replay), clock=lambda: 1.0)
    state = {
        "request": QuestionRequest(request_id=uuid4(), question=case["idea"]),
        "deadline": 10.0,
        "agent_steps": [],
    }
    if valid:
        patch = agent(state)
        plan = patch["query_plan"]
        assert plan.original_question == state["request"].question
        assert patch["agent_steps"][0]["role"] == "idea_planner"
        for field in [*plan.structured_question.pico.fields(), *plan.terms]:
            if field.origin == "user_text":
                span = field.source_span
                assert state["request"].question[span.start : span.end] == field.text
    else:
        with pytest.raises(ResearchError, match="extraction_failed"):
            agent(state)
    assert replay.calls == 1 and state["agent_steps"] == []


@pytest.mark.parametrize(
    "scope,code", [("online", "openalex_required"), ("local", "local_corpus_not_evidence")]
)
def test_agent_scout_requires_openalex_and_never_reads_local_corpus(scope, code):
    from clinical_agent.agents.nodes import LiteratureScoutAgent
    from clinical_agent.domain.research import QuestionRequest, ResearchError

    agent = LiteratureScoutAgent(clock=lambda: 1.0)
    with pytest.raises(ResearchError, match=code):
        agent(
            {
                "request": QuestionRequest(
                    request_id=uuid4(), question="Frozen replay", scope=scope
                ),
                "deadline": 10.0,
            }
        )


@pytest.mark.parametrize("expired_before", [True, False])
def test_agent_scout_obeys_shared_deadline(expired_before):
    from clinical_agent.agents.nodes import LiteratureScoutAgent
    from clinical_agent.domain.research import QuestionRequest, ResearchError
    from clinical_agent.domain.retrieval import RetrievalResult, retrieval_embedding_info

    times = iter([11.0] if expired_before else [1.0, 11.0])

    class Local:
        calls = 0

        def retrieve(self, request):
            self.calls += 1
            return RetrievalResult(
                options=request.options, embedding_info=retrieval_embedding_info(), hits=[]
            )

    local = Local()
    agent = LiteratureScoutAgent(local, clock=lambda: next(times))
    with pytest.raises(ResearchError, match="research_timeout"):
        agent(
            {
                "request": QuestionRequest(request_id=uuid4(), question="A question"),
                "deadline": 10.0,
            }
        )
    assert local.calls == (0 if expired_before else 1)
