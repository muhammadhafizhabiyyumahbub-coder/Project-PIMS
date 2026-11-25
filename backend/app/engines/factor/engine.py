"""Factor Engine — M4, Phase 1 (market-based factors, deterministic).

Implements the approved Phase-1 methodology from
`docs/management/m4-gap-proposals/02-factor.md`:

- Factors (market-based, all computed from stored CLOSED candles):
  MOMENTUM (N-period return minus a short skip gap), REVERSAL (inverse
  short-term return), VOLATILITY (std of returns), SIZE (log quote
  volume as a liquidity proxy — PIMS has no market-cap data, flagged).
- Normalization: z-score across the factor universe per rebalance date
  (owner default). Equal-weight composite.
- Missing-data policy: an asset with fewer than `min_candles` CLOSED
  candles is excluded from the universe (flagged, not imputed).
- Fundamental-based factors are OUT OF SCOPE (owner deferred the
  Fundamental Data Provider); this engine must not invent them.

No network: reads stored candles only.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import AnalyticsRun, FactorResult
from app.engines.runner import load_candles

CALC_VERSION = "factor.phase1.v1"

# owner-approved baseline lookbacks (proposal 02 §14, defaults)
MOMENTUM_LOOKBACK = 120
MOMENTUM_GAP = 20
REVERSAL_PERIOD = 5
VOLATILITY_LOOKBACK = 20
MIN_CANDLES = 30


@dataclass
class FactorConfig:
    """Tunable lookback/normalization parameters (all owner-proposed)."""
    factors: list[str] = field(
        default_factory=lambda: ["MOMENTUM", "VOLATILITY", "REVERSAL", "SIZE"]
    )
    momentum_lookback: int = MOMENTUM_LOOKBACK
    momentum_gap: int = MOMENTUM_GAP
    reversal_period: int = REVERSAL_PERIOD
    volatility_lookback: int = VOLATILITY_LOOKBACK
    normalization: str = "ZSCORE"  # ZSCORE | RANK
    weighting: str = "EQUAL"  # EQUAL | INVERSE_VAR


def _returns(closes: list[float]) -> list[Optional[float]]:
    out: list[Optional[float]] = [None]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        out.append((closes[i] - prev) / prev if prev else 0.0)
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def compute_momentum(closes: list[float], lookback: int, gap: int) -> Optional[float]:
    """N-period return skipping the last `gap` periods (avoids short-term
    reversal contamination of the momentum signal). Returns None if not
    enough history."""
    n = lookback
    if len(closes) < n + gap + 1:
        # fall back to available window but keep the gap semantics
        if len(closes) < 2:
            return None
        end = len(closes) - gap - 1 if len(closes) > gap + 1 else len(closes) - 1
        start = max(0, end - n)
    else:
        end = len(closes) - gap - 1
        start = max(0, end - n)
    if start >= end:
        return None
    base = closes[start]
    target = closes[end]
    return (target - base) / base if base else None


def compute_reversal(closes: list[float], period: int) -> Optional[float]:
    """Negative short-term return (reversal signal)."""
    if len(closes) < period + 1:
        return None
    base = closes[-(period + 1)]
    target = closes[-1]
    if not base:
        return None
    return -((target - base) / base)


def compute_volatility(closes: list[float], lookback: int) -> Optional[float]:
    """Std of period returns over the trailing window."""
    window = closes[-(lookback + 1):] if len(closes) >= lookback + 1 else closes
    rets = _returns(window)[1:]
    rets = [r for r in rets if r is not None]
    if len(rets) < 2:
        return None
    return _std(rets)


def compute_size(closes: list[float], last_quote_volume: float) -> Optional[float]:
    """Log of the most recent quote volume — a liquidity proxy, NOT
    market-cap (PIMS has no market-cap data). Flagged as a limitation."""
    if not last_quote_volume or last_quote_volume <= 0:
        return None
    return math.log(last_quote_volume)


def compute_raw_factors(
    closes: list[float],
    last_quote_volume: float,
    cfg: FactorConfig,
) -> dict[str, Optional[float]]:
    """Compute the configured raw factor values for one asset."""
    raw: dict[str, Optional[float]] = {}
    for f in cfg.factors:
        if f == "MOMENTUM":
            raw[f] = compute_momentum(closes, cfg.momentum_lookback, cfg.momentum_gap)
        elif f == "REVERSAL":
            raw[f] = compute_reversal(closes, cfg.reversal_period)
        elif f == "VOLATILITY":
            raw[f] = compute_volatility(closes, cfg.volatility_lookback)
        elif f == "SIZE":
            raw[f] = compute_size(closes, last_quote_volume)
        else:
            raise ValueError(f"unknown factor {f!r}")
    return raw


def normalize(
    raw_matrix: dict[str, dict[str, Optional[float]]],
    factor: str,
    method: str = "ZSCORE",
) -> dict[str, Optional[float]]:
    """Cross-sectional normalization of one factor across the universe.

    ZSCORE: (x - mean) / std. RANK: rank percentile in [0, 1].
    Assets missing the factor keep None.
    """
    values = {
        sym: raw_matrix[sym].get(factor)
        for sym in raw_matrix
        if raw_matrix[sym].get(factor) is not None
    }
    if not values:
        return {sym: None for sym in raw_matrix}
    # `values` holds only non-None factor values (filtered above); the dict is
    # typed Optional for call-site convenience but is non-None here.
    present = {sym: v for sym, v in values.items() if v is not None}
    if method == "RANK":
        ordered = sorted(present.items(), key=lambda kv: kv[1])
        ranks = {sym: i / max(len(ordered) - 1, 1) for i, (sym, _) in enumerate(ordered)}
        return {sym: ranks.get(sym) for sym in raw_matrix}
    # ZSCORE (default)
    xs = list(present.values())
    m = _mean(xs)
    sd = _std(xs)
    if sd == 0:
        return {sym: 0.0 for sym in raw_matrix}
    return {
        sym: (present[sym] - m) / sd if sym in present else None
        for sym in raw_matrix
    }


def composite(
    z_matrix: dict[str, dict[str, Optional[float]]],
    factors: list[str],
    weights: Optional[dict[str, float]] = None,
) -> dict[str, Optional[float]]:
    """Equal-weight (default) composite across available factors per asset.
    Missing factor values are dropped and the weight renormalized."""
    w = {f: (weights or {}).get(f, 1.0 / len(factors)) for f in factors}
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


def build_universe_series(
    session: Session,
    asset_ids: list,
    timeframe: str,
    limit: int,
    symbol_map: Optional[dict] = None,
) -> dict[str, dict]:
    """Load CLOSED candles per asset -> {asset_key: {symbol, closes, ...}}.

    `symbol_map` maps asset id (str/UUID) -> display symbol so the response
    is keyed by the asset's symbol (not its UUID). Assets with < MIN_CANDLES
    are flagged excluded (missing-data policy).
    """
    out: dict[str, dict] = {}
    smap = symbol_map or {}
    for aid in asset_ids:
        candles = load_candles(session, aid, timeframe, limit=limit)
        # look-ahead guard: CLOSED only
        closed = [c for c in candles if c.get("status") != "UNCLOSED"]
        if not closed:
            continue
        symbol = smap.get(str(aid)) or smap.get(aid) or str(aid)
        closes = [float(c["close"]) for c in closed]
        last_qv = float(closed[-1].get("quote_volume") or 0.0)
        out[str(aid)] = {
            "symbol": symbol,
            "closes": closes,
            "quote_volume": last_qv,
            "excluded": len(closes) < MIN_CANDLES,
            "candle_count": len(closes),
        }
    return out


def run_factor_for_universe(
    session: Session,
    asset_ids: list,
    cfg: Optional[FactorConfig] = None,
    timeframe: str = "1d",
    limit: int = 300,
    symbol_map: Optional[dict] = None,
) -> dict:
    """Compute market-based factor scores for the universe and persist to
    analytics_runs (FACTOR) + factor_results. Deterministic, no network.

    `symbol_map` (asset id -> symbol) keys the response by symbol; when
    omitted the asset id is used.
    """
    cfg = cfg or FactorConfig()
    series = build_universe_series(session, asset_ids, timeframe, limit,
                                   symbol_map=symbol_map)
    if not series:
        raise ValueError("universe has no assets with candles")

    # raw factor values per asset
    raw: dict[str, dict[str, Optional[float]]] = {}
    for key, s in series.items():
        if s["excluded"]:
            raw[key] = {f: None for f in cfg.factors}
            continue
        raw[key] = compute_raw_factors(s["closes"], s["quote_volume"], cfg)

    # z per factor
    z: dict[str, dict[str, Optional[float]]] = {}
    for f in cfg.factors:
        zf = normalize(raw, f, cfg.normalization)
        for sym in raw:
            z.setdefault(sym, {})[f] = zf[sym]

    # composite
    # EQUAL weighting uses the default (1/K) inside `composite`; any other
    # mode would pass explicit weights (Phase 2). Phase 1 is EQUAL only.
    scores = composite(z, cfg.factors, None)

    # persist
    now = datetime.now(timezone.utc)
    obs_closes = [s["closes"] for s in series.values() if s["closes"]]
    run = AnalyticsRun(
        engine_type="FACTOR",
        asset_id=None,
        timeframe=timeframe,
        observation_start=None,
        observation_end=now,
        calculation_version=CALC_VERSION,
        input_metadata={
            "factors": cfg.factors,
            "normalization": cfg.normalization,
            "weighting": cfg.weighting,
            "universe_size": len(series),
            "excluded": [
                s["symbol"] for s in series.values() if s["excluded"]
            ],
        },
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
    )
    session.add(run)
    session.flush()

    included = 0
    for key, s in series.items():
        zmap = z.get(key, {})
        session.add(FactorResult(
            analytics_run_id=run.id,
            asset_id=key,
            symbol=s["symbol"],
            raw_factors=raw.get(key, {}),
            z_factors=zmap,
            composite_score=scores.get(key),
            excluded=bool(s["excluded"]),
            result_metadata={
                "candle_count": s["candle_count"],
                "quote_volume": s["quote_volume"],
            },
        ))
        if not s["excluded"]:
            included += 1
    session.flush()

    return {
        "run_id": str(run.id),
        "calculation_status": "COMPLETED",
        "strategy": "FACTOR",
        "factors": cfg.factors,
        "normalization": cfg.normalization,
        "weighting": cfg.weighting,
        "universe_size": len(series),
        "assets_included": included,
        "excluded_assets": [s["symbol"] for s in series.values() if s["excluded"]],
        "calculation_version": CALC_VERSION,
        "scores": {
            s["symbol"]: {
                "raw": raw.get(key, {}),
                "z": z.get(key, {}),
                "composite": scores.get(key),
            }
            for key, s in series.items()
        },
    }
