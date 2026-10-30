"""Offline evidence replay only. Never opens models, network or business databases."""

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
from clinical_agent.domain.pubmed import PubMedSearchResult


def read(root: Path, name: str):
    return json.loads((root / name).read_text(encoding="utf-8"))


def evaluate(bundle: Path) -> dict:
    root = bundle.resolve()
    manifest = read(root, "manifest.json")
    if not manifest:
        raise ValueError("integrity: empty manifest")
    for name, expected in manifest.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("manifest path escapes bundle")
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("integrity mismatch: " + name)
    cases = read(root, "evidence/samples.json")
    ids = [c["id"] for c in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("case identities invalid")
    latest = read(root, "evidence/e2e-attempt2-summary.json")
    runs = latest["runs"]
    if len(runs) != len(ids) or {r["id"] for r in runs} != set(ids):
        raise ValueError("fresh run coverage mismatch")
    source_rows = []
    for case in cases:
        captured = PubMedSearchResult.model_validate(
            read(root, f"evidence/{case['id']}-pubmed.json")
        )
        for record in captured.records:
            parsed = parse_pubmed_response(
                ("<PubmedArticleSet>" + record.snapshot_xml + "</PubmedArticleSet>").encode(),
                fetched_at=captured.fetched_at,
            )
            valid = (
                sha256(record.snapshot_xml.encode()).hexdigest() == record.content_hash
                and len(parsed) == 1
                and parsed[0].pmid == record.pmid
                and parsed[0].title == record.title
                and parsed[0].doi == record.doi
                and parsed[0].source_units == record.source_units
                and parsed[0].abstract == record.abstract
            )
            source_rows.append({"case_id": case["id"], "pmid": record.pmid, "valid": valid})
    successes = 0
    for run in runs:
        if run.get("status") == "report_returned":
            from clinical_agent.domain.report import SECTION_TITLES, ReportResult

            artifact = f"evidence/{run['id']}-report.json"
            if artifact not in manifest:
                raise ValueError("integrity: returned report artifact missing")
            result = ReportResult.model_validate(read(root, artifact))
            successes += int(all(title in result.markdown for title in SECTION_TITLES))
    calls = read(root, "evidence/model-calls.json")
    if [c["number"] for c in calls] != list(range(1, len(calls) + 1)):
        raise ValueError("model call ledger is not sequential")
    continuation = read(root, "evidence/continuation-summary.json")
    labels = read(root, "human-labels.json")
    return {
        "baseline": "minimal-v1",
        "mode": "offline_replay_of_frozen_observations",
        "integrity": "valid",
        "fresh_e2e": {
            "total": len(ids),
            "successful": successes,
            "success_rate": successes / len(ids),
            "runs": runs,
            "definition": "latest fresh attempt per idea; actual eight-section report required",
        },
        "historical_first_attempts": read(root, "evidence/e2e-attempt1-summary.json")["runs"],
        "continuations": {
            "total": len(continuation["runs"]),
            "excluded_from_fresh": True,
            "runs": continuation["runs"],
        },
        "source_replay": {
            "mode": "offline_replay_not_report_citation_validation",
            "valid": sum(r["valid"] for r in source_rows),
            "total": len(source_rows),
            "sources": source_rows,
        },
        "model_calls": len(calls),
        "model_operation_counts": dict(Counter(c["operation"] for c in calls)),
        "model_call_seconds": [c.get("seconds") for c in calls],
        "new_model_calls": 0,
        "medical_quality": {
            "status": "not_evaluated",
            "label_status": labels["status"],
            "metrics": {
                k: None
                for k in [
                    "methods_accuracy",
                    "methods_omission",
                    "similarity_error",
                    "unsupported_gaps",
                    "unsupported_novelty",
                    "support_precision",
                    "support_recall",
                ]
            },
            "reason": "No valid report or independently signed medical labels; not zero scores.",
        },
        "source_state": read(root, "source-state.json"),
        "limitations": [
            "Historical attempts span uncommitted revisions; "
            "not a controlled before/after experiment.",
            "Captured official sources are not a recall benchmark or medical ground truth.",
            "Local database unavailable; hybrid/local end-to-end unverified.",
            "No successful report; semantic quality and full report citations unverified.",
        ],
    }


def exit_code(result: dict) -> int:
    if result["source_replay"]["valid"] != result["source_replay"]["total"]:
        return 2
    # v1 cannot award medical acceptance automatically, even after editing labels.
    return 1


def markdown(result: dict) -> str:
    lines = [
        "# 最小评价基线 v1",
        "",
        "模式：冻结历史证据的离线复算；没有新的模型/外部调用。",
        "",
        "| 指标 | 结果 |",
        "| --- | --- |",
        f"| 最新fresh端到端报告 | {result['fresh_e2e']['successful']}/"
        f"{result['fresh_e2e']['total']} |",
        f"| 真实来源XML/身份/摘要回放一致 | {result['source_replay']['valid']}/"
        f"{result['source_replay']['total']} |",
        f"| 历史模型调用 | {result['model_calls']}；本次新增0 |",
        f"| 回放续验 | {result['continuations']['total']}，不计入fresh成功率 |",
        "| 方法/相似性/缺口/论断医学质量 | 未评价（null）；无有效报告、无人工签署 |",
        "",
        "## 最新完整启动记录",
        "",
        "| 想法 | 状态 | 停止原因 | 耗时秒 |",
        "| --- | --- | --- | --- |",
    ]
    for run in result["fresh_e2e"]["runs"]:
        lines.append(
            f"| {run['id']} | {run['status']} | "
            f"{run.get('error_code', 'unknown')} | {run.get('seconds')} |"
        )
    lines.extend(["", "## 边界", "", *["- " + item for item in result["limitations"]]])
    lines.extend(["", "退出码1表示真实基线仍未达验收门槛；不是复算工具错误，也不是医学质量通过。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=project / "evaluation/minimal-v1")
    parser.add_argument("--output", type=Path, default=project / "evaluation/results/minimal-v1")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.bundle.resolve()):
        parser.error("output must be outside immutable bundle")
    try:
        result = evaluate(args.bundle)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"status": "invalid_evidence", "error_type": type(error).__name__}))
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "results.md").write_text(markdown(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "baseline_not_accepted",
                "fresh_e2e": result["fresh_e2e"]["success_rate"],
                "source_valid": result["source_replay"]["valid"],
                "new_model_calls": 0,
            }
        )
    )
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
