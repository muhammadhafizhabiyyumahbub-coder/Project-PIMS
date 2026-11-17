"""Transaction REST endpoints per api-spec §9, idempotency per api-spec §22."""
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.repositories import portfolio as repo
from app.engines.portfolio.service import TransactionError, record_transaction
from app.schemas.portfolio import TransactionCreate, serialize_money

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# TransactionError codes that mean "the referenced resource does not exist".
NOT_FOUND_CODES = {"PORTFOLIO_NOT_FOUND", "ASSET_NOT_FOUND"}
# IDEMPOTENCY_CONFLICT is a client misuse of the retry mechanism, not a rule rejection.
CONFLICT_CODES = {"IDEMPOTENCY_CONFLICT"}
# Everything else is a business-rule rejection (api-spec §21.2).


def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _transaction_payload(t) -> dict:
    return {
        "id": str(t.id),
        "portfolio_id": str(t.portfolio_id),
        "asset_id": str(t.asset_id) if t.asset_id else None,
        "transaction_type": t.transaction_type,
        "quantity": serialize_money(t.quantity),
        "price": serialize_money(t.price),
        "gross_amount": serialize_money(t.gross_amount),
        "fee": serialize_money(t.fee_amount),
        "currency": t.currency,
        "executed_at": t.transaction_date.isoformat(),
        "idempotency_key": t.idempotency_key,
        "notes": t.notes,
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
def list_transactions(
    portfolio_id: str | None = None,
    transaction_type: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 200", 422)
    pid = parse_uuid(portfolio_id) if portfolio_id else None
    if portfolio_id and pid is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    if transaction_type is not None and transaction_type not in (
        "BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "FEE", "DIVIDEND", "INTEREST",
    ):
        return error_response("VALIDATION_ERROR", f"unsupported transaction_type filter {transaction_type}", 422)
    cursor_row = None
    if cursor:
        cursor_id = parse_uuid(cursor)
        if cursor_id is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
        cursor_row = repo.get_transaction(db, cursor_id)
        if cursor_row is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
    rows, has_more = repo.list_transactions_page(
        db,
        portfolio_id=pid,
        transaction_type=transaction_type,
        limit=limit,
        cursor_transaction=cursor_row,
    )
    meta = {
        "count": len(rows),
        "pagination": {
            "limit": limit,
            "next_cursor": str(rows[-1].id) if has_more and rows else None,
            "has_more": has_more,
        },
    }
    return success_response([_transaction_payload(t) for t in rows], meta=meta)


@router.post("")
def create_transaction(
    body: TransactionCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    pid = parse_uuid(body.portfolio_id)
    if pid is None:
        return error_response("NOT_FOUND", f"portfolio {body.portfolio_id} not found", 404)
    asset_id = None
    if body.asset_id is not None:
        asset_id = parse_uuid(body.asset_id)
        if asset_id is None:
            return error_response("NOT_FOUND", f"asset {body.asset_id} not found", 404)
    key = idempotency_key or None  # header wins over body per api-spec §22
    try:
        transaction, created = record_transaction(
            db,
            pid,
            body.transaction_type,
            asset_id=asset_id,
            quantity=body.quantity,
            price=body.price,
            gross_amount=body.gross_amount,
            fee_amount=body.fee if body.fee is not None else 0,
            currency=body.currency,
            transaction_date=body.executed_at,
            idempotency_key=key,
            notes=body.notes,
        )
    except TransactionError as exc:
        db.rollback()  # never leave half-written financial rows
        if exc.code in NOT_FOUND_CODES:
            return error_response("NOT_FOUND", exc.message, 404)
        if exc.code in CONFLICT_CODES:
            return error_response("CONFLICT", exc.message, 409)
        return error_response("BUSINESS_RULE_ERROR", exc.message, 422, details=[{"code": exc.code}])
    status_code = 201 if created else 200
    return success_response(
        {**_transaction_payload(transaction), "idempotent_replay": not created},
        status_code=status_code,
    )


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    tid = parse_uuid(transaction_id)
    if tid is None:
        return error_response("NOT_FOUND", f"transaction {transaction_id} not found", 404)
    transaction = repo.get_transaction(db, tid)
    if transaction is None:
        return error_response("NOT_FOUND", f"transaction {transaction_id} not found", 404)
    return success_response(_transaction_payload(transaction))
