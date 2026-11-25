"""add_backtest_metrics

Revision ID: 5c7e2a90b3d1
Revises: 8f3a2d91c4b5
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5c7e2a90b3d1"
down_revision: Union[str, None] = "8f3a2d91c4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
    )
    op.create_index(
        "ix_backtest_metrics_analytics_run_id",
        "backtest_metrics",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_metrics_analytics_run_id", table_name="backtest_metrics")
    op.drop_table("backtest_metrics")
