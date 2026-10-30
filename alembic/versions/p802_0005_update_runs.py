"""Persistent local update cursors and audited runs."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "p802_0005"
down_revision = "p801_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "update_cursors",
        sa.Column("batch_id", sa.Text(), primary_key=True),
        sa.Column("scope_hash", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "update_runs",
        sa.Column("run_id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
    )


def downgrade():
    op.drop_table("update_runs")
    op.drop_table("update_cursors")
