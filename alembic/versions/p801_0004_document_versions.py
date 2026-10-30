"""Retain immutable prepared evidence versions beside the active search projection."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "p801_0004"
down_revision = "p501_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_versions",
        sa.Column("version_id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("prepared", JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "uq_document_versions_active",
        "document_versions",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade():
    op.drop_index("uq_document_versions_active", table_name="document_versions")
    op.drop_table("document_versions")
