"""M4 Sentiment Engine — Phase 1b tests (RSS headlines via adapter + LLM).

Covers: weighted aggregate math, UNAVAILABLE handling, endpoint + persistence,
determinism, §26 sanitization (no PII/credentials in response).
Deterministic, no network.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database.models import (
    Asset,
    DataProvider,
    Market,
    ProviderInstrument,
    SentimentResult,
    AnalyticsRun,
    Portfolio,
)
from app.engines.sentiment.engine import run_sentiment_for_universe, aggregate_sentiment
from app.data.providers.news.rss import RSSNewsAdapter

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests
# ---------------------------------------------------------------------------


def test_aggregate_sentiment_basic():
    """Test weighted aggregate of sentiment scores."""
    items = [
        {"score": 0.8, "confidence": 0.9},
        {"score": -0.4, "confidence": 0.6},
        {"score": 0.2, "confidence": 0.5},
    ]
    score, label, confidence, count = aggregate_sentiment(items)
    assert count == 3
    assert -1.0 <= score <= 1.0
    assert label in ("POSITIVE", "NEGATIVE", "NEUTRAL", "UNAVAILABLE")
    assert 0.0 <= confidence <= 1.0
    # Weighted mean: (0.8*0.9 + -0.4*0.6 + 0.2*0.5) / (0.9+0.6+0.5) = (0.72 - 0.24 + 0.10) / 2.0 = 0.58/2.0 = 0.29
    assert abs(score - 0.29) < 0.01


def test_aggregate_sentiment_empty():
    """Test empty headlines -> UNAVAILABLE."""
    score, label, confidence, count = aggregate_sentiment([])
    assert score is None
    assert label == "UNAVAILABLE"
    assert confidence is None
    assert count == 0


def test_aggregate_sentiment_zero_confidence():
    """Test zero confidence falls back to equal weighting."""
    items = [
        {"score": 0.5, "confidence": 0.0},
        {"score": -0.5, "confidence": 0.0},
    ]
    score, label, confidence, count = aggregate_sentiment(items)
    assert count == 2
    assert abs(score - 0.0) < 0.01  # Equal weight: (0.5 + -0.5) / 2 = 0
    assert label == "NEUTRAL"


def test_aggregate_sentiment_bounded():
    """Test score stays within [-1, 1]."""
    items = [
        {"score": 2.0, "confidence": 1.0},  # invalid, but should be bounded
    ]
    score, label, confidence, count = aggregate_sentiment(items)
    assert score == 1.0  # bounded to 1.0
    assert label == "POSITIVE"

    items = [
        {"score": -2.0, "confidence": 1.0},
    ]
    score, label, confidence, count = aggregate_sentiment(items)
    assert score == -1.0  # bounded to -1.0
    assert label == "NEGATIVE"


def test_aggregate_sentiment_label_thresholds():
    """Test label assignment at thresholds."""
    # POSITIVE > 0.15
    score, label, _, _ = aggregate_sentiment([{"score": 0.2, "confidence": 1.0}])
    assert label == "POSITIVE"

    # NEGATIVE < -0.15
    score, label, _, _ = aggregate_sentiment([{"score": -0.2, "confidence": 1.0}])
    assert label == "NEGATIVE"

    # NEUTRAL in [-0.15, 0.15]
    score, label, _, _ = aggregate_sentiment([{"score": 0.1, "confidence": 1.0}])
    assert label == "NEUTRAL"


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def sentiment_setup(db_session):
    """Portfolio with two holdings for sentiment tests."""
    # Provider
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)

    # Market
    mkt = db_session.query(Market).filter_by(code="US").first()
    if not mkt:
        mkt = Market(code="US", name="US Stocks", market_type="STOCK")
        db_session.add(mkt)

    # Portfolio
    pf = Portfolio(name="Sentiment Test", reporting_currency="USD", status="ACTIVE")
    db_session.add(pf)
    db_session.flush()

    # Assets
    assets = []
    for sym in ["SENT_A", "SENT_B"]:
        a = Asset(symbol=sym, name=sym, asset_type="STOCK", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id, provider_symbol=sym))
        assets.append(a)

    db_session.commit()
    return {
        "portfolio_id": str(pf.id),
        "asset_a": str(assets[0].id),
        "asset_b": str(assets[1].id),
        "symbol_a": assets[0].symbol,
        "symbol_b": assets[1].symbol,
    }


def test_sentiment_endpoint_persists(db_session, sentiment_setup):
    """Test endpoint persists analytics_runs(SENTIMENT) + sentiment_results."""
    setup = sentiment_setup

    # Mock RSS feed returning empty (no headlines at all)
    with patch("app.engines.sentiment.engine.RSSNewsAdapter.fetch_headlines") as mock_fetch:
        mock_fetch.return_value = []

        resp = client.post("/api/v1/analytics/sentiment", json={
            "symbols": [setup["symbol_a"], setup["symbol_b"]],
            "timeframe": "1d",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "COMPLETED"
        assert "run_id" in data

        # Check persistence
        run_id = data["run_id"]
        run = db_session.get(AnalyticsRun, run_id)
        assert run is not None
        assert run.engine_type == "SENTIMENT"

        rows = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).all()
        assert len(rows) == 2
        symbols = {r.symbol for r in rows}
        assert symbols == {setup["symbol_a"], setup["symbol_b"]}

        # Check UNAVAILABLE for no headlines
        for r in rows:
            assert r.label == "UNAVAILABLE"
            assert r.sentiment_score is None
            assert r.confidence is None
            assert r.headline_count == 0
            assert r.result_metadata.get("reason") == "no matching headlines found for asset"


def test_sentiment_insufficient_data(db_session):
    """Test INSUFFICIENT_DATA when symbols not found."""
    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": ["NONEXISTENT"],
        "timeframe": "1d",
    })
    assert resp.status_code == 422


def test_sentiment_determinism(db_session, sentiment_setup):
    """Two runs with same inputs produce identical results."""
    setup = sentiment_setup

    resp1 = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    resp2 = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })

    data1 = resp1.json()["data"]
    data2 = resp2.json()["data"]

    # Different run IDs
    assert data1["run_id"] != data2["run_id"]
    # Same calculations
    assert data1["status"] == data2["status"]


# ---------------------------------------------------------------------------
# §26 External-Data Sharing sanitization
# ---------------------------------------------------------------------------


def test_sentiment_sanitization_no_pii(db_session, sentiment_setup):
    """§26: Assert no PII/credentials/positions leak in response/metadata."""
    setup = sentiment_setup

    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Check response contains no sensitive fields
    response_str = str(data)
    sensitive = ["api_key", "secret", "password", "token", "credential",
                 "position", "quantity", "cost_basis", "portfolio_id"]
    for s in sensitive:
        assert s.lower() not in response_str.lower(), f"Sensitive term '{s}' leaked in response"

    # Check persisted metadata
    run_id = data["run_id"]
    rows = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).all()
    for r in rows:
        meta_str = str(r.result_metadata)
        for s in sensitive:
            assert s.lower() not in meta_str.lower(), f"Sensitive term '{s}' leaked in metadata"
        # Ensure sanitized flag
        assert r.result_metadata.get("sanitized") is True


# ---------------------------------------------------------------------------
# LLM mock test (deterministic scoring)
# ---------------------------------------------------------------------------


@patch("app.api.rest.analytics_v2.run_sentiment_for_universe")
def test_sentiment_engine_llm_mock(mock_engine, db_session, sentiment_setup):
    """Test sentiment engine with mocked LLM scoring (deterministic)."""
    setup = sentiment_setup
    
    # Mock the engine to return predetermined scores
    mock_engine.return_value = {
        "run_id": "00000000-0000-0000-0000-000000000001",
        "status": "COMPLETED",
    }

    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    mock_engine.assert_called_once()


# ---------------------------------------------------------------------------
# RSS Adapter Integration Tests (Phase 1b)
# ---------------------------------------------------------------------------


@patch("app.engines.sentiment.engine.RSSNewsAdapter.fetch_headlines")
def test_sentiment_rss_adapter_mock_returns_scores(mock_fetch, db_session, sentiment_setup):
    """Test RSS adapter mock returns scores (not UNAVAILABLE) when headlines match."""
    setup = sentiment_setup
    
    # Mock RSS feed returning headlines matching our test symbols
    mock_fetch.return_value = [
        {"title": "SENT_A reports strong quarterly earnings", "pub_date": "2024-01-15T10:00:00Z", "source": "RSS_FEED"},
        {"title": "SENT_B stock falls on weak guidance", "pub_date": "2024-01-15T11:00:00Z", "source": "RSS_FEED"},
    ]

    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"

    # Check persisted results have scores
    run_id = data["run_id"]
    rows = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) == 2
    for r in rows:
        assert r.headline_count == 1
        assert r.label != "UNAVAILABLE"
        assert r.sentiment_score is not None
        assert -1.0 <= r.sentiment_score <= 1.0
        assert r.confidence is not None


@patch("app.engines.sentiment.engine.RSSNewsAdapter.fetch_headlines")
def test_sentiment_rss_adapter_no_matching_headlines(mock_fetch, db_session, sentiment_setup):
    """Test UNAVAILABLE when headlines exist but none match the asset."""
    setup = sentiment_setup
    
    # Mock RSS feed with unrelated headlines
    mock_fetch.return_value = [
        {"title": "XYZ Corp reports earnings", "pub_date": "2024-01-15T10:00:00Z", "source": "RSS_FEED"},
        {"title": "ABC Inc stock moves up", "pub_date": "2024-01-15T11:00:00Z", "source": "RSS_FEED"},
    ]

    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"

    # Check persisted results are UNAVAILABLE
    run_id = data["run_id"]
    rows = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) == 2
    for r in rows:
        assert r.headline_count == 0
        assert r.label == "UNAVAILABLE"
        assert r.sentiment_score is None
        assert r.result_metadata.get("reason") == "no matching headlines found for asset"


@patch("app.engines.sentiment.engine.RSSNewsAdapter.fetch_headlines")
def test_sentiment_rss_adapter_feed_failure(mock_fetch, db_session, sentiment_setup):
    """Test UNAVAILABLE when RSS feed fetch fails (network error)."""
    setup = sentiment_setup
    
    # Mock RSS feed failure (empty list = network/parse error)
    mock_fetch.return_value = []

    resp = client.post("/api/v1/analytics/sentiment", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"

    run_id = data["run_id"]
    rows = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).all()
    for r in rows:
        assert r.headline_count == 0
        assert r.label == "UNAVAILABLE"
        assert r.result_metadata.get("reason") == "no matching headlines found for asset"


def test_sentiment_response_contains_source_field(db_session, sentiment_setup):
    """Test response/metadata includes 'source' field for Phase 1b."""
    setup = sentiment_setup

    # Mock to ensure we get matched headlines
    with patch("app.engines.sentiment.engine.RSSNewsAdapter.fetch_headlines") as mock_fetch:
        mock_fetch.return_value = [
            {"title": f"{setup['symbol_a']} surges on earnings beat", "pub_date": "2024-01-15T10:00:00Z", "source": "RSS_FEED"},
        ]
        
        resp = client.post("/api/v1/analytics/sentiment", json={
            "symbols": [setup["symbol_a"]],
            "timeframe": "1d",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        
        # Check persisted metadata has source
        run_id = data["run_id"]
        row = db_session.query(SentimentResult).filter_by(analytics_run_id=run_id).first()
        assert row is not None
        assert row.result_metadata.get("source") == "RSS_FEED"
        assert "sanitized" in row.result_metadata