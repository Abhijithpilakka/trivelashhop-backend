"""
tests/unit/test_products_service.py
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import NotFoundError, ValidationError
from app.services import products as svc
from app.schemas.products import ProductCreate, ProductSizes, ProductUpdate
from tests.conftest import SAMPLE_PRODUCT


@pytest.fixture
def db():
    return MagicMock()


class TestComputeExtras:
    def test_with_offer_price(self):
        row = {"price": 1299, "offer_price": 999}
        out = svc._compute_extras(row)
        assert out["display_price"] == 999
        assert out["discount_pct"] == 23

    def test_without_offer_price(self):
        row = {"price": 899, "offer_price": None}
        out = svc._compute_extras(row)
        assert out["display_price"] == 899
        assert out["discount_pct"] == 0


class TestGetProduct:
    @pytest.mark.asyncio
    async def test_found(self, db):
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            SAMPLE_PRODUCT
        ]
        with patch("app.services.products.cache_get", AsyncMock(return_value=None)):
            with patch("app.services.products.cache_set", AsyncMock()):
                result = await svc.get_product(db, 1)
        assert result["id"] == 1
        assert result["display_price"] == 999

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.services.products.cache_get", AsyncMock(return_value=None)):
            with pytest.raises(NotFoundError):
                await svc.get_product(db, 999)

    @pytest.mark.asyncio
    async def test_cache_hit(self, db):
        with patch("app.services.products.cache_get", AsyncMock(return_value=SAMPLE_PRODUCT)):
            result = await svc.get_product(db, 1)
        db.table.assert_not_called()
        assert result["id"] == 1


class TestUpdateStock:
    @pytest.mark.asyncio
    async def test_decrement_success(self, db):
        product = {**SAMPLE_PRODUCT, "sizes": {"S": 8, "M": 3, "L": 0, "XL": 5, "XXL": 2}}
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [product]
        db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {**product, "sizes": {"S": 7, "M": 3, "L": 0, "XL": 5, "XXL": 2}}
        ]
        with patch("app.services.products.cache_get", AsyncMock(return_value=None)):
            with patch("app.services.products.cache_set", AsyncMock()):
                with patch("app.services.products.cache_delete_pattern", AsyncMock()):
                    result = await svc.update_stock(db, 1, "S", -1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_decrement_below_zero_raises(self, db):
        product = {**SAMPLE_PRODUCT, "sizes": {"S": 0, "M": 3, "L": 0, "XL": 5, "XXL": 2}}
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [product]
        with patch("app.services.products.cache_get", AsyncMock(return_value=None)):
            with patch("app.services.products.cache_set", AsyncMock()):
                with pytest.raises(ValidationError, match="Insufficient stock"):
                    await svc.update_stock(db, 1, "S", -1)
