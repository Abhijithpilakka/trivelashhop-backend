"""
tests/unit/test_shipping_and_coupons.py
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shipping import estimate_shipping
from app.services.coupons import validate_coupon
from app.core.exceptions import InvalidCouponError


class TestShipping:
    def test_mumbai_local(self):
        result = estimate_shipping("400001", 0)
        assert result.zone == "Mumbai Local"
        assert result.cost == 0
        assert result.is_free is True  # cost=0 means it's already free zone

    def test_free_shipping_threshold(self):
        result = estimate_shipping("110001", 1499)
        assert result.is_free is True
        assert result.cost == 0

    def test_standard_shipping(self):
        result = estimate_shipping("110001", 500)
        assert result.is_free is False
        assert result.cost > 0

    def test_northeast_surcharge(self):
        result = estimate_shipping("786001", 500)
        assert result.cost == 120
        assert "Northeast" in result.zone

    def test_invalid_pincode_still_returns(self):
        # Valid 6-digit pincode but unknown zone → Standard
        result = estimate_shipping("999999", 0)
        assert result.zone == "Standard"


class TestCoupons:
    @pytest.mark.asyncio
    async def test_valid_pct_coupon(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        result = await validate_coupon(db, "KITDROP10", 1000)
        assert result.code == "KITDROP10"
        assert result.discount_amount == 100

    @pytest.mark.asyncio
    async def test_valid_flat_coupon(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        result = await validate_coupon(db, "FLAT150", 1000)
        assert result.discount_amount == 150

    @pytest.mark.asyncio
    async def test_flat_coupon_below_min_order(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        with pytest.raises(InvalidCouponError, match="Minimum order"):
            await validate_coupon(db, "FLAT150", 100)

    @pytest.mark.asyncio
    async def test_invalid_coupon(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        with pytest.raises(InvalidCouponError):
            await validate_coupon(db, "FAKE999", 1000)

    @pytest.mark.asyncio
    async def test_flat_cannot_exceed_subtotal(self):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        # FLAT150 on ₹100 order → discount capped at ₹100
        result = await validate_coupon(db, "FLAT150", 600)
        assert result.discount_amount <= 600
