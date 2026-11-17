"""Cost basis engine: WEIGHTED AVERAGE COST (moving average).

Approved 2026-11-17 (technical-decisions.md §7.3 / project owner):
methodology = weighted average cost; FIFO deferred.

Assumptions (documented per AGENTS.md §9.1):
- All arithmetic uses Decimal, never float (schema-spec §3.4).
- BUY fee is capitalised into cost basis: TotalCost = qty*price + fee
  (portfolio-engine-spec §4.3).
- SELL fee is deducted from proceeds: NetProceeds = qty*price - fee
  (portfolio-engine-spec §4.4).
- Average cost is unchanged by a SELL; the allocated cost basis is removed
  in proportion to the quantity sold.
- No rounding is applied inside the engine. Callers quantize to the storage
  scale (NUMERIC(30,12)) at write time, so repeated replays stay reproducible.
"""
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True)
class CostBasisState:
    """Running position state for one (portfolio, asset) pair."""

    quantity: Decimal = ZERO
    cost_basis: Decimal = ZERO
    realized_pnl: Decimal = ZERO

    @property
    def average_cost(self) -> Decimal:
        if self.quantity == ZERO:
            return ZERO
        return self.cost_basis / self.quantity


def apply_buy(
    state: CostBasisState,
    quantity: Decimal,
    price: Decimal,
    fee: Decimal = ZERO,
) -> CostBasisState:
    """Add a purchase. Fee increases cost basis."""
    if quantity <= ZERO:
        raise ValueError("BUY quantity must be positive")
    if price < ZERO or fee < ZERO:
        raise ValueError("BUY price and fee must not be negative")
    return CostBasisState(
        quantity=state.quantity + quantity,
        cost_basis=state.cost_basis + (quantity * price) + fee,
        realized_pnl=state.realized_pnl,
    )


def apply_sell(
    state: CostBasisState,
    quantity: Decimal,
    price: Decimal,
    fee: Decimal = ZERO,
) -> CostBasisState:
    """Remove a sale. Fee reduces proceeds; realized P&L uses allocated average cost."""
    if quantity <= ZERO:
        raise ValueError("SELL quantity must be positive")
    if price < ZERO or fee < ZERO:
        raise ValueError("SELL price and fee must not be negative")
    if quantity > state.quantity:
        raise ValueError("SELL quantity exceeds available holdings (shorting unsupported)")
    allocated_cost = state.average_cost * quantity
    net_proceeds = (quantity * price) - fee
    return CostBasisState(
        quantity=state.quantity - quantity,
        cost_basis=state.cost_basis - allocated_cost,
        realized_pnl=state.realized_pnl + (net_proceeds - allocated_cost),
    )


def unrealized_pnl(state: CostBasisState, market_price: Decimal) -> Decimal:
    """UnrealizedPnL = CurrentMarketValue - RemainingCostBasis (spec §9.1)."""
    return (state.quantity * market_price) - state.cost_basis
