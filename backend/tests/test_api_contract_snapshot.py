import pytest
import re
from fastapi.openapi.utils import get_openapi
from app.main import app

def normalize_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)

def test_normalize_path():
    assert normalize_path("/api/v1/x/{id}") == "/api/v1/x/{}"
    assert normalize_path("/api/v1/x/{config_id}") == "/api/v1/x/{}"
    assert normalize_path("/api/v1/x/{transaction_id}") == "/api/v1/x/{}"
    assert normalize_path("/api/v1/x/{report_id}") == "/api/v1/x/{}"
    assert normalize_path("/api/v1/x/{asset_id}") == "/api/v1/x/{}"
    # Different paths remain different
    assert normalize_path("/api/v1/x/{id}") != "/api/v1/y/{}"
    assert normalize_path("/api/v1/x/{id}") != "/api/v1/x/{}/extra"

def test_api_contract_snapshot():
    # Get endpoints from openapi (excludes docs/redoc/internal)
    openapi = get_openapi(title=app.title, version=app.version, routes=app.routes)
    
    current_endpoints = []
    paths = openapi.get("paths", {})
    for path, methods in paths.items():
        for method in methods.keys():
            current_endpoints.append((method.upper(), path))
    
    current_endpoints = sorted(current_endpoints)
    
    # Hardcoded snapshot of currently implemented API endpoints
    # Derived from the actual implementation (see audit script output)
    known_endpoints = sorted([
        ("DELETE", "/api/v1/portfolios/{portfolio_id}"),
        ("DELETE", "/api/v1/research/{report_id}"),
        ("DELETE", "/api/v1/scanner/configurations/{config_id}"),
        ("GET", "/api/v1/assets"),
        ("GET", "/api/v1/assets/search"),
        ("GET", "/api/v1/assets/{asset_id}"),
        ("GET", "/api/v1/analytics/allocation"),
        ("GET", "/api/v1/analytics/correlation"),
        ("GET", "/api/v1/analytics/market-regime"),
        ("GET", "/api/v1/analytics/performance"),
        ("GET", "/api/v1/analytics/risk"),
        ("GET", "/api/v1/analytics/technical"),
        ("GET", "/api/v1/dashboard/activity"),
        ("GET", "/api/v1/dashboard/instrument-opportunities"),
        ("GET", "/api/v1/dashboard/market-overview"),
        ("GET", "/api/v1/dashboard/overview"),
        ("GET", "/api/v1/dashboard/research-highlights"),
        ("GET", "/api/v1/dashboard/scanner-highlights"),
        ("GET", "/api/v1/market-data/candles"),
        ("GET", "/api/v1/market-data/instruments/{asset_id}/candles"),
        ("GET", "/api/v1/market-data/instruments/{asset_id}/quote"),
        ("GET", "/api/v1/market-data/quotes"),
        ("GET", "/api/v1/markets"),
        ("GET", "/api/v1/markets/status"),
        ("GET", "/api/v1/markets/{market_id}"),
        ("GET", "/api/v1/portfolios"),
        ("GET", "/api/v1/portfolios/{portfolio_id}"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/allocation"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/analytics/runs"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/analytics/runs/{run_id}"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/holdings"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/holdings/{asset_id}"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/performance"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/risk"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/snapshots"),
        ("GET", "/api/v1/portfolios/{portfolio_id}/valuation"),
        ("GET", "/api/v1/research"),
        ("GET", "/api/v1/research/{report_id}"),
        ("GET", "/api/v1/research/reports/{report_id}"),
        ("GET", "/api/v1/research/requests/{request_id}"),
        ("GET", "/api/v1/scanner/categories"),
        ("GET", "/api/v1/scanner/configurations"),
        ("GET", "/api/v1/scanner/results"),
        ("GET", "/api/v1/scanner/results/{result_id}/qualification"),
        ("GET", "/api/v1/scanner/runs/{run_id}"),
        ("GET", "/api/v1/transactions"),
        ("GET", "/api/v1/transactions/{transaction_id}"),
        ("GET", "/health"),
        ("GET", "/health/ready"),
        ("PATCH", "/api/v1/portfolios/{portfolio_id}"),
        ("PATCH", "/api/v1/scanner/configurations/{config_id}"),
        ("POST", "/api/v1/portfolios"),
        ("POST", "/api/v1/portfolios/{portfolio_id}/analytics/runs"),
        ("POST", "/api/v1/portfolios/{portfolio_id}/snapshots"),
        ("POST", "/api/v1/research"),
        ("POST", "/api/v1/research/requests"),
        ("POST", "/api/v1/scanner/configurations"),
        ("POST", "/api/v1/scanner/run"),
        ("POST", "/api/v1/transactions"),
    ])
    
    assert current_endpoints == known_endpoints, f"API contract mismatch: {set(current_endpoints) ^ set(known_endpoints)}"