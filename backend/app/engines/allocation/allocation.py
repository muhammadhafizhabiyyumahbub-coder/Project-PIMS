"""Allocation engine: actual distribution + concentration metrics.

Stage J scope (Project Owner decision): ACTUAL allocation only — target weights,
drift bands and rebalancing suggestions are not specified anywhere and are
deliberately NOT computed. The engine is read-only; nothing is persisted to the
analytics tables this round.

Spec rules honoured (allocation-engine-spec):
- Weight = value / valued-portfolio-value * 100 over the components that are
  actually valued. A position without a price keeps market_value=None and
  weight=None; it is never turned into zero and the totals are never
  renormalised to hide it (§11.2/§11.3). Coverage is reported explicitly.
- Sector/industry needs asset metadata that does not exist (assets has no sector
  column) -> null + reason, never invented (§7.2, §25).
- Values are already in the portfolio reporting currency (Portfolio Engine
  Stage A constraint), so no FX conversion is needed. If a non-reporting
  currency ever had to be converted and no rate exists, the report is degraded
  with a reason instead of inventing a rate (§3.3).
- Concentration is Top-N cumulative weight only; the spec defines no HHI, so
  none is computed (§12).
- Decimal only; weights are serialized as fixed-scale decimal strings.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.repositories import asset as asset_repo
from app.database.repositories import portfolio as repo
from app.engines.portfolio.valuation import value_portfolio

ZERO = Decimal(0)
HUNDRED = Decimal(100)
# schema-spec §7.4: allocation_percentage is NUMERIC(20,10).
PERCENT_SCALE = Decimal("0.0000000001")

CASH_CLASS = "Cash"
UNKNOWN = "Unknown"

NO_SECTOR_REASON = (
    "Sector/industry metadata is not stored for assets, so sector allocation "
    "is unavailable rather than invented (spec §7.2/§25)."
)
FX_REASON = (
    "A non-reporting-currency value must be converted but no fx_rates data is "
    "stored, so it cannot be converted (spec §3.3)."
)
# Denominator for every reported weight: valued positions + cash. Weights never
# cover unpriced positions and are never renormalised to force 100%.
WEIGHT_BASE = "priced_components_incl_cash"


def serialize_weight(value: Decimal | None) -> str | None:
    """Fixed-scale percentage string (schema §7.4); None stays None."""
    if value is None:
        return None
    return format(Decimal(str(value)).quantize(PERCENT_SCALE), "f")


@dataclass
class PositionInput:
    """One holding, already priced/valued by the Portfolio Engine."""

    asset_id: uuid.UUID
    symbol: str
    name: str | None
    asset_class: str | None
    market: str | None
    currency: str | None
    quantity: Decimal
    market_price: Decimal | None
    price_status: str  # AVAILABLE | MISSING | STALE
    price_time: datetime | None
    market_value: Decimal | None
    cost_basis: Decimal = ZERO


@dataclass
class AllocationInput:
    portfolio_id: uuid.UUID
    reporting_currency: str
    valuation_timestamp: datetime
    valuation_status: str  # COMPLETE | PARTIAL | STALE | UNAVAILABLE
    cash_value: Decimal
    positions: list[PositionInput]
    conversion_required: bool = False


@dataclass
class AllocationSlice:
    name: str
    market_value: Decimal | None
    weight: Decimal | None
    holdings_count: int


@dataclass
class IndividualAsset:
    asset_id: uuid.UUID
    symbol: str
    name: str | None
    asset_class: str
    market: str
    currency: str
    quantity: Decimal
    market_price: Decimal | None
    price_status: str
    price_time: datetime | None
    market_value: Decimal | None
    weight: Decimal | None


@dataclass
class UnpricedPosition:
    """A holding with no market price; cost basis is only a value proxy, not market value."""

    asset_id: uuid.UUID
    symbol: str
    quantity: Decimal
    cost_basis: Decimal


@dataclass
class AllocationResult:
    portfolio_id: uuid.UUID
    reporting_currency: str
    valuation_timestamp: datetime
    data_status: str
    data_status_reason: str | None
    total_value: Decimal | None
    cash_value: Decimal
    invested_value: Decimal
    coverage: dict
    categories: dict
    concentration: dict
    weight_base: str = WEIGHT_BASE
    unpriced_positions: list[UnpricedPosition] = field(default_factory=list)


def _weight(value: Decimal | None, total: Decimal) -> Decimal | None:
    if value is None or total <= ZERO:
        return None
    return value / total * HUNDRED


def _group(positions: list[PositionInput], key) -> dict[str, list[PositionInput]]:
    groups: dict[str, list[PositionInput]] = {}
    for position in positions:
        groups.setdefault(key(position), []).append(position)
    return groups


def _slices(groups: dict[str, list[PositionInput]], total: Decimal) -> list[AllocationSlice]:
    """One slice per group; a group with no valued member has a null value."""
    slices: list[AllocationSlice] = []
    for name, members in groups.items():
        valued = [m.market_value for m in members if m.market_value is not None]
        value = sum(valued, ZERO) if valued else None
        slices.append(
            AllocationSlice(
                name=name,
                market_value=value,
                weight=_weight(value, total),
                holdings_count=len(members),
            )
        )
    slices.sort(key=lambda s: (s.market_value is None, -(s.market_value or ZERO), s.name))
    return slices


def _top_n(weights: list[Decimal], n: int) -> Decimal | None:
    if not weights:
        return None
    return sum(weights[:n], ZERO)


def _add_cash(slices: list[AllocationSlice], name: str, cash: Decimal, total: Decimal) -> None:
    """Append the cash component, merging into an existing same-named slice."""
    for existing in slices:
        if existing.name == name:
            existing.market_value = (existing.market_value or ZERO) + cash
            existing.weight = _weight(existing.market_value, total)
            existing.holdings_count += 1
            return
    if cash != 0 or not slices:
        slices.append(AllocationSlice(name, cash, _weight(cash, total), 1))


def compute_allocation(data: AllocationInput) -> AllocationResult:
    """Pure allocation calculation; expected numbers are hand-computed in tests."""
    valued_positions = [p for p in data.positions if p.market_value is not None]
    unvalued = [p for p in data.positions if p.market_value is None]

    invested = sum((p.market_value for p in valued_positions), ZERO)
    valued_total = data.cash_value + invested

    total_components = len(data.positions) + 1  # every position plus cash
    covered_components = len(valued_positions) + 1  # cash is always present
    coverage_percentage = (
        Decimal(covered_components) / Decimal(total_components) * HUNDRED
        if total_components
        else None
    )
    # (a) honest position-count measure: share of HOLDINGS that actually have a
    # price. Cash is not a holding, so it is excluded here.
    position_coverage_percentage = (
        Decimal(len(valued_positions)) / Decimal(len(data.positions)) * HUNDRED
        if data.positions
        else None
    )
    # (b) honest value measure: share of KNOWN value. Cost basis is used only as
    # a proxy for unpriced positions — it is a purchase-cost figure, NOT market
    # value, and must never be reported as a price.
    unpriced_cost_basis = sum((p.cost_basis for p in unvalued), ZERO)
    value_coverage_denominator = invested + unpriced_cost_basis
    value_known_percentage = (
        invested / value_coverage_denominator * HUNDRED
        if value_coverage_denominator > ZERO
        else None
    )

    unpriced_positions = [
        UnpricedPosition(
            asset_id=p.asset_id,
            symbol=p.symbol,
            quantity=p.quantity,
            cost_basis=p.cost_basis,
        )
        for p in unvalued
    ]

    coverage = {
        "total_components": total_components,
        "covered_components": covered_components,
        "unvalued_components": len(unvalued),
        "coverage_percentage": coverage_percentage,
        "position_coverage_percentage": position_coverage_percentage,
        "value_known_percentage": value_known_percentage,
        "unpriced_positions": unpriced_positions,
    }

    if not data.positions and data.cash_value == 0:
        data_status = "UNAVAILABLE"
        data_status_reason = "Portfolio is empty; there is nothing to allocate."
    elif data.conversion_required:
        data_status = "PARTIAL"
        data_status_reason = FX_REASON
    else:
        data_status = data.valuation_status
        data_status_reason = None

    if unvalued:
        # A COMPLETE valuation cannot contain unvalued positions; keep the status
        # honest if the caller hands us contradictory input (spec §11.3).
        if data_status == "COMPLETE":
            data_status = "PARTIAL"
        if data_status_reason is None:
            data_status_reason = (
                f"{len(unvalued)} of {len(data.positions)} holding(s) have no price and "
                "are excluded from the weights; weights cover only the valued components."
            )

    # --- categories --------------------------------------------------------
    class_groups = _group(data.positions, lambda p: p.asset_class or UNKNOWN)
    market_groups = _group(data.positions, lambda p: p.market or UNKNOWN)
    currency_groups = _group(data.positions, lambda p: p.currency or UNKNOWN)

    class_slices = _slices(class_groups, valued_total)
    market_slices = _slices(market_groups, valued_total)
    currency_slices = _slices(currency_groups, valued_total)
    # Cash is a first-class component (§5.1 CASH, §10) and never double counts a
    # holding. A holding already classified "Cash" merges instead of duplicating.
    _add_cash(class_slices, CASH_CLASS, data.cash_value, valued_total)
    _add_cash(market_slices, CASH_CLASS, data.cash_value, valued_total)
    _add_cash(currency_slices, data.reporting_currency, data.cash_value, valued_total)

    individual = [
        IndividualAsset(
            asset_id=p.asset_id,
            symbol=p.symbol,
            name=p.name,
            asset_class=p.asset_class or UNKNOWN,
            market=p.market or UNKNOWN,
            currency=p.currency or UNKNOWN,
            quantity=p.quantity,
            market_price=p.market_price,
            price_status=p.price_status,
            price_time=p.price_time,
            market_value=p.market_value,
            weight=_weight(p.market_value, valued_total),
        )
        for p in data.positions
    ]

    # --- concentration -----------------------------------------------------
    ranked = sorted(valued_positions, key=lambda p: p.market_value, reverse=True)
    ranked_weights = [_weight(p.market_value, valued_total) for p in ranked]
    largest = ranked[0] if ranked else None

    largest_market = next((s.name for s in market_slices if s.market_value is not None), None)
    largest_currency = next((s.name for s in currency_slices if s.market_value is not None), None)

    concentration = {
        "largest_holding_symbol": largest.symbol if largest else None,
        "largest_holding_weight": _weight(largest.market_value, valued_total) if largest else None,
        "top_3_weight": _top_n(ranked_weights, 3),
        "top_5_weight": _top_n(ranked_weights, 5),
        "top_10_weight": _top_n(ranked_weights, 10),
        "largest_market": largest_market,
        "largest_currency": largest_currency,
        "largest_sector": None,
        "largest_sector_reason": NO_SECTOR_REASON,
    }

    return AllocationResult(
        portfolio_id=data.portfolio_id,
        reporting_currency=data.reporting_currency,
        valuation_timestamp=data.valuation_timestamp,
        data_status=data_status,
        data_status_reason=data_status_reason,
        total_value=valued_total,
        cash_value=data.cash_value,
        invested_value=invested,
        coverage=coverage,
        unpriced_positions=unpriced_positions,
        categories={
            "asset_class": class_slices,
            "market": market_slices,
            "sector": {
                "status": "UNAVAILABLE",
                "reason": NO_SECTOR_REASON,
                "allocation": [],
            },
            "currency": currency_slices,
            "individual_asset": individual,
            "cash": {
                "currency": data.reporting_currency,
                "value": data.cash_value,
                "weight": _weight(data.cash_value, valued_total),
            },
        },
        concentration=concentration,
    )


def allocation_for_portfolio(session: Session, portfolio_id: uuid.UUID) -> AllocationResult:
    """Load valuation + classification metadata and compute allocation (read-only)."""
    portfolio = repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise ValueError(f"portfolio {portfolio_id} not found")

    valuation = value_portfolio(session, portfolio_id)

    positions: list[PositionInput] = []
    for position in valuation.positions:
        row = asset_repo.get_asset_with_market(session, position.asset_id)
        asset, market_code = row if row is not None else (None, None)
        positions.append(
            PositionInput(
                asset_id=position.asset_id,
                symbol=position.symbol,
                name=asset.name if asset else None,
                # Taxonomy mapping is unapproved (§25); the stored classification
                # is reported verbatim instead of inventing a display name.
                asset_class=asset.asset_type if asset else None,
                market=market_code,
                currency=(asset.quote_currency or asset.base_currency) if asset else None,
                quantity=position.quantity,
                market_price=position.market_price,
                price_status=position.price_status,
                price_time=position.price_time,
                market_value=position.market_value,
                cost_basis=position.cost_basis,
            )
        )

    # Values are already in the reporting currency, so conversion is needed only
    # if a ledger entry is denominated in another currency (spec §3.3).
    conversion_required = any(
        entry.currency != valuation.reporting_currency
        for entry in repo.ledger_entries(session, portfolio_id)
    )

    return compute_allocation(
        AllocationInput(
            portfolio_id=portfolio_id,
            reporting_currency=valuation.reporting_currency,
            valuation_timestamp=valuation.valued_at,
            valuation_status=valuation.valuation_status,
            cash_value=valuation.cash_value,
            positions=positions,
            conversion_required=conversion_required,
        )
    )


__all__ = [
    "AllocationInput",
    "AllocationResult",
    "AllocationSlice",
    "IndividualAsset",
    "PositionInput",
    "allocation_for_portfolio",
    "compute_allocation",
    "serialize_weight",
]
