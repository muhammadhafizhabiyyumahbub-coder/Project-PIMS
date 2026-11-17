"Health and readiness endpoints."
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.envelope import success_response
from app.core.db import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return success_response({"status": "ok"})


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return success_response({"status": "ready", "database": "connected"})
