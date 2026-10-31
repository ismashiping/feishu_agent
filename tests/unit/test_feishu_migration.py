"""Feishu module relocation must preserve delivery, logging and entry contracts."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tests.unit.test_rag_db_migration import ImportOrder

ROOT = Path(__file__).parents[2]
CONTRACT = json.loads(
    (ROOT / "tests/fixtures/migration/phase4-contracts.json").read_text(encoding="utf-8")
)
MODULES = CONTRACT["modules"]


@pytest.mark.parametrize("old,new", MODULES.items())
def test_original_algorithms_preserved(old, new):
    before = ROOT / "docs/feishu-migration-phase4/before" / (old.split(".")[-1] + ".py")
    source = before.read_text(encoding="utf-8")
    for origin, target in MODULES.items():
        source = source.replace("from " + origin + " import", "from " + target + " import")
    # Logger names are a transport contract, independent of the new module name.
    source = source.replace("logging.getLogger(__name__)", f"logging.getLogger({old!r})")
    target = (ROOT / "src").joinpath(*new.split(".")).with_suffix(".py")
    assert ast.dump(ImportOrder().visit(ast.parse(source))) == ast.dump(
        ImportOrder().visit(ast.parse(target.read_text(encoding="utf-8")))
    )


@pytest.mark.parametrize(
    "module", list(MODULES.values()) + ["clinical_agent.channels", "clinical_agent.channels.feishu"]
)
def test_import_does_not_start_resources(module, tmp_path):
    from tests.unit.test_package import test_package_import_is_isolated_and_quiet

    test_package_import_is_isolated_and_quiet(module, tmp_path)


def clean_env():
    return {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    }


@pytest.mark.parametrize("entry", ["canonical", "console"])
@pytest.mark.parametrize("flag,exit_code", [("--help", 0), ("--unknown", 2)])
def test_entry_without_configuration(entry, flag, exit_code, tmp_path):
    command = {
        "canonical": [sys.executable, "-I", "-B", "-m", MODULES["feishu.main"]],
        "console": [str(Path(sys.executable).parent / "clinical-feishu.exe")]
        if os.name == "nt"
        else [shutil.which("clinical-feishu")],
    }[entry]
    result = subprocess.run(
        command + [flag], cwd=tmp_path, env=clean_env(), capture_output=True, text=True, timeout=15
    )
    assert result.returncode == exit_code, result.stderr
    assert "usage:" in (result.stdout if exit_code == 0 else result.stderr)
    assert "startup or connection failed" not in result.stderr
    assert "RuntimeWarning" not in result.stderr


def test_settings_dedup_dependencies_and_deployment_frozen():
    from clinical_agent.channels.feishu.dedup import _SCRIPT
    from clinical_agent.channels.feishu.main import FeishuSettings

    assert FeishuSettings.model_json_schema() == CONTRACT["settings_schema"]
    assert hashlib.sha256(_SCRIPT.encode()).hexdigest() == CONTRACT["redis_script_hash"]
    assert hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest() == CONTRACT[
        "fixed_file_hashes"
    ]["uv.lock"]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["optional-dependencies"] == CONTRACT["optional_dependencies"]
    assert project["project"]["scripts"]["clinical-feishu"] == MODULES["feishu.main"] + ":main"


def test_worker_and_sender_logs_use_original_formatter(capsys):
    import logging

    from clinical_agent.channels.feishu.main import configure_feishu_logging
    from clinical_agent.channels.feishu.sender import _LOG

    assert _LOG.name == "feishu.sender"
    logger = logging.getLogger("feishu")
    previous = (list(logger.handlers), logger.level, logger.propagate)
    try:
        configure_feishu_logging("INFO")
        _LOG.warning("migration_log_probe")
        logging.getLogger("feishu.worker").warning("migration_worker_probe")
        lines = capsys.readouterr().err.splitlines()
        assert [json.loads(line)["event"] for line in lines] == [
            "migration_log_probe",
            "migration_worker_probe",
        ]
    finally:
        for handler in logger.handlers:
            if handler not in previous[0]:
                handler.close()
        logger.handlers, logger.level, logger.propagate = previous
