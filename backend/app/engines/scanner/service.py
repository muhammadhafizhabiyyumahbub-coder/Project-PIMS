"Scanner service: executes a scanner run against stored candles and persists results."
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.data.validation.freshness import freshness_status
from app.database.models import Asset, DataProvider, ProviderInstrument, ScannerResult, ScannerRun
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
    provider = session.query(DataProvider).filter_by(code=provider_code).first()
    if not provider:
        run.execution_status = "FAILED"
        run.error_message = f"Provider {provider_code} not found in database."
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        return run

    # 1. Define universe based on mappings
    query = (
        session.query(Asset, ProviderInstrument)
        .join(ProviderInstrument, Asset.id == ProviderInstrument.asset_id)
        .filter(
            Asset.is_active == True,
            ProviderInstrument.provider_id == provider.id,
            ProviderInstrument.is_active == True,
        )
    )
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))

    results = query.all()
    all_active = session.query(Asset).filter_by(is_active=True)
    if asset_ids:
        all_active = all_active.filter(Asset.id.in_(asset_ids))
    all_active = all_active.all()

    skipped_reasons = []
    processed_assets = []
    symbol_candles: dict[str, list[dict]] = {}
    data_timestamps: dict[str, datetime] = {}

    # Identify assets without mapping
    mapped_ids = {a.id for a, pi in results}
    for asset in all_active:
        if asset.id not in mapped_ids:
            skipped_reasons.append(
                {"symbol": asset.symbol, "reason": f"no active mapping for {provider_code}"}
            )

    # 2. Check candles for mapped assets
    for asset, pi in results:
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

    # 3. Run instrument engines for eligible assets
    from app.engines.runner import run_instrument_engines

    for asset in processed_assets:
        try:
            run_instrument_engines(session, asset, timeframe)
        except Exception as e:
            # Engine failure for one asset shouldn't crash the whole run
            skipped_reasons.append({"symbol": asset.symbol, "reason": f"engine failure: {str(e)}"})
            if asset.symbol in symbol_candles:
                del symbol_candles[asset.symbol]

    # 4. Evaluate universe
    evaluated = []
    if symbol_candles:
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

    run.universe_size = len(all_active)
    run.eligible_count = len(evaluated)
    run.result_count = len(evaluated)
    run.execution_status = "COMPLETED"
    run.completed_at = datetime.now(timezone.utc)
    run.execution_metadata = {
        "timeframe": timeframe,
        "provider": provider_code,
        "skipped": skipped_reasons,
    }
    session.commit()
    return run
