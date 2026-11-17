"""Portfolio repositories (schema-spec §5 tables).

Functions here only read/write rows; they never commit. Transaction boundaries
belong to the calling service so financial writes stay atomic (schema-spec §15.1).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import (
    Asset,
    CashLedgerEntry,
    Holding,
    MarketCandle,
    Portfolio,
    Transaction,
)


def create_portfolio(
    session: Session,
    name: str,
    reporting_currency: str,
    description: str | None = None,
    settings: dict | None = None,
) -> Portfolio:
    portfolio = Portfolio(
        name=name,
        description=description,
        reporting_currency=reporting_currency,
        status="ACTIVE",
        settings=settings,
    )
    session.add(portfolio)
    session.flush()
    return portfolio


def get_portfolio(session: Session, portfolio_id: uuid.UUID) -> Portfolio | None:
    return session.get(Portfolio, portfolio_id)


def update_portfolio(session: Session, portfolio: Portfolio, **values) -> Portfolio:
    for field, value in values.items():
        if value is not None:
            setattr(portfolio, field, value)
    portfolio.updated_at = datetime.now(timezone.utc)
    session.flush()
    return portfolio


def delete_portfolio(session: Session, portfolio: Portfolio) -> None:
    session.delete(portfolio)
    session.flush()


def has_transactions(session: Session, portfolio_id: uuid.UUID) -> bool:
    return (
        session.query(Transaction.id)
        .filter(Transaction.portfolio_id == portfolio_id)
        .first()
        is not None
    )


def list_portfolios(session: Session) -> list[Portfolio]:
    return list(session.scalars(select(Portfolio).order_by(Portfolio.created_at)))


def find_transaction_by_idempotency_key(
    session: Session, portfolio_id: uuid.UUID, idempotency_key: str
) -> Transaction | None:
    return session.scalars(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.idempotency_key == idempotency_key,
        )
    ).first()


def get_transaction(session: Session, transaction_id: uuid.UUID) -> Transaction | None:
    return session.get(Transaction, transaction_id)


def list_transactions_page(
    session: Session,
    portfolio_id: uuid.UUID | None = None,
    transaction_type: str | None = None,
    limit: int = 50,
    cursor_transaction: Transaction | None = None,
) -> tuple[list[Transaction], bool]:
    """Deterministic (transaction_date, id) ordering; opaque cursor via last row."""
    query = select(Transaction)
    if portfolio_id is not None:
        query = query.where(Transaction.portfolio_id == portfolio_id)
    if transaction_type is not None:
        query = query.where(Transaction.transaction_type == transaction_type)
    if cursor_transaction is not None:
        query = query.where(
            (Transaction.transaction_date, Transaction.id)
            > (cursor_transaction.transaction_date, cursor_transaction.id)
        )
    query = query.order_by(Transaction.transaction_date, Transaction.id).limit(limit + 1)
    rows = list(session.scalars(query))
    has_more = len(rows) > limit
    return rows[:limit], has_more


def list_transactions(session: Session, portfolio_id: uuid.UUID) -> list[Transaction]:
    return list(
        session.scalars(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date, Transaction.created_at)
        )
    )


def add_transaction(session: Session, **values) -> Transaction:
    transaction = Transaction(**values)
    session.add(transaction)
    session.flush()
    return transaction


def add_ledger_entry(session: Session, **values) -> CashLedgerEntry:
    entry = CashLedgerEntry(**values)
    session.add(entry)
    session.flush()
    return entry


def cash_balance(session: Session, portfolio_id: uuid.UUID, currency: str) -> float:
    total = session.scalar(
        select(func.coalesce(func.sum(CashLedgerEntry.amount), 0)).where(
            CashLedgerEntry.portfolio_id == portfolio_id,
            CashLedgerEntry.currency == currency,
        )
    )
    return total or 0


def ledger_entries(session: Session, portfolio_id: uuid.UUID) -> list[CashLedgerEntry]:
    return list(
        session.scalars(
            select(CashLedgerEntry)
            .where(CashLedgerEntry.portfolio_id == portfolio_id)
            .order_by(CashLedgerEntry.effective_at, CashLedgerEntry.created_at)
        )
    )


def ledger_entries_for_transaction(
    session: Session, transaction_id: uuid.UUID
) -> list[CashLedgerEntry]:
    return list(
        session.scalars(
            select(CashLedgerEntry).where(CashLedgerEntry.transaction_id == transaction_id)
        )
    )


def list_holdings(session: Session, portfolio_id: uuid.UUID) -> list[Holding]:
    return list(
        session.scalars(
            select(Holding)
            .where(Holding.portfolio_id == portfolio_id)
            .order_by(Holding.asset_id)
        )
    )


def get_holding(session: Session, portfolio_id: uuid.UUID, asset_id: uuid.UUID) -> Holding | None:
    return session.scalars(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id, Holding.asset_id == asset_id
        )
    ).first()


def upsert_holding(
    session: Session,
    portfolio_id: uuid.UUID,
    asset_id: uuid.UUID,
    quantity,
    average_cost,
    cost_basis,
    cost_currency: str,
    calculation_status: str,
    calculated_at: datetime,
) -> Holding:
    holding = get_holding(session, portfolio_id, asset_id)
    if holding is None:
        holding = Holding(portfolio_id=portfolio_id, asset_id=asset_id)
        session.add(holding)
    holding.quantity = quantity
    holding.average_cost = average_cost
    holding.cost_basis = cost_basis
    holding.cost_currency = cost_currency
    holding.calculation_status = calculation_status
    holding.last_calculated_at = calculated_at
    session.flush()
    return holding


def delete_holding(session: Session, holding: Holding) -> None:
    session.delete(holding)
    session.flush()


def get_asset(session: Session, asset_id: uuid.UUID) -> Asset | None:
    return session.get(Asset, asset_id)


def latest_close_price(session: Session, asset_id: uuid.UUID) -> tuple[float, datetime] | None:
    """Latest stored candle close for an asset. No provider fetch, no fabricated prices."""
    row = session.execute(
        select(MarketCandle.close_price, MarketCandle.close_time, MarketCandle.open_time)
        .where(MarketCandle.asset_id == asset_id)
        .order_by(MarketCandle.open_time.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    close_price, close_time, open_time = row
    return float(close_price), (close_time or open_time)


def add_snapshot(session: Session, **values) -> None:
    from app.database.models import PortfolioSnapshot

    session.add(PortfolioSnapshot(**values))
    session.flush()
