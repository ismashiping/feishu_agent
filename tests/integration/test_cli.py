"""Exercise the installed module and console entry points from a foreign cwd."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest

pytestmark = pytest.mark.integration
SENTINEL = "CLI_TEST_SECRET_SENTINEL"


def _run_cli(
    entry: str, arguments: list[str], tmp_path: Path, **settings: str
) -> subprocess.CompletedProcess[str]:
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(settings)
    if entry == "module":
        command = [sys.executable, "-I", "-B", "-m", "clinical_agent"]
    else:
        executable = Path(sys.executable).parent / (
            "clinical-agent.exe" if os.name == "nt" else "clinical-agent"
        )
        assert executable.is_file(), "Installed clinical-agent entry point is missing"
        command = [str(executable)]
    return subprocess.run(
        [*command, *arguments],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize("entry", ["module", "console"])
@pytest.mark.parametrize("arguments", [[], ["--help"], ["doctor", "--help"]])
def test_help_does_not_build_runtime(entry: str, arguments: list[str], tmp_path: Path) -> None:
    result = _run_cli(entry, arguments, tmp_path, CLINICAL_AGENT_LOG_LEVEL=SENTINEL)
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
    assert "doctor" in result.stdout
    assert result.stderr == ""
    assert SENTINEL not in result.stdout


@pytest.mark.parametrize("entry", ["module", "console"])
@pytest.mark.parametrize("log_level", ["INFO", "WARNING"])
def test_doctor_json_and_logs(entry: str, log_level: str, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("CLINICAL_AGENT_LOG_LEVEL=" + SENTINEL)
    result = _run_cli(
        entry,
        ["doctor"],
        tmp_path,
        CLINICAL_AGENT_APP_ENV="test",
        CLINICAL_AGENT_LOG_LEVEL=log_level,
        OPENAI_API_KEY=SENTINEL,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert set(report) == {
        "status",
        "scope",
        "external_services_checked",
        "python_version",
        "app_env",
        "request_id",
    }
    assert report["status"] == "ok"
    assert report["scope"] == "local_environment"
    assert report["external_services_checked"] is False
    assert report["app_env"] == "test"
    assert re.fullmatch(r"\d+\.\d+\.\d+", report["python_version"])
    assert UUID(report["request_id"]).version == 4
    assert SENTINEL not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr
    if log_level == "INFO":
        records = [json.loads(line) for line in result.stderr.splitlines()]
        assert len(records) == 1
        assert records[0]["event"] == "local_check_completed"
        assert records[0]["request_id"] == report["request_id"]
        assert records[0]["app_env"] == report["app_env"]
    else:
        assert result.stderr == ""


@pytest.mark.parametrize("entry", ["module", "console"])
@pytest.mark.parametrize(
    "arguments, settings",
    [
        (["unsupported"], {}),
        (["doctor", "--unsupported"], {}),
        (["doctor"], {"CLINICAL_AGENT_APP_ENV": SENTINEL}),
        (["doctor"], {"CLINICAL_AGENT_LOG_LEVEL": SENTINEL}),
    ],
)
def test_invalid_cli_and_config_are_safe(
    entry: str, arguments: list[str], settings: dict[str, str], tmp_path: Path
) -> None:
    result = _run_cli(entry, arguments, tmp_path, **settings)
    assert result.returncode == 2
    assert result.stdout == ""
    assert SENTINEL not in result.stderr
    assert "Traceback" not in result.stderr
    if settings:
        assert result.stderr == "Invalid configuration.\n"
    else:
        assert "usage:" in result.stderr


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ([], 0),
        (["--help"], 0),
        (["doctor", "--help"], 0),
        (["unsupported"], 2),
        (["doctor", "--unsupported"], 2),
    ],
)
def test_parser_does_not_call_injected_factory(arguments, expected, capsys) -> None:
    from clinical_agent.cli import main

    def forbidden_factory():
        pytest.fail("Help and invalid arguments must not assemble runtime")

    try:
        result = main(arguments, runtime_factory=forbidden_factory)
    except SystemExit as exc:
        result = exc.code
    assert result == expected
    captured = capsys.readouterr()
    assert "usage:" in (captured.out if expected == 0 else captured.err)


def test_doctor_does_not_use_network_or_threads(tmp_path: Path) -> None:
    program = """
import socket
import threading
def forbidden(*args, **kwargs):
    raise AssertionError("External resource operation")
socket.create_connection = socket.getaddrinfo = forbidden
socket.socket.connect = socket.socket.connect_ex = forbidden
threading.Thread.start = forbidden
from clinical_agent.cli import main
raise SystemExit(main(["doctor"]))
"""
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", program],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["external_services_checked"] is False
