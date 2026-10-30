"""Public entry defaults authorize both sources; explicit local remains available."""

from contextlib import contextmanager

import pytest


@pytest.mark.parametrize("scope", [None, "local", "online", "hybrid"])
def test_cli_passes_default_or_explicit_scope(scope, capsys):
    from clinical_agent.cli import main
    from clinical_agent.domain.research import ResearchError

    seen = []

    class Service:
        def answer(self, request):
            seen.append(request)
            raise ResearchError("pubmed_failed")

    @contextmanager
    def factory(*args, **kwargs):
        yield Service()

    args = ["ask", "--question", "literature discovery", "--model-dir", "."]
    if scope:
        args += ["--scope", scope]
    main(args, research_factory=factory)
    assert len(seen) == 1 and seen[0].scope == (scope or "hybrid")
    assert seen[0].options.mode == "vector"


@pytest.mark.parametrize("scope", [None, "local", "online", "hybrid"])
def test_api_default_and_explicit_scope(scope):
    from clinical_agent.api_runtime import QuestionBody

    data = {"question": "literature discovery"}
    if scope:
        data["scope"] = scope
    assert QuestionBody(**data).scope == (scope or "hybrid")


@pytest.mark.parametrize("report", [False, True])
def test_feishu_text_and_report_default_to_hybrid(report):
    from clinical_agent.domain.research import ResearchError
    from feishu.worker import Dispatcher
    from tests.unit.test_feishu_worker import Dedup, Sink, envelope

    seen = []

    class Service:
        def answer(self, request):
            seen.append(request)
            raise ResearchError("pubmed_failed")

        respond = answer
        report = answer

    message = envelope()
    if report:
        message = message.model_copy(update={"text": "/report literature discovery"})
    worker = Dispatcher(research=Service(), dedup=Dedup(), sink=Sink())
    try:
        worker.submit(message).future.result(3)
        assert len(seen) == 1 and seen[0].scope == "hybrid"
    finally:
        worker.close(timeout_seconds=5)
