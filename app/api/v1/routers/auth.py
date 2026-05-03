"""
app/api/v1/routers/auth.py
--------------------------
POST /auth/login  — returns a JWT for the admin panel

Set ONE of these in Railway variables:
  ADMIN_PASSWORD=admin123            (plain text, simplest)
  ADMIN_PASSWORD_HASH=$2b$12$...     (bcrypt hash, more secure)
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginIn, TokenOut

router = APIRouter()


@router.post("/login", response_model=TokenOut, summary="Admin login")
async def login(body: LoginIn) -> TokenOut:
    settings = get_settings()

    # ── 1. Username ───────────────────────────────────────────────────────────
    if body.username != settings.ADMIN_USERNAME:
        raise UnauthorizedError("Invalid credentials.")

    # ── 2. Plain-text password (simplest — set ADMIN_PASSWORD in Railway) ─────
    if settings.ADMIN_PASSWORD:
        if body.password != settings.ADMIN_PASSWORD:
            raise UnauthorizedError("Invalid credentials.")
        token = create_access_token(subject=settings.ADMIN_USERNAME)
        return TokenOut(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── 3. Bcrypt hash (set ADMIN_PASSWORD_HASH in Railway) ───────────────────
    if not settings.ADMIN_PASSWORD_HASH:
        raise UnauthorizedError(
            "Admin not configured. Set ADMIN_PASSWORD or ADMIN_PASSWORD_HASH "
            "in your Railway environment variables."
        )

    is_valid = await run_in_threadpool(verify_password, body.password, settings.ADMIN_PASSWORD_HASH)
    if not is_valid:
        raise UnauthorizedError("Invalid credentials.")

    token = create_access_token(subject=settings.ADMIN_USERNAME)
    return TokenOut(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )