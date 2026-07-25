"""
Centralized API exception handling.

The actuarial-engine routers share a common exception-handling shape:

  - ActuarialValidationError    -> 422 (structured detail via to_dict())
  - DataNotAvailableError        -> 503 (data files missing / not loaded)
  - DataQualityError            -> 422 (structured detail via to_dict())
  - ValueError / KeyError       -> 400 (caller passed a bad value)
  - FileNotFoundError           -> 503 (a data file is missing at request time)
  - Any other Exception         -> 500 (logged with stack trace, sanitized
                                       message returned to the client)

Use :func:`safe_route` as a decorator on router endpoints to apply this
mapping uniformly, instead of copy-pasting the same six ``except`` clauses
into every endpoint.

All non-2xx responses produced by this module use a structured body of
the form::

    {"detail": <message-or-dict>, "error": <class-name>}

mirroring FastAPI's default ``{"detail": ...}`` shape so existing
frontend error extractors keep working.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from backend.engine.exceptions import (
    ActuarialError,
    ActuarialValidationError,
    DataNotAvailableError,
    DataQualityError,
)

logger = logging.getLogger(__name__)


def _body(exc: Exception, *, include_detail: bool = True) -> dict[str, Any]:
    """Build a structured JSON body for an exception response."""
    if isinstance(exc, ActuarialError):
        payload: dict[str, Any] = exc.to_dict()
        return {"detail": payload, "error": exc.__class__.__name__}
    return {
        "detail": str(exc) if include_detail else "Internal server error",
        "error": exc.__class__.__name__,
    }


def map_exception_to_response(exc: Exception) -> HTTPException:
    """
    Translate an engine / service exception into a FastAPI HTTPException
    with the appropriate status code and a sanitized, structured body.
    """
    # HTTPException should pass through untouched so callers' own explicit
    # raises (e.g. 404s) are not re-wrapped.
    if isinstance(exc, HTTPException):
        return exc

    if isinstance(exc, ActuarialValidationError | DataQualityError):
        return HTTPException(status_code=422, detail=_body(exc)["detail"])
    if isinstance(exc, DataNotAvailableError):
        return HTTPException(status_code=503, detail=_body(exc)["detail"])
    if isinstance(exc, FileNotFoundError):
        # A data file required to serve this request is missing at request
        # time (e.g. a regulatory CSV was not shipped). This is a service
        # availability problem, not a client error.
        logger.warning("FileNotFoundError serving request: %s", exc)
        return HTTPException(
            status_code=503,
            detail={
                "error": "FileNotFoundError",
                "message": "Required data file is unavailable.",
            },
        )
    if isinstance(exc, ValueError | KeyError):
        return HTTPException(status_code=400, detail=_body(exc)["detail"])

    # Anything else: log the full stack trace internally, return a sanitized
    # message so internal stack traces never leak to the client.
    logger.exception("Unhandled error in API route: %s", exc)
    return HTTPException(
        status_code=500,
        detail={"error": "InternalServerError", "message": "Internal server error"},
    )


def safe_route[T](func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that wraps a synchronous FastAPI endpoint and maps any
    exception raised inside it to a structured HTTPException via
    :func:`map_exception_to_response`.
    """

    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            raise map_exception_to_response(exc) from exc

    wrapper.__name__ = getattr(func, "__name__", "wrapper")
    wrapper.__doc__ = getattr(func, "__doc__", None)
    wrapper.__wrapped__ = func  # type: ignore[attr-defined]
    return wrapper
