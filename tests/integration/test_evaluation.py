"""Installed script outputs and benchmark failure accounting."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_evaluation_cli_writes_failed_fixture_with_provenance(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "scripts/evaluate_phase9.py"),
            "--output",
            str(tmp_path / "output"),
            "--performance",
            "--requests",
            "5",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 1, completed.stderr
    result = json.loads((tmp_path / "output/results.json").read_text(encoding="utf-8"))
    assert result["overall_status"] == "fail"
    assert result["provenance"]["files"]["uv.lock"]
    assert result["unexecuted_scopes"] == [
        "real_model",
        "external",
        "medical_review",
        "service_load",
    ]
    assert [r["concurrency"] for r in result["performance"]] == [1, 2, 4]
    assert all(r["requests"] == 5 for r in result["performance"])
    assert (tmp_path / "output/results.md").is_file()


def test_evaluation_performance_counts_exceptions():
    spec = importlib.util.spec_from_file_location(
        "evaluation_cli", ROOT / "scripts/evaluate_phase9.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def broken():
        raise TimeoutError("synthetic")

    result = module.benchmark(broken, 2, 5)
    assert result["failures"] == result["requests"] == 5
    assert len(result["errors"]) == 5
    assert result["p95_seconds"] >= result["p50_seconds"]
