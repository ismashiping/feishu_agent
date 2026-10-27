"""Runtime assembly and the CLI's context boundary."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest


def test_explicit_settings_are_used_with_fixed_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from clinical_agent import bootstrap
    from clinical_agent.config import Settings

    settings = Settings(app_env="test", log_level="DEBUG")
    request_id = UUID("00000000-0000-4000-8000-000000000002")
    monkeypatch.setenv("CLINICAL_AGENT_APP_ENV", "INVALID_ENV_SENTINEL")

    def forbidden_load() -> None:
        pytest.fail("Explicit settings must not reload environment")

    configured = []
    monkeypatch.setattr(bootstrap, "load_settings", forbidden_load)
    monkeypatch.setattr(bootstrap, "configure_logging", configured.append)
    with bootstrap.open_runtime(settings, request_id=request_id) as runtime:
        assert isinstance(runtime, bootstrap.Runtime)
        assert runtime.settings is settings
        assert runtime.request_id == request_id
        assert configured == [settings]
        with pytest.raises(FrozenInstanceError):
            runtime.request_id = UUID(int=0)


def test_default_runtime_loads_once_and_generates_request_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clinical_agent import bootstrap
    from clinical_agent.config import Settings

    settings = Settings(app_env="test", log_level="INFO")
    loads = []
    configured = []

    def load_settings() -> Settings:
        loads.append(True)
        return settings

    monkeypatch.setattr(bootstrap, "load_settings", load_settings)
    monkeypatch.setattr(bootstrap, "configure_logging", configured.append)
    manager = bootstrap.open_runtime()
    assert loads == configured == []
    with manager as runtime:
        assert runtime.settings is settings
        assert isinstance(runtime.request_id, UUID)
        assert runtime.request_id.version == 4
        assert loads == [True]
        assert configured == [settings]
    with bootstrap.open_runtime() as another:
        assert another.request_id != runtime.request_id
    assert len(loads) == len(configured) == 2


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "body_error",
        "body_validation",
        "exit_error",
        "exit_validation",
        "entry_validation",
        "entry_error",
    ],
)
def test_cli_runtime_factory_lifecycle(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    from clinical_agent import bootstrap, cli
    from clinical_agent.config import Settings

    runtime = bootstrap.Runtime(
        Settings(app_env="test", log_level="INFO"),
        UUID("00000000-0000-4000-8000-000000000003"),
    )
    events = []
    sentinel = "CLI_TEST_SECRET_SENTINEL"

    def fail(validation: bool) -> None:
        if validation:
            Settings(log_level=sentinel)
        raise RuntimeError(sentinel)

    @contextmanager
    def factory() -> Iterator[bootstrap.Runtime]:
        events.append("factory")
        if mode.startswith("entry_"):
            fail(mode.endswith("validation"))
        events.append("enter")
        try:
            yield runtime
        finally:
            events.append("exit")
            assert capsys.readouterr().out == "", "Result must wait until context exit"
            if mode.startswith("exit_"):
                fail(mode.endswith("validation"))

    original_build = cli.build_doctor_report

    def build_report(received: bootstrap.Runtime):
        assert received is runtime
        events.append("build")
        if mode.startswith("body_"):
            fail(mode.endswith("validation"))
        return original_build(received)

    def forbidden_default():
        pytest.fail("Injected runtime factory must be used")

    monkeypatch.setattr(cli, "open_runtime", forbidden_default)
    monkeypatch.setattr(cli, "build_doctor_report", build_report)
    caplog.set_level(logging.INFO, logger="clinical_agent")
    result = cli.main(["doctor"], runtime_factory=factory)
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err
    assert "Traceback" not in captured.err
    assert sentinel not in caplog.text
    if mode == "success":
        import json

        assert result == 0
        report = json.loads(captured.out)
        assert report["request_id"] == str(runtime.request_id)
        assert report["app_env"] == "test"
        assert captured.err == ""
        assert [record.msg for record in caplog.records] == ["local_check_completed"]
    else:
        assert result == (2 if mode == "entry_validation" else 1)
        assert captured.out == ""
        expected = "Invalid configuration." if result == 2 else "Local check failed."
        assert captured.err == expected + "\n"
        if not mode.startswith("entry_"):
            assert [record.msg for record in caplog.records] == ["local_check_failed"]
            assert caplog.records[0].error_code == "local_check_failed"
            assert caplog.records[0].exception_type == (
                "ValidationError" if mode.endswith("validation") else "RuntimeError"
            )
    if mode.startswith("entry_"):
        assert events == ["factory"]
        assert caplog.records == []
    else:
        assert events == ["factory", "enter", "build", "exit"]
        assert caplog.records[0].request_id == str(runtime.request_id)
