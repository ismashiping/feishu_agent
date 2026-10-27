"""Exercise the standard LangChain interface without any provider or network."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from clinical_agent.domain.research import GenerationInput, ResearchError


def context():
    return GenerationInput(
        question="Synthetic question",
        evidence=[
            {
                "chunk_id": "00000000-0000-0000-0000-000000000001",
                "text": "Synthetic evidence.",
                "content_scope": "abstract",
                "location": {"kind": "abstract", "section": "RESULTS", "start": 0, "end": 19},
            }
        ],
    )


def test_standard_chat_model_can_replace_model_api():
    from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator

    model = FakeListChatModel(responses=['{"claims":[]}'])
    generator = LangChainAnswerGenerator(model)
    assert generator.generate(context(), timeout_seconds=2) == '{"claims":[]}'


@pytest.mark.parametrize("budget", [0, -1, float("nan"), float("inf")])
def test_invalid_budget_does_not_call_model(budget):
    from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator

    model = FakeListChatModel(responses=["{}"])
    with pytest.raises(ResearchError, match="generation_timeout"):
        LangChainAnswerGenerator(model).generate(context(), timeout_seconds=budget)


def test_empty_standard_message_is_rejected():
    from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator

    with pytest.raises(ResearchError, match="model_output_invalid"):
        LangChainAnswerGenerator(FakeListChatModel(responses=[" "])).generate(
            context(), timeout_seconds=2
        )


def test_standard_messages_json_mode_and_budget_reach_model(monkeypatch):
    from langchain_core.messages import HumanMessage, SystemMessage

    from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator

    seen = []
    original = FakeListChatModel._generate

    def record(self, messages, **kwargs):
        seen.append((messages, kwargs))
        return original(self, messages, **kwargs)

    monkeypatch.setattr(FakeListChatModel, "_generate", record)
    LangChainAnswerGenerator(FakeListChatModel(responses=['{"claims":[]}'])).generate(
        context(), timeout_seconds=1.5
    )
    messages, options = seen[0]
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == context().instructions
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == context().model_dump_json(exclude={"instructions"})
    assert options["response_format"] == {"type": "json_object"}
    assert options["timeout"].read == 1.5


def test_completed_call_still_must_meet_total_budget(monkeypatch):
    from clinical_agent.adapters import langchain_generation

    times = iter([0.0, 3.0])
    monkeypatch.setattr(langchain_generation, "monotonic", lambda: next(times))
    generator = langchain_generation.LangChainAnswerGenerator(FakeListChatModel(responses=["{}"]))
    with pytest.raises(ResearchError, match="generation_timeout"):
        generator.generate(context(), timeout_seconds=2)
