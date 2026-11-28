"API response envelope standard per api-spec.md."
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse

_logger = logging.getLogger(__name__)


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


def server_error(exc: Exception) -> JSONResponse:
    """Log exception detail server-side; return a generic 500 to the client.

    Keeps str(exc) (DSN, SQL, paths) out of the response body (QA S7 / Q2).
    """
    _logger.exception("unhandled error: %s", exc)
    return error_response("SERVER_ERROR", "Internal error (see server logs)", 500)
