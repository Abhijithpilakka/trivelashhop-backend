"""
tests/conftest.py
-----------------
Shared pytest fixtures. Tests use the real app with a mocked Supabase client.
"""

from __future__ import annotations

from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.client import get_db
from app.core.config import get_settings


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture
def mock_db():
    """A MagicMock that quacks like a Supabase client."""
    return MagicMock()


@pytest.fixture
def client(mock_db) -> Generator:
    """Test client with the real Supabase client replaced by the mock."""
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client) -> str:
    """Get a valid admin JWT. Requires ADMIN_PASSWORD_HASH to be set in .env.test."""
    settings = get_settings()
    from app.core.security import create_access_token
    return create_access_token(subject=settings.ADMIN_USERNAME)


@pytest.fixture
def auth_headers(admin_token) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Sample Data ──────────────────────────────────────────────────────────────

SAMPLE_PRODUCT = {
    "id": 1,
    "name": "Real Madrid Home 24/25",
    "club": "Real Madrid",
    "category": "Club",
    "description": "The iconic all-white home shirt.",
    "price": 1299,
    "offer_price": 999,
    "logo": "Embroidery",
    "in_stock": True,
    "sizes": {"S": 8, "M": 3, "L": 0, "XL": 5, "XXL": 2},
    "versions": ["Fan Version", "Player Version"],
    "photos": ["https://example.com/photo.jpg"],
    "tag": "bestseller",
    "display_price": 999,
    "discount_pct": 23,
}
