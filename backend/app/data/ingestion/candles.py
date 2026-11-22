import argparse
import json
import logging
from datetime import datetime, timezone
from httpx import HTTPStatusError
from app.core.db import get_session_factory
from app.data.ingestion.ingest import refresh_asset_candles, resolve_provider
from app.database.models import Asset, ProviderInstrument, Market

logger = logging.getLogger(__name__)

def ingest_candles(timeframe: str = "1h", limit: int = 300, markets: str | None = None) -> dict:
    session_factory = get_session_factory()
    skipped_reasons = []
    failed = []
    written = 0
    skipped_count = 0

    with session_factory() as session:
        provider, adapter = resolve_provider(session)
        
        query = session.query(Asset).filter(Asset.is_active == True)
        # Optional markets filter
        if markets:
            market_list = [m.strip() for m in markets.split(",")]
            query = query.join(Market, Asset.market_id == Market.id).filter(Market.code.in_(market_list))
        
        all_active_assets = query.all()
        mapping_query = session.query(ProviderInstrument).filter_by(provider_id=provider.id, is_active=True)
        mappings = {m.asset_id: m for m in mapping_query.all()}
        
        for asset in all_active_assets:
            if asset.id not in mappings:
                skipped_count += 1
                skipped_reasons.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": f"no provider instrument mapping for {asset.symbol}"})
                continue
            
            try:
                written += refresh_asset_candles(session, asset, timeframe, limit)
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    skipped_count += 1
                    skipped_reasons.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": f"provider does not offer data for {mappings[asset.id].provider_symbol}"})
                else:
                    failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})
            except Exception as e:
                failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})
                
    return {
        "requested": len(all_active_assets),
        "written": written,
        "skipped": skipped_count,
        "skipped_reasons": skipped_reasons,
        "failed": failed,
        "provider": provider.code,
        "timeframe": timeframe,
        "is_realtime": False
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--markets", help="Comma-separated market codes (e.g. CRYPTO,US,IDX)")
    args = parser.parse_args()
    print(json.dumps(ingest_candles(args.timeframe, args.limit, args.markets)))
