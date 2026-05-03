"""
tests/integration/test_products_api.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import SAMPLE_PRODUCT


class TestListProducts:
    def test_returns_200(self, client):
        with patch("app.services.products.list_products", AsyncMock(return_value={
            "items": [SAMPLE_PRODUCT],
            "total": 1,
            "page": 1,
            "page_size": 20,
        })):
            resp = client.get("/api/v1/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == SAMPLE_PRODUCT["name"]

    def test_filter_by_category(self, client):
        with patch("app.services.products.list_products", AsyncMock(return_value={
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        })):
            resp = client.get("/api/v1/products?category=Retro")
        assert resp.status_code == 200

    def test_invalid_sort_by_rejected(self, client):
        resp = client.get("/api/v1/products?sort_by=hacked")
        assert resp.status_code == 422


class TestGetProduct:
    def test_found(self, client):
        with patch("app.services.products.get_product", AsyncMock(return_value=SAMPLE_PRODUCT)):
            resp = client.get("/api/v1/products/1")
        assert resp.status_code == 200

    def test_not_found(self, client):
        from app.core.exceptions import NotFoundError
        with patch("app.services.products.get_product", AsyncMock(side_effect=NotFoundError("not found"))):
            resp = client.get("/api/v1/products/999")
        assert resp.status_code == 404


class TestAdminCreateProduct:
    VALID_PAYLOAD = {
        "name": "Test Kit",
        "club": "Test FC",
        "category": "Club",
        "description": "A test football jersey for testing purposes only.",
        "price": 999,
        "offer_price": 799,
        "logo": "Embroidery",
        "in_stock": True,
        "sizes": {"S": 5, "M": 5, "L": 5, "XL": 5, "XXL": 5},
        "versions": ["Fan Version"],
        "photos": ["https://example.com/photo.jpg"],
        "tag": "new",
    }

    def test_requires_auth(self, client):
        resp = client.post("/api/v1/products", json=self.VALID_PAYLOAD)
        assert resp.status_code == 401

    def test_creates_with_auth(self, client, auth_headers):
        with patch("app.services.products.create_product", AsyncMock(return_value={
            **self.VALID_PAYLOAD,
            "id": 99,
            "display_price": 799,
            "discount_pct": 20,
        })):
            resp = client.post("/api/v1/products", json=self.VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201

    def test_invalid_category_rejected(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "category": "Invalid"}
        resp = client.post("/api/v1/products", json=payload, headers=auth_headers)
        assert resp.status_code == 422


class TestShippingEstimate:
    def test_valid_pincode(self, client):
        resp = client.post("/api/v1/orders/shipping/estimate", json={
            "pincode": "400001",
            "subtotal": 500,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "zone" in data
        assert "cost" in data

    def test_invalid_pincode_format(self, client):
        resp = client.post("/api/v1/orders/shipping/estimate", json={
            "pincode": "12345",   # 5 digits, not 6
            "subtotal": 500,
        })
        assert resp.status_code == 422


class TestCouponValidate:
    def test_valid_coupon(self, client):
        with patch("app.services.coupons.validate_coupon", AsyncMock(return_value=MagicMock(
            code="KITDROP10",
            type="pct",
            value=10,
            discount_amount=100,
            message="10% off applied!",
        ))):
            resp = client.post("/api/v1/orders/coupon/validate", json={
                "code": "KITDROP10",
                "subtotal": 1000,
            })
        assert resp.status_code == 200
