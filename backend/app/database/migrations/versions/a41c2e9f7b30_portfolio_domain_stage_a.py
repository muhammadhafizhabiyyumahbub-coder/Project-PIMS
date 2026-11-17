"""portfolio domain tables (Stage A, schema-spec §5)

Revision ID: a41c2e9f7b30
Revises: 3374e73084c0
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a41c2e9f7b30"
down_revision: Union[str, None] = "3374e73084c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(30, 12)


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reporting_currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_portfolio_status"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", MONEY, nullable=True),
        sa.Column("price", MONEY, nullable=True),
        sa.Column("gross_amount", MONEY, nullable=False),
        sa.Column("fee_amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("exchange_rate", MONEY, nullable=True),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.CheckConstraint(
            "transaction_type IN ('BUY','SELL','DEPOSIT','WITHDRAWAL','FEE','DIVIDEND','INTEREST')",
            name="ck_transaction_type",
        ),
        sa.CheckConstraint("gross_amount >= 0", name="ck_transaction_gross_non_negative"),
        sa.CheckConstraint("fee_amount >= 0", name="ck_transaction_fee_non_negative"),
        sa.UniqueConstraint("portfolio_id", "idempotency_key", name="uq_transaction_idempotency"),
    )
    op.create_index("ix_transactions_portfolio_id", "transactions", ["portfolio_id"])
    op.create_index("ix_transactions_asset_id", "transactions", ["asset_id"])
    op.create_index("ix_transactions_portfolio_date", "transactions", ["portfolio_id", "transaction_date"])
    op.create_index("ix_transactions_asset_date", "transactions", ["asset_id", "transaction_date"])

    op.create_table(
        "cash_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("entry_type", sa.String(length=30), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.CheckConstraint(
            "entry_type IN ('DEPOSIT','WITHDRAWAL','BUY','SELL','FEE','DIVIDEND','INTEREST','ADJUSTMENT')",
            name="ck_ledger_entry_type",
        ),
        sa.CheckConstraint("amount <> 0", name="ck_ledger_amount_non_zero"),
        sa.UniqueConstraint("transaction_id", name="uq_ledger_transaction"),
    )
    op.create_index("ix_cash_ledger_portfolio_id", "cash_ledger", ["portfolio_id"])
    op.create_index("ix_cash_ledger_portfolio_effective", "cash_ledger", ["portfolio_id", "effective_at"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("average_cost", MONEY, nullable=True),
        sa.Column("cost_basis", MONEY, nullable=True),
        sa.Column("cost_currency", sa.String(length=10), nullable=True),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculation_status", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.CheckConstraint("quantity >= 0", name="ck_holding_quantity_non_negative"),
        sa.CheckConstraint(
            "calculation_status IN ('VALID','PARTIAL','INVALID','PENDING')",
            name="ck_holding_calculation_status",
        ),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_holding_portfolio_asset"),
    )
    op.create_index("ix_holdings_portfolio_id", "holdings", ["portfolio_id"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_value", MONEY, nullable=True),
        sa.Column("cash_value", MONEY, nullable=True),
        sa.Column("invested_value", MONEY, nullable=True),
        sa.Column("reporting_currency", sa.String(length=10), nullable=False),
        sa.Column("valuation_status", sa.String(length=30), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.CheckConstraint(
            "valuation_status IN ('COMPLETE','PARTIAL','STALE','UNAVAILABLE')",
            name="ck_snapshot_valuation_status",
        ),
    )
    op.create_index("ix_portfolio_snapshots_portfolio_id", "portfolio_snapshots", ["portfolio_id"])
    op.create_index(
        "ix_portfolio_snapshots_portfolio_time",
        "portfolio_snapshots",
        ["portfolio_id", "snapshot_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_portfolio_time", table_name="portfolio_snapshots")
    op.drop_index("ix_portfolio_snapshots_portfolio_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_index("ix_holdings_portfolio_id", table_name="holdings")
    op.drop_table("holdings")
    op.drop_index("ix_cash_ledger_portfolio_effective", table_name="cash_ledger")
    op.drop_index("ix_cash_ledger_portfolio_id", table_name="cash_ledger")
    op.drop_table("cash_ledger")
    op.drop_index("ix_transactions_asset_date", table_name="transactions")
    op.drop_index("ix_transactions_portfolio_date", table_name="transactions")
    op.drop_index("ix_transactions_asset_id", table_name="transactions")
    op.drop_index("ix_transactions_portfolio_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("portfolios")
