"""Existing PostgreSQL persistence, atomic publication and scoped pgvector search."""

import json

from sqlalchemy import text


class PostgresFulltextStore:
    def __init__(self, engine, *, openalex=False):
        self.engine = engine
        self.index_table = "oa_fulltext_indexes" if openalex else "fulltext_indexes"
        self.vector_table = "oa_fulltext_vectors" if openalex else "fulltext_vectors"
        self.key_column = "paper_key" if openalex else "pmid"

    def load(self, pmid, signature):
        with self.engine.connect() as connection:
            row = connection.execute(
                text(f"""SELECT payload FROM {self.index_table}
                WHERE {self.key_column}=:pmid AND signature=:signature AND expires_at > now()"""),
                dict(pmid=pmid, signature=signature),
            ).scalar_one_or_none()
            return row

    def reuse_content(self, pmid, signature, digest):
        hash_field = "representation_hash" if self.key_column == "paper_key" else "content_hash"
        with self.engine.begin() as connection:
            found = connection.execute(
                text(f"""UPDATE {self.index_table}
                SET expires_at=now()+interval '30 days'
                WHERE {self.key_column}=:pmid AND signature=:signature
                AND payload->>'{hash_field}'=:digest RETURNING {self.key_column}"""),
                dict(pmid=pmid, signature=signature, digest=digest),
            ).scalar_one_or_none()
            return found is not None

    def publish(self, pmid, signature, payload, vectors):
        with self.engine.begin() as connection:
            connection.execute(
                text("""SELECT pg_advisory_xact_lock(hashtext(:pmid))"""), dict(pmid=pmid)
            )
            connection.execute(
                text(f"DELETE FROM {self.vector_table} WHERE {self.key_column}=:pmid"),
                dict(pmid=pmid),
            )
            connection.execute(
                text(f"""INSERT INTO {self.index_table}
                ({self.key_column}, signature, payload, expires_at) VALUES
                (:pmid, :signature, CAST(:payload AS jsonb), now()+interval '30 days')
                ON CONFLICT ({self.key_column}) DO UPDATE SET signature=excluded.signature,
                payload=excluded.payload, expires_at=excluded.expires_at"""),
                dict(pmid=pmid, signature=signature, payload=json.dumps(payload)),
            )
            for passage, vector in zip(payload["passages"], vectors, strict=True):
                connection.execute(
                    text(f"""INSERT INTO {self.vector_table}
                    (chunk_id, {self.key_column}, payload, embedding) VALUES
                    (:id, :pmid, CAST(:payload AS jsonb), CAST(:vector AS vector))"""),
                    dict(
                        id=passage["chunk_id"],
                        pmid=pmid,
                        payload=json.dumps(passage),
                        vector=str(vector),
                    ),
                )

    def search(self, pmid, vector, limit=2):
        with self.engine.connect() as connection:
            return list(
                connection.execute(
                    text(f"""SELECT payload FROM {self.vector_table}
                WHERE {self.key_column}=:pmid ORDER BY embedding <=> CAST(:vector AS vector)
                LIMIT :limit"""),
                    dict(pmid=pmid, vector=str(vector), limit=limit),
                ).scalars()
            )
