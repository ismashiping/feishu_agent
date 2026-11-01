import pytest
from pydantic import ValidationError


def test_api_rejects_retired_scope():
    from clinical_agent.api.schemas import QuestionBody

    with pytest.raises(ValidationError):
        QuestionBody(question="test", scope="local")


def test_cli_rejects_retired_scope(capsys):
    from clinical_agent.cli import main

    with pytest.raises(SystemExit) as error:
        main(["ask", "--question", "test", "--scope", "local", "--model-dir", "model"])
    assert error.value.code == 2
