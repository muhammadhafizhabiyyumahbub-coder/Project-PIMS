"""Portfolio service: atomic transaction recording + holdings persistence.

Financial writes are atomic (schema-spec §15.1): the transactions row and its
cash_ledger entry are committed together or not at all. Idempotency is enforced
per portfolio (schema-spec §15.2).

Stage A constraint: transaction.currency must equal the portfolio reporting
currency. Multi-currency cash and FX conversion are deferred (portfolio-engine
spec §5.4 / §8.2 require conversion before summing; not in this stage).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.repositories import portfolio as repo
from app.engines.portfolio.holdings import (
    CASH_OUTFLOW,
    cash_movement_amount,
    quantize,
    replay_holdings,
    utc_now,
)

SUPPORTED_TYPES = ("BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "FEE", "DIVIDEND", "INTEREST")
ASSET_TYPES = ("BUY", "SELL")
CASH_TYPES = ("DEPOSIT", "WITHDRAWAL", "FEE", "DIVIDEND", "INTEREST")

SNAPSHOT_STATUS_REASONS = {
    "COMPLETE": "All held positions priced from fresh stored candles; totals are final.",
    "PARTIAL": "At least one position has no stored price; unavailable values are stored as NULL.",
    "STALE": "Stored prices are older than the freshness policy; values are withheld, not estimated.",
    "UNAVAILABLE": "No transactions or holdings; only cash (if any) is meaningful.",
}


def serialize_optional(value) -> str | None:
    """Decimal -> plain string, None stays None (api-spec §4.3: no zero placeholder)."""
    if value is None:
        return None
    return format(Decimal(str(value)).normalize(), "f")


class TransactionError(Exception):
    """Rejected transaction; nothing is written."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def record_transaction(
    session: Session,
    portfolio_id: uuid.UUID,
    transaction_type: str,
    *,
    asset_id: uuid.UUID | None = None,
    quantity: Decimal | None = None,
    price: Decimal | None = None,
    gross_amount: Decimal | None = None,
    fee_amount: Decimal = Decimal("0"),
    currency: str | None = None,
    transaction_date: datetime | None = None,
    idempotency_key: str | None = None,
    external_reference: str | None = None,
    notes: str | None = None,
) -> tuple[object, bool]:
    """Validate, persist transaction + ledger atomically, refresh holdings.

    Returns (transaction, created). created=False signals an idempotent replay.
    """
    if transaction_type not in SUPPORTED_TYPES:
        raise TransactionError("UNSUPPORTED_TYPE", f"transaction type {transaction_type} is not supported")
    portfolio = repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise TransactionError("PORTFOLIO_NOT_FOUND", f"portfolio {portfolio_id} not found")
    if portfolio.status != "ACTIVE":
        raise TransactionError("PORTFOLIO_INACTIVE", f"portfolio {portfolio_id} is {portfolio.status}")
    currency = currency or portfolio.reporting_currency
    if currency != portfolio.reporting_currency:
        raise TransactionError(
            "CURRENCY_MISMATCH",
            "multi-currency transactions are not supported in Stage A; "
            f"got {currency}, portfolio reports in {portfolio.reporting_currency}",
        )
    fee = Decimal(str(fee_amount))
    if fee < 0:
        raise TransactionError("NEGATIVE_FEE", "fee_amount must not be negative")
    transaction_date = transaction_date or utc_now()

    # Idempotent replay: same key returns the original transaction untouched.
    if idempotency_key is not None:
        existing = repo.find_transaction_by_idempotency_key(session, portfolio_id, idempotency_key)
        if existing is not None:
            _assert_payload_matches(existing, transaction_type, asset_id, quantity, price, fee, gross_amount, currency)
            return existing, False

    if transaction_type in ASSET_TYPES:
        transaction = _record_asset_transaction(
            session,
            portfolio,
            transaction_type,
            asset_id,
            quantity,
            price,
            fee,
            currency,
            transaction_date,
            idempotency_key,
            external_reference,
            notes,
        )
    else:
        transaction = _record_cash_transaction(
            session,
            portfolio,
            transaction_type,
            asset_id,
            quantity,
            price,
            gross_amount,
            fee,
            currency,
            transaction_date,
            idempotency_key,
            external_reference,
            notes,
        )

    _persist_holdings(session, portfolio_id)
    session.commit()
    return transaction, True


def _assert_payload_matches(existing, transaction_type, asset_id, quantity, price, fee, gross_amount, currency) -> None:
    """Duplicate key with a different payload is a client bug, not a replay
    (api-spec §22: key/payload conflicts must be handled)."""
    same = (
        existing.transaction_type == transaction_type
        and existing.asset_id == asset_id
        and existing.currency == currency
        and (existing.quantity is None) == (quantity is None)
        and (existing.price is None) == (price is None)
        and (existing.gross_amount is None) == (gross_amount is None)
        and (
            existing.quantity is None
            or Decimal(str(existing.quantity)) == Decimal(str(quantity))
        )
        and (
            existing.price is None
            or Decimal(str(existing.price)) == Decimal(str(price))
        )
        and (
            existing.gross_amount is None
            or Decimal(str(existing.gross_amount)) == Decimal(str(gross_amount))
        )
        and Decimal(str(existing.fee_amount)) == Decimal(str(fee))
    )
    if not same:
        raise TransactionError(
            "IDEMPOTENCY_CONFLICT",
            "idempotency key was already used with a different payload",
        )


def _record_asset_transaction(
    session,
    portfolio,
    transaction_type,
    asset_id,
    quantity,
    price,
    fee,
    currency,
    transaction_date,
    idempotency_key,
    external_reference,
    notes,
):
    if asset_id is None:
        raise TransactionError("ASSET_REQUIRED", f"{transaction_type} requires an asset")
    if repo.get_asset(session, asset_id) is None:
        raise TransactionError("ASSET_NOT_FOUND", f"asset {asset_id} not found")
    quantity_d = _require_amount(quantity, "quantity")
    price_d = _require_amount(price, "price")
    if quantity_d <= 0 or price_d <= 0:
        raise TransactionError("NON_POSITIVE_AMOUNT", "quantity and price must be positive")
    gross = quantity_d * price_d

    if transaction_type == "SELL":
        holdings = replay_holdings(repo.list_transactions(session, portfolio.id))
        current = holdings.get(asset_id)
        available = current.quantity if current else Decimal("0")
        if quantity_d > available:
            raise TransactionError(
                "INSUFFICIENT_HOLDINGS",
                f"SELL {quantity_d} exceeds available holdings {available} (shorting unsupported)",
            )
        net_proceeds = quantize(gross) - quantize(fee)
        if net_proceeds <= 0:
            raise TransactionError(
                "FEE_EXCEEDS_PROCEEDS",
                f"SELL net proceeds {net_proceeds} must be positive (fee {fee} >= gross {gross})",
            )

    if transaction_type == "BUY":
        # Owner decision §7.8 (2026-11-17): no margin in MVP. BUY outflow is
        # qty*price + fee; must not exceed cash balance. Computed on quantized
        # amounts so the check matches the ledger entries exactly (boundary
        # equality passes, one smallest unit short is rejected).
        balance = Decimal(str(repo.cash_balance(session, portfolio.id, currency)))
        outflow = quantize(gross) + quantize(fee)
        if outflow > balance:
            raise TransactionError(
                "INSUFFICIENT_CASH",
                f"BUY outflow {outflow} exceeds available cash {balance} (no margin in MVP)",
            )

    transaction = repo.add_transaction(
        session,
        portfolio_id=portfolio.id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        quantity=quantize(quantity_d),
        price=quantize(price_d),
        gross_amount=quantize(gross),
        fee_amount=quantize(fee),
        currency=currency,
        idempotency_key=idempotency_key,
        external_reference=external_reference,
        notes=notes,
    )
    amount = cash_movement_amount(transaction)
    repo.add_ledger_entry(
        session,
        portfolio_id=portfolio.id,
        transaction_id=transaction.id,
        entry_type=transaction_type,
        amount=quantize(amount),
        currency=currency,
        effective_at=transaction_date,
        description=f"{transaction_type} {quantity_d} @ {price_d}",
    )
    return transaction


def _record_cash_transaction(
    session,
    portfolio,
    transaction_type,
    asset_id,
    quantity,
    price,
    gross_amount,
    fee,
    currency,
    transaction_date,
    idempotency_key,
    external_reference,
    notes,
):
    if asset_id is not None:
        raise TransactionError("ASSET_NOT_ALLOWED", f"{transaction_type} must not reference an asset")
    if quantity is not None or price is not None:
        raise TransactionError("FIELD_NOT_ALLOWED", f"{transaction_type} must not carry quantity/price")
    amount = _require_amount(gross_amount, "gross_amount")
    if amount <= 0:
        raise TransactionError("NON_POSITIVE_AMOUNT", "gross_amount must be positive")

    if transaction_type in CASH_OUTFLOW:
        balance = quantize(Decimal(str(repo.cash_balance(session, portfolio.id, currency))))
        outflow = quantize(amount + fee)
        if outflow > balance:
            raise TransactionError(
                "INSUFFICIENT_CASH",
                f"cash outflow {outflow} exceeds available balance {balance}",
            )

    transaction = repo.add_transaction(
        session,
        portfolio_id=portfolio.id,
        asset_id=None,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        quantity=None,
        price=None,
        gross_amount=quantize(amount),
        fee_amount=quantize(fee),
        currency=currency,
        idempotency_key=idempotency_key,
        external_reference=external_reference,
        notes=notes,
    )
    ledger_amount = cash_movement_amount(transaction)
    repo.add_ledger_entry(
        session,
        portfolio_id=portfolio.id,
        transaction_id=transaction.id,
        entry_type=transaction_type,
        amount=quantize(ledger_amount),
        currency=currency,
        effective_at=transaction_date,
        description=transaction_type,
    )
    return transaction


def _require_amount(value, field_name: str) -> Decimal:
    if value is None:
        raise TransactionError("MISSING_FIELD", f"{field_name} is required")
    return Decimal(str(value))


def _persist_holdings(session, portfolio_id: uuid.UUID) -> None:
    """Rebuild holdings from transaction history (derived data, reproducible)."""
    transactions = repo.list_transactions(session, portfolio_id)
    holdings = replay_holdings(transactions)
    seen_assets = set()
    for asset_id, state in holdings.items():
        seen_assets.add(asset_id)
        if state.quantity == 0:
            continue
        repo.upsert_holding(
            session,
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            quantity=quantize(state.quantity),
            average_cost=quantize(state.average_cost),
            cost_basis=quantize(state.cost_basis),
            cost_currency=next(
                (t.currency for t in transactions if t.asset_id == asset_id), None
            ),
            calculation_status="VALID",
            calculated_at=utc_now(),
        )


def write_snapshot(
    session,
    portfolio_id: uuid.UUID,
    valuation,
    idempotency_key: str | None = None,
) -> tuple[uuid.UUID, bool]:
    """Persist one snapshot from a ValuationResult; returns (id, created).

    Duplicate protection (owner decision §7.9, simplest honest rule): when an
    Idempotency-Key header is supplied, a snapshot already stored under that key
    for this portfolio is returned as-is (created=False) instead of writing a
    second row. Without a key every manual POST is a new snapshot, because a
    portfolio can legitimately be snapshotted twice in a row.

    Values the valuation could not produce are stored as NULL, never zero
    (portfolio-engine-spec §8.4); the status and a human-readable reason go in
    metadata so an incomplete snapshot explains itself.
    """
    if idempotency_key is not None:
        existing = repo.find_snapshot_by_idempotency_key(session, portfolio_id, idempotency_key)
        if existing is not None:
            return existing.id, False

    metadata = {
        "idempotency_key": idempotency_key,
        "realized_pnl": serialize_optional(valuation.realized_pnl),
        "unrealized_pnl": serialize_optional(valuation.unrealized_pnl),
        "valued_at": valuation.valued_at.isoformat(),
        "status_reason": SNAPSHOT_STATUS_REASONS.get(
            valuation.valuation_status, valuation.valuation_status
        ),
        "positions": [
            {
                "asset_id": str(p.asset_id),
                "symbol": p.symbol,
                "quantity": serialize_optional(p.quantity),
                "market_price": serialize_optional(p.market_price),
                "market_value": serialize_optional(p.market_value),
                "price_status": p.price_status,
            }
            for p in valuation.positions
        ],
    }
    snapshot = repo.add_snapshot(
        session,
        portfolio_id=portfolio_id,
        snapshot_at=valuation.valued_at,
        total_value=valuation.total_value,
        cash_value=valuation.cash_value,
        invested_value=valuation.invested_value,
        reporting_currency=valuation.reporting_currency,
        valuation_status=valuation.valuation_status,
        snapshot_metadata=metadata,
    )
    session.commit()
    return snapshot.id, True
