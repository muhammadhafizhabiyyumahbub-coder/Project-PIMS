"""Valuation engine: cash + holdings valued at the latest stored candle close.

Prices come only from market_candles (Stage A rule: no new provider fetch).
Missing prices are never substituted with zero or invented values
(portfolio-engine-spec §8.4).
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.repositories import asset as asset_repo
from app.database.repositories import portfolio as repo
from app.engines.portfolio.holdings import quantize, replay_holdings

PRICE_FRESHNESS_SECONDS = 7200  # 2 closed 1h candles; marks STALE per §8.5.


@dataclass
class PositionValuation:
    asset_id: uuid.UUID
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    market_price: Decimal | None
    market_value: Decimal | None
    price_time: datetime | None
    price_status: str  # AVAILABLE | MISSING | STALE
    unrealized_pnl: Decimal | None


@dataclass
class ValuationResult:
    portfolio_id: uuid.UUID
    reporting_currency: str
    valuation_status: str  # COMPLETE | PARTIAL | STALE | UNAVAILABLE (spec §8.5)
    cash_value: Decimal
    invested_value: Decimal | None
    total_value: Decimal | None
    realized_pnl: Decimal
    unrealized_pnl: Decimal | None
    valued_at: datetime
    positions: list[PositionValuation] = field(default_factory=list)


def value_portfolio(
    session: Session,
    portfolio_id: uuid.UUID,
    priced_at: datetime | None = None,
) -> ValuationResult:
    portfolio = repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise ValueError(f"portfolio {portfolio_id} not found")
    currency = portfolio.reporting_currency
    priced_at = priced_at or datetime.now(timezone.utc)

    cash = quantize(Decimal(str(repo.cash_balance(session, portfolio_id, currency))))
    transactions = repo.list_transactions(session, portfolio_id)
    holdings = replay_holdings(transactions)

    positions: list[PositionValuation] = []
    missing = False
    stale = False
    invested = Decimal("0")
    realized_total = Decimal("0")
    unrealized_total = Decimal("0")

    # Batch lookup asset details and prices
    asset_ids = list(holdings.keys())
    assets = {a.id: a for a in asset_repo.get_assets(session, asset_ids)}
    latest_prices = repo.latest_close_prices(session, asset_ids)

    for asset_id, state in sorted(holdings.items(), key=lambda item: str(item[0])):
        asset = assets.get(asset_id)
        symbol = asset.symbol if asset else str(asset_id)
        realized_total += state.realized_pnl
        latest = latest_prices.get(asset_id)
        price: Decimal | None = None
        price_time: datetime | None = None
        price_status = "MISSING"
        market_value: Decimal | None = None
        unrealized: Decimal | None = None
        if latest is not None:
            price_raw, price_time = latest
            price = Decimal(str(price_raw))
            age = priced_at - price_time
            if age.total_seconds() <= PRICE_FRESHNESS_SECONDS:
                price_status = "AVAILABLE"
                market_value = state.quantity * price
                unrealized = market_value - state.cost_basis
                invested += market_value
                unrealized_total += unrealized
            else:
                price_status = "STALE"
                stale = True
        else:
            missing = True
        positions.append(
            PositionValuation(
                asset_id=asset_id,
                symbol=symbol,
                quantity=state.quantity,
                average_cost=state.average_cost,
                cost_basis=state.cost_basis,
                realized_pnl=state.realized_pnl,
                market_price=price,
                market_value=market_value,
                price_time=price_time,
                price_status=price_status,
                unrealized_pnl=unrealized,
            )
        )

    if not transactions and not holdings:
        status = "UNAVAILABLE"
    elif missing:
        status = "PARTIAL"
    elif stale:
        status = "STALE"
    else:
        status = "COMPLETE"

    has_valued_positions = any(p.market_value is not None for p in positions)
    # No positions at all: invested 0 is a true zero (nothing held), not a
    # placeholder — api-spec §4.3 forbids only substituting UNAVAILABLE data.
    if not positions:
        invested_q: Decimal | None = Decimal("0")
    else:
        invested_q = quantize(invested) if has_valued_positions else None
    # invested_value sums only AVAILABLE positions; totals are reported only
    # when the valuation is COMPLETE (partial/stale sums must not look final).
    return ValuationResult(
        portfolio_id=portfolio_id,
        reporting_currency=currency,
        valuation_status=status,
        cash_value=cash,
        invested_value=invested_q,
        total_value=(cash + invested_q) if status == "COMPLETE" else None,
        realized_pnl=quantize(realized_total),
        unrealized_pnl=quantize(unrealized_total) if status == "COMPLETE" else None,
        valued_at=priced_at,
        positions=positions,
    )
