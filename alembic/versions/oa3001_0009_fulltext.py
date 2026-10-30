"""Add OA cache alongside immutable legacy PMID caches."""

from alembic import op

revision = "oa3001_0009"
down_revision = "p1001_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE oa_fulltext_indexes (
        paper_key text PRIMARY KEY, signature text NOT NULL,
        payload jsonb NOT NULL, expires_at timestamptz NOT NULL)""")
    op.execute("""CREATE TABLE oa_fulltext_vectors (
        chunk_id uuid PRIMARY KEY,
        paper_key text NOT NULL REFERENCES oa_fulltext_indexes(paper_key),
        payload jsonb NOT NULL, embedding vector(768) NOT NULL)""")
    op.execute("CREATE INDEX ix_oa_fulltext_vectors_key ON oa_fulltext_vectors(paper_key)")


def downgrade():
    op.drop_table("oa_fulltext_vectors")
    op.drop_table("oa_fulltext_indexes")
