"""
app/schemas/orders.py
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ─── Cart / Order Items ───────────────────────────────────────────────────────

class OrderItemIn(BaseModel):
    product_id: int
    size: str = Field(..., pattern="^(S|M|L|XL|XXL)$")
    version: str = Field(..., min_length=1, max_length=60)
    qty: int = Field(..., ge=1, le=10)


class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    club: str
    size: str
    version: str
    qty: int
    unit_price: int
    line_total: int


# ─── Coupon ──────────────────────────────────────────────────────────────────

class CouponValidateIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    subtotal: int = Field(..., gt=0)


class CouponOut(BaseModel):
    code: str
    type: str          # "pct" | "flat"
    value: int
    discount_amount: int
    message: str


# ─── Shipping ────────────────────────────────────────────────────────────────

class ShippingEstimateIn(BaseModel):
    pincode: str = Field(..., pattern=r"^\d{6}$")
    subtotal: int = Field(..., ge=0)


class ShippingEstimateOut(BaseModel):
    zone: str
    eta: str
    cost: int
    is_free: bool


# ─── Order ───────────────────────────────────────────────────────────────────

class OrderCreateIn(BaseModel):
    items: List[OrderItemIn] = Field(..., min_length=1, max_length=20)
    coupon_code: Optional[str] = Field(None, max_length=30)
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$")
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, pattern=r"^\d{10}$")
    customer_email: Optional[str] = Field(None, max_length=120)

    @field_validator("items")
    @classmethod
    def no_duplicate_items(cls, v):
        seen = set()
        for item in v:
            key = (item.product_id, item.size, item.version)
            if key in seen:
                raise ValueError(
                    f"Duplicate item: product {item.product_id} size {item.size} version {item.version}"
                )
            seen.add(key)
        return v


class OrderOut(BaseModel):
    id: str
    status: str
    items: List[OrderItemOut]
    subtotal: int
    discount: int
    shipping_cost: int
    total: int
    coupon_code: Optional[str]
    whatsapp_url: str
    created_at: str
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    pincode: str | None = None

# ─── Admin Order Update ──────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|shipped|delivered|cancelled)$")
    notes: Optional[str] = Field(None, max_length=500)


class OrderListOut(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    page_size: int

class OrderCustomerInfo(BaseModel):
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$")
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, pattern=r"^\d{10}$")
    customer_email: Optional[str] = Field(None, max_length=120)

class OrderCustomerUpdateOut(BaseModel):
    id: str
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    pincode: str | None = None