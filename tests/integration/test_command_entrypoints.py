"""Installed command parser behavior from a foreign directory and clean environment."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def run(entry, arguments, tmp_path, **overrides):
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(overrides)
    command = (
        [sys.executable, "-I", "-B", "-m", "clinical_agent"]
        if entry == "module"
        else [
            str(
                Path(sys.executable).parent
                / ("clinical-agent.exe" if os.name == "nt" else "clinical-agent")
            )
        ]
    )
    return subprocess.run(
        [*command, *arguments],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize("entry", ["module", "console"])
@pytest.mark.parametrize("name", ["ingest", "ask"])
def test_command_help_without_configuration(entry, name, tmp_path):
    result = run(entry, [name, "--help"], tmp_path, CLINICAL_AGENT_LOG_LEVEL="private-config")
    assert result.returncode == 0 and result.stderr == ""
    assert "--model-dir" in result.stdout
    assert "private-config" not in result.stdout


@pytest.mark.parametrize("entry", ["module", "console"])
def test_invalid_syntax_does_not_echo_private_input(entry, tmp_path):
    result = run(entry, ["ask", "--unknown", "private-question"], tmp_path)
    assert result.returncode == 2 and result.stdout == ""
    assert "usage:" in result.stderr and "private-question" not in result.stderr


@pytest.mark.parametrize("entry", ["module", "console"])
def test_missing_configuration_does_not_load_model_or_dotenv(entry, tmp_path):
    (tmp_path / ".env").write_text("CLINICAL_AGENT_DB_PASSWORD=private-password\n")
    result = run(
        entry, ["ask", "--question", "private-question", "--model-dir", "private-path"], tmp_path
    )
    assert result.returncode == 2 and result.stdout == ""
    error = json.loads(result.stderr.splitlines()[-1])
    assert error["error_code"] == "invalid_configuration"
    assert "private-" not in result.stderr
