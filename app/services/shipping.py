"""
app/services/shipping.py
------------------------
Pincode-based shipping zone estimation.
Extend this with a real courier API (Shiprocket, Delhivery, etc.) later.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.schemas.orders import ShippingEstimateOut


_ZONES = [
    # (prefix_range_start, prefix_range_end, zone_label, eta, cost_override)
    (40, 41, "Mumbai Local",   "3–4 days",  60),
    (36, 42, "West India",     "4–5 days",  60),
    (50, 69, "Pan India",      "5–6 days",  None),   # None = default
    (10, 29, "Pan India",      "5–6 days",  None),
    (78, 79, "Northeast",      "5–7 days",  120),
    (83, 85, "Andaman & Nicobar / Lakshadweep", "7–10 days", 200),
]


def estimate_shipping(pincode: str, subtotal: int) -> ShippingEstimateOut:
    settings = get_settings()
    prefix = int(pincode[:2])

    zone_label = "Standard"
    eta = "3–5 days"
    cost = settings.DEFAULT_SHIP_COST

    # Match first applicable zone
    for start, end, label, zone_eta, override in _ZONES:
        if start <= prefix <= end:
            zone_label = label
            eta = zone_eta
            cost = override if override is not None else settings.DEFAULT_SHIP_COST
            break

    # Free shipping override
    is_free = subtotal >= settings.FREE_SHIP_THRESHOLD
    if is_free:
        cost = 0

    return ShippingEstimateOut(
        zone=zone_label,
        eta=eta,
        cost=cost,
        is_free=is_free,
    )
