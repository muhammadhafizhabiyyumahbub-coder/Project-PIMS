"Scanner service: executes a scanner run against stored candles and persists results."
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data.validation.freshness import freshness_status
from app.database.models import Asset, ScannerResult, ScannerRun
from app.engines import scanner
from app.engines.runner import load_candles


def run_scanner(session: Session, timeframe: str = "1h") -> ScannerRun:
    """Run scanner over the CRYPTO universe. Synchronous, small universe."""
    started_at = datetime.now(timezone.utc)
    run = ScannerRun(execution_mode="MANUAL", execution_status="RUNNING", started_at=started_at)
    session.add(run)
    session.flush()

    assets = session.query(Asset).filter_by(asset_type="CRYPTO", is_active=True).all()
    symbol_candles: dict[str, list[dict]] = {}
    data_timestamps: dict[str, datetime] = {}
    for asset in assets:
        candles = load_candles(session, asset.id, timeframe)
        symbol_candles[asset.symbol] = candles
        if candles:
            data_timestamps[asset.symbol] = candles[-1]["close_time"]

    # Analysis pipeline: instrument engines run before screening so qualification
    # has traceable engine results for every evaluated instrument.
    from app.engines.runner import run_instrument_engines

    for asset in assets:
        run_instrument_engines(session, asset, timeframe)

    evaluated = scanner.evaluate_universe(symbol_candles)
    for item in evaluated:
        asset = next(a for a in assets if a.symbol == item["symbol"])
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

    run.universe_size = len(assets)
    run.eligible_count = len(evaluated)
    run.result_count = len(evaluated)
    run.execution_status = "COMPLETED"
    run.completed_at = datetime.now(timezone.utc)
    run.execution_metadata = {"timeframe": timeframe, "universe": [a.symbol for a in assets]}
    session.commit()
    return run
