"""
app/api/v1/routers/auth.py
--------------------------
POST /auth/login  — returns a JWT for the admin panel
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

    if body.username != settings.ADMIN_USERNAME:
        raise UnauthorizedError("Invalid credentials.")

    if not settings.ADMIN_PASSWORD_HASH:
        raise UnauthorizedError("Admin account not configured. Set ADMIN_PASSWORD_HASH.")

    # Run password verification in a thread to avoid async context issues with passlib
    is_valid = await run_in_threadpool(verify_password, body.password, settings.ADMIN_PASSWORD_HASH)
    if not is_valid:
        raise UnauthorizedError("Invalid credentials.")

    token = create_access_token(subject=settings.ADMIN_USERNAME)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenOut(access_token=token, token_type="bearer", expires_in=expires_in)
