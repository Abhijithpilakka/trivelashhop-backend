"""
app/api/v1/routers/orders.py
-----------------------------
Public:
  POST /orders               — create order (validates stock, applies coupon, decrements stock)
  POST /orders/coupon/validate — validate a coupon code
  POST /orders/shipping/estimate — estimate shipping for pincode

Admin (require_admin):
  GET  /orders               — list all orders (paginated)
  GET  /orders/{id}          — get single order
  PATCH /orders/{id}/status  — update order status
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import AdminDep
from app.db.client import get_db
from app.schemas.orders import (
    CouponOut,
    CouponValidateIn,
    OrderCreateIn,
    OrderListOut,
    OrderOut,
    OrderStatusUpdate,
    ShippingEstimateIn,
    ShippingEstimateOut,
)
from app.services import coupons as coupon_svc
from app.services import orders as order_svc
from app.services.shipping import estimate_shipping

router = APIRouter()


# ─── Public ───────────────────────────────────────────────────────────────────

@router.post("", response_model=OrderOut, status_code=201, summary="Create order")
async def create_order(payload: OrderCreateIn, db: Client = Depends(get_db)):
    return await order_svc.create_order(db, payload)


@router.post(
    "/coupon/validate",
    response_model=CouponOut,
    summary="Validate a coupon code",
)
async def validate_coupon(body: CouponValidateIn, db: Client = Depends(get_db)):
    return await coupon_svc.validate_coupon(db, body.code, body.subtotal)


@router.post(
    "/shipping/estimate",
    response_model=ShippingEstimateOut,
    summary="Estimate shipping for a pincode",
)
def shipping_estimate(body: ShippingEstimateIn):
    return estimate_shipping(body.pincode, body.subtotal)


# ─── Admin ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=OrderListOut,
    summary="[Admin] List orders",
    dependencies=[AdminDep],
)
async def list_orders(
    db: Client = Depends(get_db),
    status: str = Query(None, pattern="^(pending|confirmed|shipped|delivered|cancelled)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await order_svc.list_orders(db, status=status, page=page, page_size=page_size)


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="[Admin] Get order",
    dependencies=[AdminDep],
)
async def get_order(order_id: str, db: Client = Depends(get_db)):
    return await order_svc.get_order(db, order_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="[Admin] Update order status",
    dependencies=[AdminDep],
)
async def update_order_status(
    order_id: str,
    update: OrderStatusUpdate,
    db: Client = Depends(get_db),
):
    return await order_svc.update_order_status(db, order_id, update)
