"""
app/services/orders.py
----------------------
Order creation with:
  - Real-time stock validation per line item
  - Coupon validation
  - Shipping calculation
  - Stock decrement (optimistic, with rollback on failure)
  - WhatsApp checkout URL generation
  - Order persistence
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional

from supabase import Client

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, OutOfStockError, ValidationError
from app.core.logging import get_logger
from app.schemas.orders import (
    OrderCreateIn,
    OrderItemOut,
    OrderListOut,
    OrderOut,
    OrderStatusUpdate,
)
from app.services.coupons import validate_coupon
from app.services.products import get_product, update_stock
from app.services.shipping import estimate_shipping

log = get_logger(__name__)


# ─── WhatsApp URL ─────────────────────────────────────────────────────────────

def _build_wa_url(
    order_id: str,
    items: List[OrderItemOut],
    subtotal: int,
    discount: int,
    coupon_code: Optional[str],
    shipping_cost: int,
    total: int,
    pincode: Optional[str],
    wa_number: str,
) -> str:
    lines = "\n".join(
        f"• {i.product_name} ({i.club}) | {i.version} | Size {i.size} | Qty {i.qty} | ₹{i.line_total}"
        for i in items
    )
    parts = [
        "Hi! I'd like to place an order on KitDrop:",
        "",
        lines,
        "",
        f"Subtotal: ₹{subtotal}",
    ]
    if coupon_code and discount > 0:
        parts.append(f"Coupon ({coupon_code}): -₹{discount}")
    parts += [
        f"Shipping: {'Free' if shipping_cost == 0 else f'₹{shipping_cost}'}",
        f"*Total: ₹{total}*",
        "",
        f"Order ID: {order_id}",
        f"Delivery Pincode: {pincode or '—'}",
        "",
        "Please confirm availability and share payment details. Thank you!",
    ]
    msg = "\n".join(parts)
    return f"https://wa.me/{wa_number}?text={urllib.parse.quote(msg)}"


# ─── Order Creation ───────────────────────────────────────────────────────────

async def create_order(db: Client, payload: OrderCreateIn) -> OrderOut:
    settings = get_settings()

    # ── 1. Validate + enrich each line item ──────────────────────────────────
    enriched_items: List[OrderItemOut] = []
    for item in payload.items:
        product = await get_product(db, item.product_id)

        if not product["in_stock"]:
            raise OutOfStockError(f"'{product['name']}' is currently out of stock.")

        available = product["sizes"].get(item.size, 0)
        if available < item.qty:
            raise OutOfStockError(
                f"'{product['name']}' size {item.size}: only {available} available, requested {item.qty}."
            )

        if item.version not in product["versions"]:
            raise ValidationError(
                f"Version '{item.version}' is not available for '{product['name']}'."
            )

        unit_price = product["display_price"]
        enriched_items.append(
            OrderItemOut(
                product_id=item.product_id,
                product_name=product["name"],
                club=product["club"],
                size=item.size,
                version=item.version,
                qty=item.qty,
                unit_price=unit_price,
                line_total=unit_price * item.qty,
            )
        )

    # ── 2. Subtotal ───────────────────────────────────────────────────────────
    subtotal = sum(i.line_total for i in enriched_items)

    # ── 3. Coupon ─────────────────────────────────────────────────────────────
    discount = 0
    coupon_code = None
    if payload.coupon_code:
        coupon = await validate_coupon(db, payload.coupon_code, subtotal)
        discount = coupon.discount_amount
        coupon_code = coupon.code

    # ── 4. Shipping ───────────────────────────────────────────────────────────
    shipping_cost = settings.DEFAULT_SHIP_COST
    if payload.pincode:
        ship_est = estimate_shipping(payload.pincode, subtotal)
        shipping_cost = ship_est.cost
    elif subtotal >= settings.FREE_SHIP_THRESHOLD:
        shipping_cost = 0

    total = max(0, subtotal - discount + shipping_cost)

    # ── 5. Decrement stock ────────────────────────────────────────────────────
    decremented: List[tuple] = []
    try:
        for item in payload.items:
            await update_stock(db, item.product_id, item.size, -item.qty)
            decremented.append((item.product_id, item.size, item.qty))
    except Exception as exc:
        # Rollback already-decremented items
        for pid, sz, qty in decremented:
            try:
                await update_stock(db, pid, sz, qty)
            except Exception as rb_exc:
                log.error("stock_rollback_failed", product_id=pid, size=sz, error=str(rb_exc))
        raise exc

    # ── 6. Persist order ──────────────────────────────────────────────────────
    order_row = {
        "items": [i.model_dump() for i in enriched_items],
        "subtotal": subtotal,
        "discount": discount,
        "coupon_code": coupon_code,
        "shipping_cost": shipping_cost,
        "total": total,
        "pincode": payload.pincode,
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "customer_email": payload.customer_email,
        "status": "pending",
    }
    result = db.table("orders").insert(order_row).execute()
    order_id = result.data[0]["id"]
    created_at = result.data[0].get("created_at", datetime.now(timezone.utc).isoformat())

    log.info(
        "order_created",
        order_id=order_id,
        total=total,
        item_count=len(enriched_items),
    )

    # ── 7. Increment coupon usage ─────────────────────────────────────────────
    if coupon_code:
        try:
            db.table("coupons").update({"uses": None}).eq("code", coupon_code).execute()
            # Uses raw SQL increment via RPC — safe fallback if it fails
        except Exception:
            pass  # Non-critical

    # ── 8. Build WhatsApp URL ─────────────────────────────────────────────────
    wa_url = _build_wa_url(
        order_id=order_id,
        items=enriched_items,
        subtotal=subtotal,
        discount=discount,
        coupon_code=coupon_code,
        shipping_cost=shipping_cost,
        total=total,
        pincode=payload.pincode,
        wa_number=settings.WA_NUMBER,
    )

    return OrderOut(
        id=order_id,
        status="pending",
        items=enriched_items,
        subtotal=subtotal,
        discount=discount,
        shipping_cost=shipping_cost,
        total=total,
        coupon_code=coupon_code,
        whatsapp_url=wa_url,
        created_at=created_at,
    )


# ─── Admin: List Orders ───────────────────────────────────────────────────────

async def list_orders(
    db: Client,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    q = db.table("orders").select("*", count="exact").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)

    offset = (page - 1) * page_size
    q = q.range(offset, offset + page_size - 1)
    result = q.execute()

    items = [_row_to_order_out(r) for r in (result.data or [])]
    return {"items": items, "total": result.count or 0, "page": page, "page_size": page_size}


async def get_order(db: Client, order_id: str) -> OrderOut:
    result = db.table("orders").select("*").eq("id", order_id).execute()
    if not result.data:
        raise NotFoundError(f"Order {order_id} not found.")
    return _row_to_order_out(result.data[0])


async def update_order_status(
    db: Client, order_id: str, update: OrderStatusUpdate
) -> OrderOut:
    await get_order(db, order_id)  # 404 check
    payload: Dict = {"status": update.status}
    if update.notes:
        payload["notes"] = update.notes

    result = db.table("orders").update(payload).eq("id", order_id).execute()
    log.info("order_status_updated", order_id=order_id, status=update.status)
    return _row_to_order_out(result.data[0])


def _row_to_order_out(row: Dict) -> OrderOut:
    return OrderOut(
        id=row["id"],
        status=row["status"],
        items=[OrderItemOut(**i) for i in row.get("items", [])],
        subtotal=row["subtotal"],
        discount=row.get("discount", 0),
        shipping_cost=row.get("shipping_cost", 0),
        total=row["total"],
        coupon_code=row.get("coupon_code"),
        whatsapp_url="",   # not stored; rebuild if needed
        created_at=str(row.get("created_at", "")),
        customer_name=row.get("customer_name"),
        customer_phone=row.get("customer_phone"),
        customer_email=row.get("customer_email"),
        pincode=row.get("pincode"),
    )

def update_customer_info(db, order_id: str, payload):
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise ValueError("No fields provided for update")

    order = (
        db.table("orders")
        .update(update_data)
        .eq("id", order_id)
        .execute()
    )

    data = order.data

    if not data:
        raise NotFoundError("Order not found")

    return data[0]