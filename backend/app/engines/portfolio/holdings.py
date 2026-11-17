"""Holdings calculator: derives holdings from authoritative transaction history.

Holdings are derived data (portfolio-engine-spec §6), reproducible from
transactions by an ordered replay. Cash movements do not change quantity.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.engines.portfolio.cost_basis import CostBasisState, apply_buy, apply_sell

QUANTITY_AFFECTING = {"BUY", "SELL"}
CASH_INFLOW = {"DEPOSIT", "DIVIDEND", "INTEREST"}
CASH_OUTFLOW = {"WITHDRAWAL", "FEE"}
LEDGER_ENTRY_TYPES = {
    "BUY": "BUY",
    "SELL": "SELL",
    "DEPOSIT": "DEPOSIT",
    "WITHDRAWAL": "WITHDRAWAL",
    "FEE": "FEE",
    "DIVIDEND": "DIVIDEND",
    "INTEREST": "INTEREST",
}


@dataclass
class HoldingState:
    asset_id: object
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal


def replay_holdings(transactions) -> dict[object, HoldingState]:
    """Replay transactions in execution order and return per-asset holding state."""
    ordered = sorted(transactions, key=lambda t: (t.transaction_date, t.created_at or t.transaction_date))
    states: dict[object, CostBasisState] = {}
    for transaction in ordered:
        if transaction.transaction_type not in QUANTITY_AFFECTING:
            continue
        if transaction.asset_id is None:
            raise ValueError(
                f"{transaction.transaction_type} transaction {transaction.id} has no asset"
            )
        state = states.get(transaction.asset_id, CostBasisState())
        quantity = Decimal(str(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fee = Decimal(str(transaction.fee_amount or 0))
        if transaction.transaction_type == "BUY":
            states[transaction.asset_id] = apply_buy(state, quantity, price, fee)
        else:
            states[transaction.asset_id] = apply_sell(state, quantity, price, fee)

    return {
        asset_id: HoldingState(
            asset_id=asset_id,
            quantity=state.quantity,
            average_cost=state.average_cost,
            cost_basis=state.cost_basis,
            realized_pnl=state.realized_pnl,
        )
        for asset_id, state in states.items()
    }


def cash_movement_amount(transaction) -> Decimal:
    """Cash effect of a transaction, with the sign convention of cash_ledger.

    positive = inflow, negative = outflow. BUY is a cash outflow of
    qty*price + fee; SELL is an inflow of qty*price - fee (spec §4.3/§4.4).
    """
    ttype = transaction.transaction_type
    fee = Decimal(str(transaction.fee_amount or 0))
    if ttype == "BUY":
        return -(Decimal(str(transaction.quantity or 0)) * Decimal(str(transaction.price or 0)) + fee)
    if ttype == "SELL":
        return (Decimal(str(transaction.quantity or 0)) * Decimal(str(transaction.price or 0))) - fee
    if ttype in CASH_INFLOW:
        return Decimal(str(transaction.gross_amount or 0)) - fee
    if ttype in CASH_OUTFLOW:
        return -(Decimal(str(transaction.gross_amount or 0)) + fee)
    raise ValueError(f"unsupported transaction type for cash movement: {ttype}")


def quantize(value: Decimal) -> Decimal:
    """Match storage scale NUMERIC(30,12)."""
    return value.quantize(Decimal("0.000000000001"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
