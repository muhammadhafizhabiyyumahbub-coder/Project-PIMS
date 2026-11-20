"""Portfolio-scope risk engine (Stage L).

Read-only risk metrics over stored daily candles and current holding weights.
Nothing is persisted this round (technical-decisions.md §7.11).

Methodology (owner decision §7.11):
- Daily portfolio return = SUM(weight_i * daily_return_i) over holdings priced
  at the latest stored candle. Weights are normalized over priced holdings;
  cash is excluded. Labelled current_weights_buy_and_hold_approximation — a
  buy-and-hold proxy on today's composition, not historical realized return.
- Price series: stored 1d candles; if none exist for an asset, 1h candles are
  aggregated to daily closes (last close per UTC day). price_source per asset
  is reported so the provenance is auditable.
- Returns are aligned on dates where ALL held assets have a close; missing
  observations are never substituted with zero (spec §3.3, decision §7.11#6).
- Fewer than 30 aligned daily returns -> UNAVAILABLE + reason; an asset with
  no stored candles at all -> UNAVAILABLE + reason.
- Volatility: sample stdev of daily returns. Annualized: daily * sqrt(factor),
  factor = 365 (all-crypto portfolio), 252 otherwise; mixed portfolios keep
  252 and are labelled mixed_calendar_252.
- Max drawdown from the portfolio index series V_t = prod(1 + r_t), reported as
  a negative number (spec §7.1 drawdown formula).
- Sharpe = (mean daily excess return / daily stdev) * sqrt(factor); risk-free
  rate = 0 for MVP, sent explicitly.
- Sortino = (mean daily excess return / downside deviation) * sqrt(factor);
  downside deviation = sqrt(mean of squared shortfalls vs target 0 over ALL
  observations). Null with reason when no downside observations exist.
- VaR/CVaR: empirical quantile of sorted returns at the confidence level; VaR
  is the quantile itself (negative = loss), CVaR is the mean of the tail at or
  below VaR. Quantile index: floor((1 - confidence) * n), clamped to [0, n-1].
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext

from sqlalchemy.orm import Session

from app.database.repositories import asset as asset_repo
from app.database.repositories import portfolio as repo
from app.engines.portfolio.holdings import replay_holdings
from app.engines.portfolio.performance import serialize_return

ZERO = Decimal(0)
ONE = Decimal(1)
MIN_RETURNS = 30
TARGET_RETURN = Decimal(0)  # minimum acceptable return (MVP: risk-free = 0)
PREC = 50
WINDOW_MAX_DAYS = 1095

METHOD = "current_weights_buy_and_hold_approximation"
WEIGHT_BASE = "current_holding_market_value_excl_cash"

METRIC_KEYS = [
    "volatility",
    "annualized_volatility",
    "max_drawdown",
    "sharpe",
    "sortino",
    "var_95",
    "var_99",
    "cvar_95",
    "cvar_99",
]


@dataclass
class AssetSeries:
    asset_id: object
    symbol: str
    asset_type: str
    closes: list  # oldest-first (datetime, Decimal) daily closes
    source: str  # "1d" | "1h_aggregated"


@dataclass
class HoldingInput:
    asset_id: object
    symbol: str
    asset_type: str
    quantity: Decimal
    market_price: Decimal | None
    market_value: Decimal | None
    weight: Decimal | None = None


@dataclass
class RiskResult:
    portfolio_id: object
    reporting_currency: str
    window_days: int
    observation_start: datetime | None
    observation_end: datetime | None
    return_count: int
    holdings_count: int
    method: str = METHOD
    weight_base: str = WEIGHT_BASE
    annualization: str = ""
    annualization_factor: int = 0
    risk_free_rate: Decimal = ZERO
    data_status: str = "UNAVAILABLE"
    data_status_reason: str | None = None
    metrics: dict = field(default_factory=dict)
    metric_reasons: dict = field(default_factory=dict)
    holdings: list = field(default_factory=list)
    price_source: str = ""
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ------------------------------------------------------------------ metrics


def sample_stdev(returns: list) -> Decimal | None:
    n = len(returns)
    if n < 2:
        return None
    mean = sum(returns, ZERO) / Decimal(n)
    with localcontext() as ctx:
        ctx.prec = PREC
        variance = sum((r - mean) ** 2 for r in returns) / Decimal(n - 1)
        return variance.sqrt()


def max_drawdown(values: list) -> Decimal:
    """Largest peak-to-trough fall as a negative number (spec §7.1)."""
    peak = values[0]
    worst = ZERO
    for value in values:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak if peak > ZERO else ZERO
        if drawdown < worst:
            worst = drawdown
    return worst


def empirical_var(returns: list, confidence: Decimal) -> Decimal:
    """Nearest-rank empirical quantile at (1 - confidence). Negative = loss."""
    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    idx = int((Decimal(1) - confidence) * Decimal(n))
    if idx < 0:
        idx = 0
    if idx >= n:
        idx = n - 1
    return sorted_returns[idx]


def empirical_cvar(returns: list, confidence: Decimal) -> Decimal:
    """Mean of the tail at or below the VaR quantile."""
    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    idx = int((Decimal(1) - confidence) * Decimal(n))
    if idx < 0:
        idx = 0
    if idx >= n:
        idx = n - 1
    tail = sorted_returns[: idx + 1]
    return sum(tail, ZERO) / Decimal(len(tail))


def downside_deviation(returns: list, target: Decimal) -> Decimal | None:
    """sqrt(mean of squared shortfalls vs target over ALL observations)."""
    shortfalls = [min(r - target, ZERO) for r in returns]
    if all(s == ZERO for s in shortfalls):
        return None
    with localcontext() as ctx:
        ctx.prec = PREC
        variance = sum(s * s for s in shortfalls) / Decimal(len(returns))
        return variance.sqrt()


def compute_over_series(
    weights: dict,
    series: dict,
    annualization_factor: int,
):
    """Pure metrics over the aligned portfolio return series.

    Returns (metrics, metric_reasons, return_count, observation_start, observation_end).
    """
    metrics = {}
    reasons = {}

    assets = sorted(weights)
    common_dates: set | None = None
    for asset_id in assets:
        dates = {t.date() for t, _ in series[asset_id].closes}
        common_dates = dates if common_dates is None else common_dates & dates
    ordered = sorted(common_dates)

    returns: list = []
    index_values: list = [ONE]
    close_map = {
        asset_id: {t.date(): c for t, c in series[asset_id].closes}
        for asset_id in assets
    }
    for prev_date, date in zip(ordered, ordered[1:]):
        portfolio_return = ZERO
        for asset_id in assets:
            prev = close_map[asset_id][prev_date]
            curr = close_map[asset_id][date]
            portfolio_return += weights[asset_id] * (curr / prev - ONE)
        returns.append(portfolio_return)
        index_values.append(index_values[-1] * (ONE + portfolio_return))

    daily_vol = sample_stdev(returns)
    metrics["volatility"] = daily_vol
    if daily_vol is None:
        reasons["volatility"] = (
            f"butuh minimal 2 return harian, tersedia {len(returns)}"
        )

    with localcontext() as ctx:
        ctx.prec = PREC
        factor_root = Decimal(annualization_factor).sqrt()
    metrics["annualized_volatility"] = (
        None if daily_vol is None else daily_vol * factor_root
    )
    metrics["max_drawdown"] = max_drawdown(index_values)

    mean_daily = sum(returns, ZERO) / Decimal(len(returns)) if returns else ZERO
    if daily_vol is not None and daily_vol > ZERO:
        with localcontext() as ctx:
            ctx.prec = PREC
            metrics["sharpe"] = (mean_daily / daily_vol) * factor_root
    else:
        metrics["sharpe"] = None
        reasons["sharpe"] = "daily stdev adalah nol; Sharpe tak terdefinisi"

    dd = downside_deviation(returns, TARGET_RETURN)
    if dd is not None and dd > ZERO:
        with localcontext() as ctx:
            ctx.prec = PREC
            metrics["sortino"] = (mean_daily / dd) * factor_root
    else:
        metrics["sortino"] = None
        reasons["sortino"] = (
            "tidak ada return di bawah target (0); downside deviation tak terdefinisi"
        )

    metrics["var_95"] = empirical_var(returns, Decimal("0.95"))
    metrics["var_99"] = empirical_var(returns, Decimal("0.99"))
    metrics["cvar_95"] = empirical_cvar(returns, Decimal("0.95"))
    metrics["cvar_99"] = empirical_cvar(returns, Decimal("0.99"))

    start = (
        datetime(ordered[0].year, ordered[0].month, ordered[0].day, tzinfo=UTC)
        if ordered
        else None
    )
    end = (
        datetime(ordered[-1].year, ordered[-1].month, ordered[-1].day, tzinfo=UTC)
        if ordered
        else None
    )
    return metrics, reasons, len(returns), start, end


# ---------------------------------------------------------------- orchestration


def _daily_series(session: Session, asset_id, start_at: datetime):
    """Daily closes oldest-first: stored 1d candles, else 1h aggregated to daily."""
    rows = repo.closes_in_range(session, asset_id, "1d", start_at)
    if len(rows) >= 2:
        return [(t, Decimal(str(p))) for t, p in rows], "1d"
    by_day = {}
    for t, p in repo.closes_in_range(session, asset_id, "1h", start_at):
        day = t.date()
        if day not in by_day or t > by_day[day][0]:
            by_day[day] = (t, Decimal(str(p)))
    return sorted(by_day.values()), "1h_aggregated"


def _unavailable(portfolio_id, reporting_currency, window_days, holdings_count,
                 holdings, reason, annualization="", annualization_factor=0,
                 price_source="") -> RiskResult:
    return RiskResult(
        portfolio_id=portfolio_id,
        reporting_currency=reporting_currency,
        window_days=window_days,
        observation_start=None,
        observation_end=None,
        return_count=0,
        holdings_count=holdings_count,
        annualization=annualization,
        annualization_factor=annualization_factor,
        data_status="UNAVAILABLE",
        data_status_reason=reason,
        metrics={k: None for k in METRIC_KEYS},
        holdings=holdings,
        price_source=price_source,
    )


def risk_for_portfolio(session: Session, portfolio_id, window_days: int) -> RiskResult:
    """Load holdings + daily candles, compute risk metrics. Read-only."""
    portfolio = repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise ValueError(f"portfolio {portfolio_id} not found")
    currency = portfolio.reporting_currency

    holdings_state = replay_holdings(repo.list_transactions(session, portfolio_id))
    if not holdings_state:
        return _unavailable(
            portfolio_id, currency, window_days, 0, [],
            "Portfolio tidak memiliki holding; tidak ada return yang dapat diukur.",
        )

    # Batch lookup asset details
    asset_ids = list(holdings_state.keys())
    assets = {a.id: a for a in asset_repo.get_assets(session, asset_ids)}
    latest_prices = repo.latest_close_prices(session, asset_ids)

    holding_inputs = []
    invested = ZERO
    for asset_id, state in sorted(holdings_state.items(), key=lambda item: str(item[0])):
        asset = assets.get(asset_id)
        symbol = asset.symbol if asset else str(asset_id)
        asset_type = asset.asset_type if asset else "UNKNOWN"
        latest = latest_prices.get(asset_id)
        price = Decimal(str(latest[0])) if latest else None
        market_value = state.quantity * price if price is not None else None
        holding_inputs.append(
            HoldingInput(
                asset_id=asset_id,
                symbol=symbol,
                asset_type=asset_type,
                quantity=state.quantity,
                market_price=price,
                market_value=market_value,
            )
        )
        if market_value is not None:
            invested += market_value

    if invested <= ZERO or any(h.market_price is None for h in holding_inputs):
        missing_candles = [h.symbol for h in holding_inputs if h.market_price is None]
        if missing_candles:
            # Owner decision §7.11#6: never substitute zero for a missing asset.
            return _unavailable(
                portfolio_id, currency, window_days, len(holding_inputs),
                holding_inputs,
                "Tidak tersimpan candle untuk: " + ", ".join(missing_candles)
                + "; return historis tidak dapat dibangun tanpa nol-padding.",
            )
        return _unavailable(
            portfolio_id, currency, window_days, len(holding_inputs),
            holding_inputs,
            "Tidak ada holding dengan nilai pasar tersimpan; bobot tidak dapat dibentuk.",
        )

    for h in holding_inputs:
        h.weight = h.market_value / invested

    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=window_days + 2)
    series_map = {}
    price_source = "1d"
    for h in holding_inputs:
        closes, source = _daily_series(session, h.asset_id, start_at)
        if not closes:
            return _unavailable(
                portfolio_id, currency, window_days, len(holding_inputs),
                holding_inputs,
                f"{h.symbol} tidak memiliki candle harian tersimpan dalam window; "
                "return historis tidak dapat dibangun.",
                price_source=price_source,
            )
        if source != "1d":
            price_source = "mixed_1d_1h_aggregated"
        series_map[h.asset_id] = AssetSeries(
            h.asset_id, h.symbol, h.asset_type, closes, source
        )

    priced = [h for h in holding_inputs if h.market_value is not None]
    all_crypto = all(h.asset_type == "CRYPTO" for h in priced)
    if all_crypto:
        annualization = "crypto_calendar_365"
        factor = 365
    else:
        factor = 252
        has_crypto = any(h.asset_type == "CRYPTO" for h in priced)
        has_non_crypto = any(h.asset_type != "CRYPTO" for h in priced)
        annualization = (
            "mixed_calendar_252" if has_crypto and has_non_crypto else "trading_calendar_252"
        )

    weights_map = {h.asset_id: h.weight for h in priced}
    series_priced = {h.asset_id: series_map[h.asset_id] for h in priced}
    metrics, metric_reasons, return_count, obs_start, obs_end = compute_over_series(
        weights_map, series_priced, factor
    )

    if return_count < MIN_RETURNS:
        return _unavailable(
            portfolio_id, currency, window_days, len(holding_inputs),
            holding_inputs,
            f"Hanya {return_count} return harian tersusun dalam window "
            f"{window_days} hari; minimal {MIN_RETURNS} diperlukan.",
            annualization=annualization,
            annualization_factor=factor,
            price_source=price_source,
        )

    return RiskResult(
        portfolio_id=portfolio_id,
        reporting_currency=currency,
        window_days=window_days,
        observation_start=obs_start,
        observation_end=obs_end,
        return_count=return_count,
        holdings_count=len(holding_inputs),
        annualization=annualization,
        annualization_factor=factor,
        data_status="AVAILABLE",
        metrics=metrics,
        metric_reasons=metric_reasons,
        holdings=holding_inputs,
        price_source=price_source,
    )
