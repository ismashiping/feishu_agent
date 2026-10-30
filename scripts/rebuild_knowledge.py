"""Explicit rebuild plan/stage/activate; staging never replaces live evidence."""

import argparse
import json
from pathlib import Path
from uuid import UUID


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("plan")
    stage = sub.add_parser("stage")
    stage.add_argument("--run-id", type=UUID, required=True)
    stage.add_argument("--model-dir", type=Path, required=True)
    stage.add_argument("--max-tokens", type=int, default=512)
    stage.add_argument("--evaluate", action="store_true")
    sub.add_parser("activate").add_argument("--run-id", type=UUID, required=True)
    args = parser.parse_args()
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.rebuild import KnowledgeRebuilder
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.maintenance import RebuildRequest

    try:
        with database_engine(DatabaseSettings()) as engine:
            rebuilder = KnowledgeRebuilder(engine)
            if args.action == "plan":
                result = rebuilder.plan()
            elif args.action == "activate":
                result = rebuilder.activate(args.run_id)
            else:
                from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder

                policy = ChunkingPolicy(max_tokens=args.max_tokens)
                if policy.max_tokens > 512:
                    raise ValueError("unsupported_token_budget")
                rebuilder = KnowledgeRebuilder(
                    engine, load_local_embedder(LocalModelConfig(snapshot_dir=args.model_dir))
                )
                result = rebuilder.stage(
                    RebuildRequest(run_id=args.run_id, policy=policy),
                    evaluate=rebuilder.evaluate if args.evaluate else None,
                )
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result.get("evaluation_status") in {"failed", "not_accepted"} else 0
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
