"""Add isolated fulltext cache to the existing PostgreSQL database."""
from alembic import op

revision = 'p1001_0008'
down_revision = 'p804_0007'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE fulltext_indexes (
        pmid text PRIMARY KEY, signature text NOT NULL, payload jsonb NOT NULL,
        expires_at timestamptz NOT NULL)''')
    op.execute('''CREATE TABLE fulltext_vectors (
        chunk_id uuid PRIMARY KEY, pmid text NOT NULL REFERENCES fulltext_indexes(pmid),
        payload jsonb NOT NULL, embedding vector(768) NOT NULL)''')
    op.execute('CREATE INDEX ix_fulltext_vectors_pmid ON fulltext_vectors(pmid)')


def downgrade():
    op.drop_table('fulltext_vectors')
    op.drop_table('fulltext_indexes')
