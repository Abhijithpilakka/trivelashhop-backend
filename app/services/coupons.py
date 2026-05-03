"""
app/services/coupons.py
-----------------------
Coupon validation with DB-backed coupons and fallback to config.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from supabase import Client

from app.core.config import get_settings
from app.core.exceptions import InvalidCouponError
from app.core.logging import get_logger
from app.schemas.orders import CouponOut

log = get_logger(__name__)

# Hardcoded fallback coupons (move everything to DB for production)
_BUILTIN_COUPONS: Dict[str, Dict] = {
    "KITDROP10": {"type": "pct", "value": 10, "min_order": 0, "max_uses": None},
    "FLAT150": {"type": "flat", "value": 150, "min_order": 500, "max_uses": None},
    "NEWSEASON": {"type": "pct", "value": 15, "min_order": 999, "max_uses": None},
}


def _calc_discount(coupon: Dict, subtotal: int) -> int:
    if coupon["type"] == "pct":
        return round(subtotal * coupon["value"] / 100)
    return min(coupon["value"], subtotal)  # flat can't exceed subtotal


async def validate_coupon(db: Client, code: str, subtotal: int) -> CouponOut:
    code = code.strip().upper()

    # ── 1. Try DB coupons table first ────────────────────────────────────────
    try:
        result = (
            db.table("coupons")
            .select("*")
            .eq("code", code)
            .eq("active", True)
            .execute()
        )
        if result.data:
            row = result.data[0]

            # Check expiry
            if row.get("expires_at"):
                expires = datetime.fromisoformat(row["expires_at"])
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < datetime.now(timezone.utc):
                    raise InvalidCouponError("Coupon has expired.")

            # Check usage limit
            if row.get("max_uses") and row.get("uses", 0) >= row["max_uses"]:
                raise InvalidCouponError("Coupon usage limit reached.")

            # Check min order
            if subtotal < (row.get("min_order") or 0):
                raise InvalidCouponError(
                    f"Minimum order ₹{row['min_order']} required for this coupon."
                )

            discount = _calc_discount(row, subtotal)
            return CouponOut(
                code=code,
                type=row["type"],
                value=row["value"],
                discount_amount=discount,
                message=f"{row['value']}{'%' if row['type'] == 'pct' else '₹'} off applied!",
            )
    except InvalidCouponError:
        raise
    except Exception as e:
        log.warning("coupon_db_lookup_failed", code=code, error=str(e))
        # Fall through to builtin coupons

    # ── 2. Fallback to builtin coupons ───────────────────────────────────────
    coupon = _BUILTIN_COUPONS.get(code)
    if not coupon:
        raise InvalidCouponError(f"Coupon '{code}' is not valid.")

    if subtotal < coupon["min_order"]:
        raise InvalidCouponError(
            f"Minimum order ₹{coupon['min_order']} required for this coupon."
        )

    discount = _calc_discount(coupon, subtotal)
    label = f"{coupon['value']}{'%' if coupon['type'] == 'pct' else '₹'}"
    return CouponOut(
        code=code,
        type=coupon["type"],
        value=coupon["value"],
        discount_amount=discount,
        message=f"{label} off applied!",
    )
