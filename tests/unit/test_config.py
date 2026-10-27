"""Configuration behavior specified for Phase 0, independent of host settings."""

import os
import re
from pathlib import Path

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def isolated_config_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in tuple(os.environ):
        if key.casefold().startswith("clinical_agent_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_defaults_without_external_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from clinical_agent.config import Settings, load_settings

    for key in ("DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY", "FEISHU_APP_SECRET"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("UNRELATED_HOST_SETTING", "not-a-project-field")

    settings = load_settings()

    assert isinstance(settings, Settings)
    assert settings.model_dump() == {"app_env": "development", "log_level": "INFO"}
    assert Settings().model_dump() == settings.model_dump()


@pytest.mark.parametrize(
    ("app_env", "log_level", "key_case"),
    [
        ("development", "DEBUG", "upper"),
        ("test", "INFO", "lower"),
        ("production", "WARNING", "mixed"),
        ("test", "ERROR", "upper"),
        ("development", "CRITICAL", "upper"),
    ],
)
def test_environment_overrides_and_reloads(
    monkeypatch: pytest.MonkeyPatch, app_env: str, log_level: str, key_case: str
) -> None:
    from clinical_agent.config import load_settings

    app_key, log_key = "CLINICAL_AGENT_APP_ENV", "CLINICAL_AGENT_LOG_LEVEL"
    if key_case == "lower":
        app_key, log_key = app_key.lower(), log_key.lower()
    elif key_case == "mixed":
        app_key, log_key = "Clinical_Agent_App_Env", "Clinical_Agent_Log_Level"
    monkeypatch.setenv(app_key, app_env)
    monkeypatch.setenv(log_key, log_level)

    first = load_settings()
    assert (first.app_env, first.log_level) == (app_env, log_level)

    next_env = "production" if app_env != "production" else "test"
    next_level = "INFO" if log_level != "INFO" else "ERROR"
    monkeypatch.setenv(app_key, next_env)
    monkeypatch.setenv(log_key, next_level)

    second = load_settings()
    assert second is not first
    assert (second.app_env, second.log_level) == (next_env, next_level)
    assert (first.app_env, first.log_level) == (app_env, log_level)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("app_env", "staging"),
        ("app_env", "TEST"),
        ("app_env", "123"),
        ("app_env", ""),
        ("log_level", "TRACE"),
        ("log_level", "info"),
        ("log_level", "123"),
        ("log_level", ""),
        ("log_level", "CONFIG_TEST_SECRET_SENTINEL"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, field: str, invalid_value: str
) -> None:
    from clinical_agent.config import Settings, load_settings

    monkeypatch.setenv(f"CLINICAL_AGENT_{field.upper()}", invalid_value)
    for construct in (Settings, load_settings):
        with pytest.raises(ValidationError) as caught:
            construct()
        assert any(error["loc"] == (field,) for error in caught.value.errors(include_input=False))
        assert "input_value" not in str(caught.value)
        assert "input_type" not in str(caught.value)
        if invalid_value:
            # A value must not leak as a complete token; "info" in "information" is not a leak.
            assert re.search(rf"\b{re.escape(invalid_value)}\b", str(caught.value)) is None


@pytest.mark.parametrize("dotenv_location", ["current", "ancestor"])
def test_no_implicit_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dotenv_location: str
) -> None:
    from clinical_agent.config import Settings, load_settings

    working_dir = tmp_path / "work"
    working_dir.mkdir()
    dotenv_dir = working_dir if dotenv_location == "current" else tmp_path
    (dotenv_dir / ".env").write_text(
        "CLINICAL_AGENT_APP_ENV=production\nCLINICAL_AGENT_LOG_LEVEL=CRITICAL\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(working_dir)

    assert load_settings().model_dump() == {"app_env": "development", "log_level": "INFO"}
    assert Settings().model_dump() == {"app_env": "development", "log_level": "INFO"}
    monkeypatch.setenv("CLINICAL_AGENT_APP_ENV", "test")
    assert load_settings().app_env == "test"
    assert load_settings().log_level == "INFO"
