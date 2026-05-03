"""
app/core/dependencies.py
------------------------
FastAPI dependency-injection helpers.
"""

from __future__ import annotations

from fastapi import Depends, Header
from jose import JWTError

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.client import get_db


# ─── Re-export DB dep ─────────────────────────────────────────────────────────

DBDep = Depends(get_db)


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _get_token(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Invalid Authorization header.")
    return token


def require_admin(token: str = Depends(_get_token)) -> str:
    """Returns admin username or raises 401."""
    settings = get_settings()
    try:
        subject = decode_access_token(token)
    except JWTError:
        raise UnauthorizedError("Token is invalid or expired.")
    if subject != settings.ADMIN_USERNAME:
        raise UnauthorizedError("Not an admin account.")
    return subject


AdminDep = Depends(require_admin)
