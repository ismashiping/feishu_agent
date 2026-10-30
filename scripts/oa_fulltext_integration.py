"""Opt-in isolated database + real E5 cache acceptance; no production migration or messages."""

import json
import sys
from pathlib import Path
from time import monotonic

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DataError

from alembic import command
from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
from clinical_agent.adapters.oa_fulltext import parse_jats
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore
from clinical_agent.application.fulltext import FulltextService
from clinical_agent.application.oa_fulltext import SIGNATURE
from clinical_agent.application.openalex import record_hit
from clinical_agent.domain.openalex import OpenAlexProvenance, OpenAlexRecord
from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult


def main():
    root = Path(sys.argv[1])
    output = root / (sys.argv[2] if len(sys.argv) > 2 else "result")
    output.mkdir(exist_ok=False)
    settings = DatabaseSettings()
    assert settings.name.startswith("clinical_agent_test_oa_stage3_")
    fixture = root / "fixtures"
    record = OpenAlexRecord.model_validate_json((fixture / "mri-record.json").read_text())
    record.verify_snapshot()
    raw = (fixture / "mri-fulltext.xml").read_bytes()
    manifest = json.loads((fixture / "manifest.json").read_text())
    from hashlib import sha256

    assert sha256(raw).hexdigest() == manifest["sha256"]

    class Source:
        calls = 0

        def fetch_record(self, selected, deadline, count):
            self.calls += 1
            return manifest["license"], manifest["source_url"], raw, parse_jats(raw, selected)

    with database_engine(settings) as engine:
        config = Config(str(root / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        source = Source()
        model = load_local_embedder(LocalModelConfig(snapshot_dir=Path("/app/model")))

        class MeteredEmbedder:
            passage_calls = 0
            passage_chunks = 0
            query_calls = 0

            def count_tokens(self, value):
                return model.count_tokens(value)

            def embed_passages(self, texts, *, deadline):
                self.passage_calls += 1
                self.passage_chunks += len(texts)
                return model.embed_passages(texts, deadline=deadline)

            def embed_query(self, question):
                self.query_calls += 1
                return model.embed_query(question)

        embedder = MeteredEmbedder()
        store = PostgresFulltextStore(engine, openalex=True)
        service = FulltextService(None, None, embedder, oa_source=source, oa_store=store)
        from datetime import UTC, datetime

        retrieval = RetrievalResult(
            scope="online",
            options=RetrievalOptions(),
            embedding_info=None,
            hits=[record_hit(record, datetime.now(UTC))],
            search_provenance=OpenAlexProvenance.model_validate_json(
                (fixture / "search-provenance.json").read_text()
            ),
        )
        runs = []
        for mode in ["cold", "warm", "expired_same_content"]:
            if mode == "expired_same_content":
                with engine.begin() as connection:
                    connection.execute(
                        text("UPDATE oa_fulltext_indexes SET expires_at=now()-interval '1 day'")
                    )
            started = monotonic()
            result = service.enrich(
                "Which CT and MRI scanners, sequences, and contrast agents were used?",
                retrieval,
                deadline=monotonic() + 35,
            )
            runs.append(
                {
                    "mode": mode,
                    "seconds": round(monotonic() - started, 3),
                    "source_calls": source.calls,
                    "passage_embedding_calls": embedder.passage_calls,
                    "passage_embedding_chunks": embedder.passage_chunks,
                    "query_embedding_calls": embedder.query_calls,
                    "passages": len(result.hits[0].fulltext),
                    "sections": [p.section for p in result.hits[0].fulltext],
                    "warnings": result.warnings,
                }
            )
            (output / (mode + ".json")).write_text(result.model_dump_json(indent=2))
        with engine.connect() as connection:
            rows = connection.scalar(text("SELECT count(*) FROM oa_fulltext_vectors"))
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        payload = store.load(
            "doi:" + record.doi,
            SIGNATURE,
        )
        rollback_verified = False
        if payload:
            try:
                store.publish(
                    "doi:" + record.doi,
                    "bad-signature",
                    payload,
                    [[1.0]] * len(payload["passages"]),
                )
            except DataError as error:
                assert error.orig.sqlstate == "22000"
                rollback_verified = (
                    store.load(
                        "doi:" + record.doi,
                        SIGNATURE,
                    )
                    == payload
                )
        summary = {
            "source": "saved real licensed OAI response; HTTP verified separately",
            "database": settings.name,
            "revision": revision,
            "vector_rows": rows,
            "max_chunk_tokens": max(
                model.count_tokens("passage: " + p["text"]) for p in payload["passages"]
            )
            if payload
            else None,
            "runs": runs,
            "atomic_rollback_verified": rollback_verified,
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary), flush=True)
        assert rows > 0 and rollback_verified
        assert all(run["passages"] == 2 for run in runs)
        assert runs[1]["source_calls"] == 1
        assert runs[1]["passage_embedding_calls"] == 1
        assert runs[2]["source_calls"] == 2 and runs[2]["passage_embedding_calls"] == 1


if __name__ == "__main__":
    main()
