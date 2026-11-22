"Scanner service: executes a scanner run against stored candles and persists results."
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.data.validation.freshness import freshness_status
from app.database.models import Asset, DataProvider, ProviderInstrument, ScannerResult, ScannerRun, Market
from app.engines import scanner
from app.engines.runner import load_candles

MIN_CANDLES = 50


def run_scanner(
    session: Session,
    timeframe: str = "1h",
    markets: list[str] | None = None,
    asset_ids: list[uuid.UUID] | None = None,
) -> ScannerRun:
    """Run scanner over the universe. Synchronous, small universe.

    Universe defined by active assets with valid provider mapping and sufficient candles.
    """
    started_at = datetime.now(timezone.utc)
    run = ScannerRun(execution_mode="MANUAL", execution_status="RUNNING", started_at=started_at)
    session.add(run)
    session.flush()

    provider_code = get_settings().crypto_provider.upper()
    
    # 1. Setup Universe Query
    query = (
        session.query(Asset, ProviderInstrument, DataProvider, Market)
        .join(ProviderInstrument, Asset.id == ProviderInstrument.asset_id)
        .join(DataProvider, ProviderInstrument.provider_id == DataProvider.id)
        .outerjoin(Market, Asset.market_id == Market.id)
        .filter(
            Asset.is_active == True,
            ProviderInstrument.is_active == True,
        )
    )

    # Filter by market category
    if markets:
        query = query.filter(Market.code.in_(markets))
        
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))

    results = query.all()
    
    # Identify candidates
    all_candidates = session.query(Asset).filter(Asset.is_active == True)
    if markets:
        all_candidates = all_candidates.join(Market).filter(Market.code.in_(markets))
    if asset_ids:
        all_candidates = all_candidates.filter(Asset.id.in_(asset_ids))
    all_candidates = all_candidates.all()

    skipped_reasons = []
    processed_assets = []
    symbol_candles: dict[str, list[dict]] = {}
    data_timestamps: dict[str, datetime] = {}
    
    # Mapping for eligibility
    candidate_map = {a.id: a for a in all_candidates}
    mapped_ids = {a.id for a, pi, pd, m in results}
    
    for asset in all_candidates:
        if asset.id not in mapped_ids:
            skipped_reasons.append(
                {"symbol": asset.symbol, "reason": f"no provider mapping available"}
            )
            continue
            
        # Determine provider
        m = next((m for a, pi, pd, m in results if a.id == asset.id), None)
        is_crypto = m and m.code == "CRYPTO"
        chosen_provider_code = provider_code if is_crypto else "YAHOO"
        
        pi = next((pi for a, pi, pd, m in results if a.id == asset.id and pd.code == chosen_provider_code), None)
        if not pi:
            skipped_reasons.append(
                {"symbol": asset.symbol, "reason": f"no {chosen_provider_code} mapping found"}
            )
            continue
            
        try:
            candles = load_candles(session, asset.id, timeframe)
            if len(candles) < MIN_CANDLES:
                skipped_reasons.append(
                    {
                        "symbol": asset.symbol,
                        "reason": f"insufficient candles ({len(candles)} < {MIN_CANDLES})",
                    }
                )
                continue

            symbol_candles[asset.symbol] = candles
            data_timestamps[asset.symbol] = candles[-1]["close_time"]
            processed_assets.append(asset)
        except Exception as e:
            skipped_reasons.append({"symbol": asset.symbol, "reason": f"error loading data: {str(e)}"})

    # 3. Run instrument engines
    from app.engines.runner import run_instrument_engines

    for asset in processed_assets:
        try:
            run_instrument_engines(session, asset, timeframe)
        except Exception as e:
            skipped_reasons.append({"symbol": asset.symbol, "reason": f"engine failure: {str(e)}"})
            if asset.symbol in symbol_candles:
                del symbol_candles[asset.symbol]

    # 4. Evaluate universe
    evaluated = scanner.evaluate_universe(symbol_candles)

    for item in evaluated:
        asset = next(a for a in processed_assets if a.symbol == item["symbol"])
        data_time = data_timestamps.get(item["symbol"], started_at)
        session.add(
            ScannerResult(
                scanner_run_id=run.id,
                asset_id=asset.id,
                timeframe=timeframe,
                rank=item["rank"],
                score=item["score"],
                matched_rules=item["matched_rules"],
                metric_snapshot=item["metric_snapshot"],
                result_status="COMPLETED",
                freshness_status=freshness_status(data_time, started_at, timeframe),
                data_timestamp=data_time,
                created_at=started_at,
            )
        )

    run.universe_size = len(all_candidates)
    run.eligible_count = len(evaluated)
    run.result_count = len(evaluated)
    run.execution_status = "COMPLETED"
    run.completed_at = datetime.now(timezone.utc)
    run.execution_metadata = {
        "timeframe": timeframe,
        "markets": markets,
        "skipped": skipped_reasons,
    }
    session.commit()
    return run
