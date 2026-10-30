"""Explicit local source governance; no models or online verification."""

import argparse
import json
from pathlib import Path
from uuid import UUID


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("claim", "status"):
        sub.add_parser(action).add_argument("--request", type=Path, required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--namespace", choices=("doi", "pmid", "pdf_sha256"), required=True)
    resolve.add_argument("--value", required=True)
    sub.add_parser("inspect").add_argument("--document-id", type=UUID, required=True)
    args = parser.parse_args()
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.domain.governance import AliasClaim, StatusChange

    try:
        request = None
        if args.action in ("claim", "status"):
            with args.request.open("rb") as stream:
                body = stream.read(65537)
            if len(body) > 65536:
                raise ValueError("request_too_large")
            request = json.loads(body)
        with database_engine(DatabaseSettings()) as engine:
            service = SourceGovernance(engine)
            if args.action == "claim":
                result = service.claim(AliasClaim.model_validate(request))
            elif args.action == "status":
                result = service.change_status(StatusChange.model_validate(request))
            elif args.action == "resolve":
                result = service.resolve(args.namespace, args.value)
            else:
                result = service.inspect(args.document_id)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result.get("status") == "conflicted" else 0
    except Exception as error:
        # Validation and DB diagnostics can contain raw inputs or connection details.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
