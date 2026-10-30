"""One-shot Phase 9 offline replay and explicitly scoped Python microbenchmark."""

import argparse
import json
import platform
import statistics
import subprocess
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

from clinical_agent.application.evaluation import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def benchmark(operation, concurrency, requests):
    def timed(_):
        started = time.perf_counter()
        try:
            operation()
            return time.perf_counter() - started, None
        except Exception as exc:
            return time.perf_counter() - started, type(exc).__name__

    tracemalloc.start()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(timed, range(requests)))
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    latencies = sorted(r[0] for r in results)
    return {
        "concurrency": concurrency,
        "requests": requests,
        "failures": sum(r[1] is not None for r in results),
        "errors": [r[1] for r in results if r[1]],
        "elapsed_seconds": elapsed,
        "throughput_per_second": requests / elapsed,
        "p50_seconds": statistics.median(latencies),
        "p95_seconds": latencies[max(0, (95 * requests + 99) // 100 - 1)],
        "python_peak_bytes": peak,
        "cache": "warm_in_memory",
        "scope": "offline_evaluator_microbenchmark",
        "service_capacity_status": "inconclusive",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "evaluation/phase9-v1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.requests <= 10000:
        parser.error("requests must be in 1..10000")
    bundle = args.bundle.resolve()
    output = args.output.resolve()
    if output.is_relative_to(bundle):
        parser.error("output must be outside frozen bundle")
    if args.baseline and args.baseline.resolve().is_relative_to(output):
        parser.error("baseline must not be overwritten")
    dataset, observations, thresholds = [
        load(bundle / name) for name in ("dataset.json", "observations.json", "thresholds.json")
    ]
    baseline = load(args.baseline) if args.baseline else None
    operation = lambda: evaluate(dataset, observations, thresholds, baseline)  # noqa: E731
    result = operation()
    source_files = sorted((ROOT / "src").rglob("*.py"))
    source_files += [Path(__file__), ROOT / "uv.lock", ROOT / "pyproject.toml"]
    result["provenance"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "files": {
            str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in source_files
        },
        "configuration": thresholds["configuration"],
        "input_files": {
            p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(bundle.glob("*.json"))
        },
    }
    if args.performance:
        result["performance"] = [benchmark(operation, n, args.requests) for n in (1, 2, 4)]
    result["run_id"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:20]
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    lines = [
        "# Phase 9 replay",
        "",
        f"Status: {result['overall_status']}",
        f"Dataset: {result['dataset_version']} ({result['dataset_kind']})",
        "",
        "| Metric | Value | Numerator | Denominator | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, metric in result["metrics"].items():
        lines.append(
            f"| {name} | {metric['value']} | {metric['numerator']} | "
            f"{metric['denominator']} | {metric['status']} |"
        )
    lines += [
        "",
        "Unexecuted: " + ", ".join(result["unexecuted_scopes"]),
        "Synthetic replay does not establish medical quality or production capacity.",
        "Full observations, errors, configuration and provenance: results.json",
    ]
    (output / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{result['overall_status']}: {output}")
    return {"pass": 0, "fail": 1, "inconclusive": 2}[result["overall_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
