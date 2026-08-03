"""Shared request-scoped dependencies.

Currently just the demo session id, which gives each browser its own SCR
portfolio instead of one process-wide portfolio shared by every visitor.
"""

import secrets

from fastapi import Cookie, Response

SESSION_COOKIE = "sima_session"

# Opaque, unauthenticated, and used for nothing but partitioning demo portfolio
# state. It carries no identity and grants no privilege, so it is not a
# credential -- but it is still marked HttpOnly and SameSite=Lax so it is not
# readable from page scripts and is not sent on cross-site requests.
_COOKIE_MAX_AGE = 60 * 60


def demo_session(
    response: Response,
    sima_session: str | None = Cookie(default=None),
) -> str:
    """Return this caller's session id, minting and setting one if absent."""
    if sima_session and len(sima_session) <= 64 and sima_session.isalnum():
        return sima_session

    session_id = secrets.token_hex(16)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return session_id
