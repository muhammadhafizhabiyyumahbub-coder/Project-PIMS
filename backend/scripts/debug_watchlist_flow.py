"Temp debug: replicate watchlist add-item flow over TestClient (not committed)."
import json

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        assets = client.get("/api/v1/assets", params={"query": "BTC"}).json()
        print("assets:", json.dumps(assets)[:400])
        if not assets.get("data"):
            print("NO ASSETS")
            return
        asset_id = assets["data"][0]["id"]
        wl = client.post("/api/v1/watchlists", json={"name": "dbg", "description": None})
        print("create:", wl.status_code, json.dumps(wl.json())[:300])
        wid = wl.json()["data"]["id"]
        add = client.post(
            f"/api/v1/watchlists/{wid}/items", json={"asset_id": asset_id}
        )
        print("add:", add.status_code, json.dumps(add.json())[:400])
        detail = client.get(f"/api/v1/watchlists/{wid}")
        print("detail:", detail.status_code, json.dumps(detail.json())[:400])
        rm = client.delete(f"/api/v1/watchlists/{wid}/items/{asset_id}")
        print("remove:", rm.status_code, json.dumps(rm.json())[:300])


if __name__ == "__main__":
    main()
