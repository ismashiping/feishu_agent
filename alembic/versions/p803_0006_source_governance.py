"""Explicit source aliases and audited governance states."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "p803_0006"
down_revision = "p802_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_aliases",
        sa.Column("namespace", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), primary_key=True),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("namespace IN ('pmid','doi','pdf_sha256')", name="ck_alias_namespace"),
    )
    op.create_table(
        "source_status_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("request", JSONB(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("document_id", "event_id", name="uq_source_event_document"),
    )
    op.create_table(
        "source_states",
        sa.Column("document_id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "event_id"],
            ["source_status_events.document_id", "source_status_events.event_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('normal','corrected','retracted','withdrawn','expression_of_concern')",
            name="ck_source_status",
        ),
    )


def downgrade():
    op.drop_table("source_states")
    op.drop_table("source_status_events")
    op.drop_table("source_aliases")
