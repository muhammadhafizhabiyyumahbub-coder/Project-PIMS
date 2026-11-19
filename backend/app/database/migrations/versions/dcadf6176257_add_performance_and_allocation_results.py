"""add_performance_and_allocation_results

Revision ID: dcadf6176257
Revises: a41c2e9f7b30
Create Date: 2026-11-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'dcadf6176257'
down_revision: Union[str, None] = 'a41c2e9f7b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "performance_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_return", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("daily_return", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("cagr", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("reporting_currency", sa.String(length=10), nullable=False),
        sa.Column("methodology", sa.String(length=50), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
    )
    op.create_index("ix_performance_results_portfolio_id", "performance_results", ["portfolio_id"])

    op.create_table(
        "allocation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_type", sa.String(length=50), nullable=False),
        sa.Column("allocation_key", sa.String(length=150), nullable=False),
        sa.Column("market_value", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("allocation_percentage", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("reporting_currency", sa.String(length=10), nullable=False),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
    )
    op.create_index("ix_allocation_results_portfolio_id", "allocation_results", ["portfolio_id"])


def downgrade() -> None:
    op.drop_index("ix_allocation_results_portfolio_id", table_name="allocation_results")
    op.drop_table("allocation_results")
    op.drop_index("ix_performance_results_portfolio_id", table_name="performance_results")
    op.drop_table("performance_results")
