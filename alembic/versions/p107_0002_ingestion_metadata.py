"""Retain real parser and processing metadata, preserving legacy rows without fabrication."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p107_0002"
down_revision = "p106_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("ingestion_metadata", postgresql.JSONB(none_as_null=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_documents_ingestion_metadata",
        "documents",
        "ingestion_metadata IS NULL OR jsonb_typeof(ingestion_metadata)='object'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_ingestion_metadata", "documents", type_="check")
    op.drop_column("documents", "ingestion_metadata")
