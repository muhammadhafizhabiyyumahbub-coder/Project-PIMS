"""add watchlists and watchlist_items tables

Revision ID: a3f5c7d9e1b2
Revises: f2b3c4d5e6a7 (backtest rule columns)
Create Date: 2026-11-28

Watchlist module (api-spec §17); two-table schema approved in
docs/decisions/technical-decisions.md §7.17. Single-user: no user_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3f5c7d9e1b2"
down_revision: Union[str, None] = "f2b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watchlist_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["watchlist_id"], ["watchlists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "watchlist_id", "asset_id", name="uq_watchlist_item_asset"
        ),
    )
    op.create_index(
        "ix_watchlist_items_watchlist_id", "watchlist_items", ["watchlist_id"]
    )
    op.create_index(
        "ix_watchlist_items_asset_id", "watchlist_items", ["asset_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_watchlist_items_asset_id", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_watchlist_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
