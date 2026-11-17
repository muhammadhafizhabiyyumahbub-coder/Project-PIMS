"API response envelope standard per api-spec.md."
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, meta: dict | None = None, status_code: int = 200) -> JSONResponse:
    payload = {
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), **(meta or {})},
    }
    return JSONResponse(content=payload, status_code=status_code)


def error_response(
    code: str, message: str, status_code: int = 400, details: list | None = None
) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    return JSONResponse(content=payload, status_code=status_code)
