"""Online frozen windows and isolated rebuild staging."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "p804_0007"
down_revision = "p803_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "online_update_batches",
        sa.Column("batch_id", sa.Text(), primary_key=True),
        sa.Column("scope_hash", sa.Text(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
    )
    op.create_table(
        "rebuild_runs",
        sa.Column("run_id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_signature", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("evaluation_status", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("rebuild_runs")
    op.drop_table("online_update_batches")
