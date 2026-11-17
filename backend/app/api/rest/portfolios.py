"""Portfolio REST endpoints per api-spec §8 and §10 (holdings).

Route handlers only validate input and orchestrate Stage A engines/repositories;
no financial computation happens here (AGENTS.md §7.1).
"""
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.repositories import portfolio as repo
from app.engines.portfolio.service import write_snapshot
from app.engines.portfolio.valuation import value_portfolio
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, serialize_money

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _portfolio_payload(portfolio) -> dict:
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        # Public contract name per api-spec §8.2; column is reporting_currency.
        "base_currency": portfolio.reporting_currency,
        "status": portfolio.status,
        "created_at": portfolio.created_at.isoformat(),
        "updated_at": portfolio.updated_at.isoformat(),
    }


def _position_payload(position, currency: str, valued_at) -> dict:
    return {
        "asset_id": str(position.asset_id),
        "symbol": position.symbol,
        "quantity": serialize_money(position.quantity),
        "average_cost": serialize_money(position.average_cost),
        "cost_basis": serialize_money(position.cost_basis),
        "market_price": serialize_money(position.market_price),
        "market_value": serialize_money(position.market_value),
        "unrealized_pnl": serialize_money(position.unrealized_pnl),
        "realized_pnl": serialize_money(position.realized_pnl),
        "price_status": position.price_status,
        "price_time": position.price_time.isoformat() if position.price_time else None,
        "currency": currency,
        "valuation_timestamp": valued_at.isoformat(),
    }


@router.get("")
def list_portfolios(limit: int = 50, db: Session = Depends(get_db)):
    if limit < 1 or limit > 200:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 200", 422)
    portfolios = repo.list_portfolios(db)
    page = portfolios[:limit]
    return success_response(
        [_portfolio_payload(p) for p in page],
        meta={"count": len(page), "total": len(portfolios)},
    )


@router.post("", status_code=201)
def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)):
    portfolio = repo.create_portfolio(
        db,
        name=body.name,
        reporting_currency=body.base_currency,
        description=body.description,
    )
    db.commit()
    return success_response(_portfolio_payload(portfolio), status_code=201)


@router.get("/{portfolio_id}")
def get_portfolio_detail(portfolio_id: str, db: Session = Depends(get_db)):
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    portfolio = repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    return success_response(_portfolio_payload(portfolio))


@router.patch("/{portfolio_id}")
def update_portfolio(portfolio_id: str, body: PortfolioUpdate, db: Session = Depends(get_db)):
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    portfolio = repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    repo.update_portfolio(
        db,
        portfolio,
        name=body.name,
        description=body.description,
        status=body.status,
    )
    db.commit()
    return success_response(_portfolio_payload(portfolio))


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    portfolio = repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    # Domain policy (proposed): financial history must not be lost silently
    # (api-spec §8.4, schema-spec §14); archive instead.
    if repo.has_transactions(db, pid):
        return error_response(
            "CONFLICT",
            "portfolio has transaction history and cannot be deleted; archive it via PATCH status=ARCHIVED",
            409,
        )
    repo.delete_portfolio(db, portfolio)
    db.commit()
    return success_response({"deleted": True, "id": str(pid)})


@router.get("/{portfolio_id}/holdings")
def list_holdings(portfolio_id: str, db: Session = Depends(get_db)):
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    valuation = value_portfolio(db, pid)
    return success_response(
        [_position_payload(p, valuation.reporting_currency, valuation.valued_at) for p in valuation.positions],
        meta={"valuation_status": valuation.valuation_status},
    )


@router.get("/{portfolio_id}/holdings/{asset_id}")
def get_holding(portfolio_id: str, asset_id: str, db: Session = Depends(get_db)):
    pid = parse_uuid(portfolio_id)
    aid = parse_uuid(asset_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    if aid is None:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)
    valuation = value_portfolio(db, pid)
    position = next((p for p in valuation.positions if p.asset_id == aid), None)
    if position is None:
        return error_response("NOT_FOUND", f"holding for asset {asset_id} not found", 404)
    return success_response(_position_payload(position, valuation.reporting_currency, valuation.valued_at))


@router.get("/{portfolio_id}/valuation")
def get_valuation(portfolio_id: str, db: Session = Depends(get_db)):
    """Valuation endpoint (api-spec gap): shape follows portfolio-engine-spec §8
    status model and api-spec §5.3 money-as-string. PROPOSED contract — see
    technical-decisions pending list."""
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    valuation = value_portfolio(db, pid)
    return success_response(
        {
            "portfolio_id": str(valuation.portfolio_id),
            "valuation_status": valuation.valuation_status,
            "reporting_currency": valuation.reporting_currency,
            "cash_value": serialize_money(valuation.cash_value),
            "invested_value": serialize_money(valuation.invested_value),
            "total_value": serialize_money(valuation.total_value),
            "realized_pnl": serialize_money(valuation.realized_pnl),
            "unrealized_pnl": serialize_money(valuation.unrealized_pnl),
            "valued_at": valuation.valued_at.isoformat(),
            "positions": [
                {
                    "asset_id": str(p.asset_id),
                    "symbol": p.symbol,
                    "quantity": serialize_money(p.quantity),
                    "average_cost": serialize_money(p.average_cost),
                    "cost_basis": serialize_money(p.cost_basis),
                    "market_price": serialize_money(p.market_price),
                    "market_value": serialize_money(p.market_value),
                    "price_status": p.price_status,
                    "unrealized_pnl": serialize_money(p.unrealized_pnl),
                }
                for p in valuation.positions
            ],
        }
    )


def _snapshot_payload(snapshot) -> dict:
    metadata = snapshot.snapshot_metadata or {}
    return {
        "id": str(snapshot.id),
        "portfolio_id": str(snapshot.portfolio_id),
        "snapshot_at": snapshot.snapshot_at.isoformat(),
        "total_value": serialize_money(snapshot.total_value),
        "cash_value": serialize_money(snapshot.cash_value),
        "invested_value": serialize_money(snapshot.invested_value),
        "reporting_currency": snapshot.reporting_currency,
        "valuation_status": snapshot.valuation_status,
        "status_reason": metadata.get("status_reason"),
        "realized_pnl": metadata.get("realized_pnl"),
        "unrealized_pnl": metadata.get("unrealized_pnl"),
        "positions": metadata.get("positions", []),
        "created_at": snapshot.created_at.isoformat(),
    }


@router.post("/{portfolio_id}/snapshots", status_code=201)
def create_snapshot(
    portfolio_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Manual snapshot (owner decision §7.9). Scheduled snapshots are deferred.

    Values the valuation cannot produce are stored NULL, never estimated.
    """
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    valuation = value_portfolio(db, pid)
    snapshot_id, created = write_snapshot(db, pid, valuation, idempotency_key)
    snapshot = repo.get_snapshot(db, snapshot_id)
    return success_response(
        {**_snapshot_payload(snapshot), "idempotent_replay": not created},
        status_code=201 if created else 200,
    )


@router.get("/{portfolio_id}/snapshots")
def list_snapshots(
    portfolio_id: str,
    limit: int = 50,
    cursor: str | None = None,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 200", 422)
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    cursor_snapshot = None
    if cursor:
        cursor_id = parse_uuid(cursor)
        if cursor_id is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
        cursor_snapshot = repo.get_snapshot(db, cursor_id)
        if cursor_snapshot is None or cursor_snapshot.portfolio_id != pid:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
    rows, has_more = repo.list_snapshots_page(db, pid, limit=limit, cursor_snapshot=cursor_snapshot)
    return success_response(
        [_snapshot_payload(s) for s in rows],
        meta={
            "count": len(rows),
            "pagination": {
                "limit": limit,
                "next_cursor": str(rows[-1].id) if has_more and rows else None,
                "has_more": has_more,
            },
        },
    )
