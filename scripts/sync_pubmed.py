"""Explicit bounded PubMed window ingestion; no automatic next-window scheduling."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--snapshot-dir", type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_tokens <= 512:
        parser.error("max-tokens must be 1..512")
    if not args.dry_run and (args.model_dir is None or args.snapshot_dir is None):
        parser.error("Publishing requires model-dir and snapshot-dir")
    from contextlib import ExitStack

    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.adapters.postgres.maintenance import OnlineBatchRepository
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.adapters.pubmed_online import open_pubmed
    from clinical_agent.application.online_updates import OnlineUpdateService
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.maintenance import OnlineUpdateRequest

    try:
        with args.request.open("rb") as stream:
            body = stream.read(65537)
        if len(body) > 65536:
            raise ValueError("request_too_large")
        request = OnlineUpdateRequest.model_validate({**json.loads(body), "dry_run": args.dry_run})
        with ExitStack() as stack:
            engine = stack.enter_context(database_engine(DatabaseSettings()))
            client = stack.enter_context(open_pubmed())
            reader = PostgresStore(engine)

            def forbidden(*args, **kwargs):
                raise AssertionError("dry_run_publication")

            run_local = forbidden
            if not request.dry_run:
                from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
                from clinical_agent.adapters.offline import OfflineReader
                from clinical_agent.adapters.postgres.online_publication import (
                    OnlinePublicationStore,
                )
                from clinical_agent.application.ingestion import IngestionService
                from clinical_agent.domain.chunking import ChunkingPolicy

                store = OnlinePublicationStore(engine)
                ingestion = IngestionService(
                    reader=OfflineReader(args.snapshot_dir),
                    embedder=load_local_embedder(LocalModelConfig(snapshot_dir=args.model_dir)),
                    store=store,
                    policy=ChunkingPolicy(max_tokens=args.max_tokens),
                )
                run_local = UpdateService(
                    ledger=PostgresUpdateLedger(engine), reader=reader, publish=ingestion.ingest
                ).run
            result = OnlineUpdateService(
                search=client,
                repository=OnlineBatchRepository(engine),
                run_local=run_local,
                reader=reader,
                governance=SourceGovernance(engine),
                prepare_publication=store.configure if not request.dry_run else None,
            ).run(request)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in {"completed", "dry_run"} else 1
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
