"""Phase 5 removes only mapped compatibility paths after callers migrate."""

import ast
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
CONTRACT = json.loads(
    (ROOT / "tests/fixtures/migration/phase5-contracts.json").read_text(encoding="utf-8")
)
LEGACY_MODULES = tuple(CONTRACT["legacy_modules"])


def clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    }


@pytest.mark.parametrize("path", CONTRACT["legacy_files"])
def test_mapped_legacy_file_removed(path):
    assert not (ROOT / path).exists()


@pytest.mark.parametrize("module", LEGACY_MODULES)
def test_legacy_module_is_not_importable(module, tmp_path):
    code = """
import importlib
import sys

try:
    importlib.import_module(sys.argv[1])
except ModuleNotFoundError:
    raise SystemExit(0)
raise SystemExit("legacy module remains importable")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, module],
        cwd=tmp_path,
        env=clean_env(),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_canonical_modules_import_in_fresh_process(tmp_path):
    code = """
import importlib
import json
import sys

for module in json.loads(sys.argv[1]):
    importlib.import_module(module)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, json.dumps(CONTRACT["canonical_modules"])],
        cwd=tmp_path,
        env=clean_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            imports.append(node.args[0].value)
    return imports


def is_legacy(module: str) -> bool:
    if module == "clinical_agent.adapters.pmc_fulltext":
        return False
    return any(module == old or module.startswith(old + ".") for old in LEGACY_MODULES)


def test_active_python_has_no_legacy_imports():
    roots = [ROOT / name for name in ("src", "tests", "scripts", "alembic", "docs")]
    violations: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if (
                relative.startswith("docs/archive/")
                or "/before/" in relative
                or relative.startswith("docs/api-migration-phase2/before-")
            ):
                continue
            for module in imported_modules(path):
                if is_legacy(module):
                    violations.append(f"{relative}: {module}")
    assert violations == []


def test_deployment_and_package_discovery_use_canonical_feishu():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["setuptools"]["packages"]["find"]["include"] == ["clinical_agent*"]
    assert (
        project["project"]["scripts"]["clinical-feishu"]
        == "clinical_agent.channels.feishu.main:main"
    )
    for path in (ROOT / "Dockerfile", ROOT / "docker-compose.yml"):
        text = path.read_text(encoding="utf-8")
        assert "clinical_agent.channels.feishu.main" in text
        assert '"feishu.main"' not in text
