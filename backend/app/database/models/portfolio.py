"""Portfolio domain models per schema-spec.md §5 (approved 2026-11-17, Stage A)."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.database.models.core import utc_now

# Money/quantity columns per schema-spec §3.4.
MONEY = NUMERIC(30, 12)

TRANSACTION_TYPES = ("BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "FEE", "DIVIDEND", "INTEREST")
# Cash ledger sign convention (explicit per schema-spec §5.2 constraint):
# amount > 0 = cash inflow (DEPOSIT, SELL proceeds, DIVIDEND, INTEREST),
# amount < 0 = cash outflow (WITHDRAWAL, BUY total cost, FEE).
LEDGER_ENTRY_TYPES = ("DEPOSIT", "WITHDRAWAL", "BUY", "SELL", "FEE", "DIVIDEND", "INTEREST", "ADJUSTMENT")
PORTFOLIO_STATUSES = ("ACTIVE", "ARCHIVED")
CALCULATION_STATUSES = ("VALID", "PARTIAL", "INVALID", "PENDING")
VALUATION_STATUSES = ("COMPLETE", "PARTIAL", "STALE", "UNAVAILABLE")


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_portfolio_status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporting_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('BUY','SELL','DEPOSIT','WITHDRAWAL','FEE','DIVIDEND','INTEREST')",
            name="ck_transaction_type",
        ),
        CheckConstraint("gross_amount >= 0", name="ck_transaction_gross_non_negative"),
        CheckConstraint("fee_amount >= 0", name="ck_transaction_fee_non_negative"),
        # Idempotency scope: one key per portfolio (schema-spec §5.2).
        UniqueConstraint("portfolio_id", "idempotency_key", name="uq_transaction_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    gross_amount: Mapped[float] = mapped_column(MONEY, nullable=False)
    fee_amount: Mapped[float] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange_rate: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DB column is "metadata" per schema-spec §5.2; attribute differs because
    # Declarative reserves the "metadata" attribute name.
    tx_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CashLedgerEntry(Base):
    __tablename__ = "cash_ledger"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('DEPOSIT','WITHDRAWAL','BUY','SELL','FEE','DIVIDEND','INTEREST','ADJUSTMENT')",
            name="ck_ledger_entry_type",
        ),
        CheckConstraint("amount <> 0", name="ck_ledger_amount_non_zero"),
        # One ledger entry per source transaction prevents double counting (portfolio-engine-spec §5.3).
        UniqueConstraint("transaction_id", name="uq_ledger_transaction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, unique=True
    )
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[float] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ledger_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_holding_quantity_non_negative"),
        CheckConstraint(
            "calculation_status IN ('VALID','PARTIAL','INVALID','PENDING')",
            name="ck_holding_calculation_status",
        ),
        UniqueConstraint("portfolio_id", "asset_id", name="uq_holding_portfolio_asset"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(MONEY, nullable=False)
    average_cost: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    cost_basis: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    calculation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="VALID")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        CheckConstraint(
            "valuation_status IN ('COMPLETE','PARTIAL','STALE','UNAVAILABLE')",
            name="ck_snapshot_valuation_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False, index=True
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_value: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    cash_value: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    invested_value: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    reporting_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    valuation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    snapshot_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
