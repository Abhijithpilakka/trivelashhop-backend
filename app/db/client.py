"""
app/db/client.py
----------------
Supabase client — one instance per process.
The service-role client is used server-side (bypasses RLS for admin ops).
The anon client is available for public queries that respect RLS.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Generator

from supabase import Client, create_client

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _service_client() -> Client:
    settings = get_settings()
    log.info("supabase_connect", url=settings.SUPABASE_URL, role="service")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@lru_cache(maxsize=1)
def _anon_client() -> Client:
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_db() -> Generator[Client, None, None]:
    """FastAPI dependency — yields the service-role client."""
    yield _service_client()


def get_anon_db() -> Generator[Client, None, None]:
    """FastAPI dependency — yields the anon client (respects RLS)."""
    yield _anon_client()
