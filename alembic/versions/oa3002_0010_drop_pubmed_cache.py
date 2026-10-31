"""Remove stored PubMed abstracts and the retired PMID fulltext cache.

PDF rows in documents stay. Downgrade recreates empty cache tables only;
deleted abstract rows are not restored. This revision is not run on import.
"""

from alembic import op

revision = "oa3002_0010"
down_revision = "oa3001_0009"
branch_labels = None
depends_on = None

_PUBMED = "SELECT document_id FROM documents WHERE source_type = 'pubmed'"


def upgrade():
    op.execute(f"DELETE FROM source_states WHERE document_id IN ({_PUBMED})")
    op.execute(f"DELETE FROM source_status_events WHERE document_id IN ({_PUBMED})")
    op.execute(f"DELETE FROM source_aliases WHERE document_id IN ({_PUBMED})")
    op.execute(f"DELETE FROM document_versions WHERE document_id IN ({_PUBMED})")
    op.execute("DELETE FROM documents WHERE source_type = 'pubmed'")
    op.execute("DROP TABLE IF EXISTS fulltext_vectors")
    op.execute("DROP TABLE IF EXISTS fulltext_indexes")


def downgrade():
    op.execute("""CREATE TABLE fulltext_indexes (
        pmid text PRIMARY KEY, signature text NOT NULL, payload jsonb NOT NULL,
        expires_at timestamptz NOT NULL)""")
    op.execute("""CREATE TABLE fulltext_vectors (
        chunk_id uuid PRIMARY KEY, pmid text NOT NULL REFERENCES fulltext_indexes(pmid),
        payload jsonb NOT NULL, embedding vector(768) NOT NULL)""")
    op.execute("CREATE INDEX ix_fulltext_vectors_pmid ON fulltext_vectors(pmid)")
