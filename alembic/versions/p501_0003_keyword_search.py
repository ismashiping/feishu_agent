"""Add a generated keyword index without replacing evidence or vector identities."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p501_0003"
down_revision = "p107_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple'::regconfig, text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("ix_chunks_search_vector", "chunks", ["search_vector"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_chunks_search_vector", table_name="chunks")
    op.drop_column("chunks", "search_vector")
