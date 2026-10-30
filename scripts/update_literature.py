"""Explicit local update command; bounded in-process scheduling, no installed jobs."""

import argparse
import json
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--allowed-root", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--snapshot-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rescan", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--interval-seconds", type=int, default=0)
    args = parser.parse_args()
    if (
        not 1 <= args.runs <= 100
        or not 0 <= args.interval_seconds <= 86400
        or (args.runs > 1 and args.interval_seconds < 1)
    ):
        parser.error("Invalid bounded schedule")
    if args.dry_run and args.runs != 1:
        parser.error("dry-run is single-shot")
    if not args.dry_run and (args.model_dir is None or args.snapshot_dir is None):
        parser.error("Publishing requires model-dir and snapshot-dir")
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.command_runtime import IngestionCommand, open_ingestion
    from clinical_agent.domain.updates import UpdateRequest

    try:
        with args.manifest.open("rb") as stream:
            body = stream.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError("manifest_too_large")
        request = UpdateRequest(
            **json.loads(body),
            allowed_root=args.allowed_root,
            dry_run=args.dry_run,
            rescan=args.rescan,
        )

        def evaluate() -> str:
            project = Path(__file__).resolve().parents[1]
            output = project / ".artifacts/update-evaluations" / str(uuid4())
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(project / "scripts/evaluate_minimal_baseline.py"),
                    "--output",
                    str(output),
                ],
                cwd=project,
                capture_output=True,
                timeout=60,
            )
            return {0: "passed", 1: "not_accepted"}.get(result.returncode, "failed")

        with ExitStack() as stack:
            engine = stack.enter_context(database_engine(DatabaseSettings()))

            def no_publish(request):
                raise AssertionError("Dry-run cannot publish")

            publish = no_publish
            if not args.dry_run:
                ingestion = stack.enter_context(
                    open_ingestion(
                        IngestionCommand(
                            model_dir=args.model_dir,
                            snapshot_dir=args.snapshot_dir,
                            update_existing=True,
                            chunk_max_tokens=args.max_tokens,
                        )
                    )
                )
                publish = ingestion.ingest
            service = UpdateService(
                ledger=PostgresUpdateLedger(engine),
                publish=publish,
                reader=PostgresStore(engine),
                evaluate=evaluate if args.evaluate else None,
            )
            code = 0
            for index in range(args.runs):
                if index:
                    Event().wait(args.interval_seconds)
                current = request.model_copy(update={"rescan": args.rescan or index > 0})
                result = service.run(current)
                print(result.model_dump_json(), flush=True)
                if result.status == "failed" or result.evaluation_status in {
                    "failed",
                    "not_accepted",
                }:
                    code = 1
                    break
            return code
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
