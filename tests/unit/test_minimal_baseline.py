"""Failure baselines must stay failures; integrity and missing labels matter."""

import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "minimal_baseline", ROOT / "scripts/evaluate_minimal_baseline.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_recorded_failures_and_unrated_medical_quality():
    result = module.evaluate(ROOT / "evaluation/minimal-v1")
    assert result["fresh_e2e"]["total"] == 2
    assert result["fresh_e2e"]["successful"] == 0
    assert result["continuations"]["total"] == 1
    assert result["model_calls"] == 5
    assert result["medical_quality"]["status"] == "not_evaluated"
    assert all(v is None for v in result["medical_quality"]["metrics"].values())
    assert module.exit_code(result) == 1


def test_real_sources_replay_validates_identity_and_abstract():
    result = module.evaluate(ROOT / "evaluation/minimal-v1")
    assert result["source_replay"]["valid"] == result["source_replay"]["total"] == 4
    assert result["source_replay"]["mode"] == "offline_replay_not_report_citation_validation"


def test_tampered_evidence_is_not_evaluated_as_valid(tmp_path):
    bundle = tmp_path / "copy"
    shutil.copytree(ROOT / "evaluation/minimal-v1", bundle)
    (bundle / "evidence/samples.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        module.evaluate(bundle)


def test_manifest_path_cannot_escape_bundle(tmp_path):
    import json

    (tmp_path / "manifest.json").write_text(json.dumps({"../outside": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="path"):
        module.evaluate(tmp_path)
