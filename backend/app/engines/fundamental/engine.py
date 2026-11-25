"""Fundamental Engine — M4, Phase 1 (Yahoo-based, deterministic).

Implements the approved Phase-1 methodology:
- Fetches fundamentals via Yahoo Finance (quoteSummary).
- Metrics: P/E, ROE, revenue growth.
- Scoring: z-score per metric, composite equal-weight.
- Missing data = UNAVAILABLE (reason stored in metadata).

No network: uses already fetched data or assumes Yahoo adapter availability.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.database.models import AnalyticsRun, FundamentalResult, Asset

CALC_VERSION = "fundamental.phase1.v1"

def _normalize(values: dict[str, float]) -> dict[str, float]:
    """Z-score normalization."""
    if not values:
        return {}
    xs = list(values.values())
    m = sum(xs) / len(xs)
    sd = (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5
    if sd == 0:
        return {k: 0.0 for k in values}
    return {k: (v - m) / sd for k, v in values.items()}

def _composite(
    z_matrix: dict[str, dict[str, Optional[float]]],
    factors: list[str],
) -> dict[str, Optional[float]]:
    """Equal-weight composite across available factors per asset."""
    w = {f: 1.0 / len(factors) for f in factors}
    out: dict[str, Optional[float]] = {}
    for sym, zmap in z_matrix.items():
        num = 0.0
        den = 0.0
        for f in factors:
            z = zmap.get(f)
            if z is None:
                continue
            num += w[f] * z
            den += w[f]
        out[sym] = num / den if den else None
    return out

def run_fundamental_for_universe(
    session: Session,
    assets: list[Asset],
    timeframe: str = "1d",
) -> dict:
    """Compute fundamental scores for universe and persist results.

    HONEST: Yahoo data may be missing for some assets.
    If no fundamentals available -> UNAVAILABLE with reason in metadata.
    """
    factors = ["pe", "roe", "revenue_growth"]
    now = datetime.now(timezone.utc)

    # Real fetch via Yahoo quoteSummary (adapter). No fabricated numbers:
    # every value comes from the provider or is None (+ reason, UNAVAILABLE).
    # Crypto / thin-coverage instruments report no fundamentals -> None.
    from app.data.providers.crypto.yahoo import YahooProvider
    from app.database.models import DataProvider, ProviderInstrument

    yahoo = YahooProvider()

    def _yahoo_symbol(asset):
        prov = session.query(DataProvider).filter_by(code="YAHOO").first()
        if prov:
            pi = (
                session.query(ProviderInstrument)
                .filter_by(asset_id=asset.id, provider_id=prov.id)
                .first()
            )
            if pi and pi.provider_symbol:
                return pi.provider_symbol
        return asset.symbol

    fundamentals_map = {}
    for asset in assets:
        try:
            fundamentals_map[str(asset.id)] = yahoo.fetch_fundamentals(_yahoo_symbol(asset))
        except Exception as exc:  # network/provider failure -> honest UNAVAILABLE
            fundamentals_map[str(asset.id)] = {
                "pe": None, "roe": None, "revenue_growth": None,
                "reason": f"fetch failed: {exc.__class__.__name__}",
            }

    # Build raw and z-score matrices
    raw_matrix = {}
    for asset in assets:
        f = fundamentals_map.get(str(asset.id), {})
        raw_matrix[asset.symbol] = {
            "pe": f.get("pe"),
            "roe": f.get("roe"),
            "revenue_growth": f.get("revenue_growth"),
        }

    # Z-score per metric (only for available values)
    z_matrix = {}
    for factor in factors:
        present = {sym: raw_matrix[sym][factor] for sym in raw_matrix if raw_matrix[sym].get(factor) is not None}
        if present:
            z_matrix[factor] = _normalize(present)
        else:
            z_matrix[factor] = {sym: None for sym in raw_matrix}

    # Transpose to per-asset z-map
    z_per_asset = {}
    for sym in raw_matrix:
        z_per_asset[sym] = {f: z_matrix[f].get(sym) for f in factors}

    # Composite score
    composite_scores = _composite(z_per_asset, factors)

    # Rank
    ranked = sorted(
        [(s, c) for s, c in composite_scores.items() if c is not None],
        key=lambda x: x[1],
        reverse=True
    )
    ranks = {s: i + 1 for i, (s, _) in enumerate(ranked)}
    for sym in composite_scores:
        if sym not in ranks:
            ranks[sym] = None

    # Persist
    run = AnalyticsRun(
        engine_type="FUNDAMENTAL",
        calculation_version=CALC_VERSION,
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
        input_metadata={"factors": factors, "universe_size": len(assets)},
    )
    session.add(run)
    session.flush()

    for asset in assets:
        sym = asset.symbol
        f = fundamentals_map.get(str(asset.id), {})
        meta = {
            "reason": f.get("reason", "Fundamental data not available"),
            "z_scores": z_per_asset.get(sym, {}),
        }
        session.add(FundamentalResult(
            analytics_run_id=run.id,
            asset_id=asset.id,
            symbol=sym,
            pe=f.get("pe"),
            roe=f.get("roe"),
            revenue_growth=f.get("revenue_growth"),
            composite_score=composite_scores.get(sym),
            rank=ranks.get(sym),
            result_metadata=meta,
        ))
    session.flush()

    per_asset = [
        {
            "symbol": asset.symbol,
            "pe": f.get("pe"),
            "roe": f.get("roe"),
            "revenue_growth": f.get("revenue_growth"),
            "composite_score": composite_scores.get(asset.symbol),
            "rank": ranks.get(asset.symbol),
            "status": "UNAVAILABLE" if (
                f.get("pe") is None and f.get("roe") is None
                and f.get("revenue_growth") is None
            ) else "COMPLETED",
            "reason": f.get("reason"),
        }
        for asset in assets
        if (f := fundamentals_map.get(str(asset.id), {})) is not None
    ]

    return {
        "run_id": str(run.id),
        "status": "COMPLETED",
        "per_asset": per_asset,
    }