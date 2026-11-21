import argparse
import json
from httpx import HTTPStatusError
from app.core.db import get_session_factory
from app.data.ingestion.ingest import refresh_asset_candles, resolve_provider
from app.database.models import Asset, ProviderInstrument

def ingest_candles(timeframe: str = "1h", limit: int = 300) -> dict:
    session_factory = get_session_factory()
    skipped_reasons = []
    failed = []
    written = 0
    skipped_count = 0

    with session_factory() as session:
        provider, adapter = resolve_provider(session)
        
        all_active_crypto = session.query(Asset).filter_by(is_active=True, asset_type="CRYPTO").all()
        # Filter for those with mappings
        mapping_query = session.query(ProviderInstrument).filter_by(provider_id=provider.id, is_active=True)
        mappings = {m.asset_id: m for m in mapping_query.all()}
        
        for asset in all_active_crypto:
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
        "requested": len(all_active_crypto),
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
    args = parser.parse_args()
    print(json.dumps(ingest_candles(args.timeframe, args.limit)))
