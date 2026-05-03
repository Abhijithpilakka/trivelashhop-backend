"""
app/services/products.py
------------------------
All product business logic. Routers stay thin — they only validate input
and call this service.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import Client

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.cache import cache_delete_pattern, cache_get, cache_set
from app.schemas.products import ProductCreate, ProductOut, ProductUpdate

log = get_logger(__name__)

_CACHE_TTL = 300        # 5 minutes
_CACHE_PREFIX = "products"


def _compute_extras(row: Dict) -> Dict:
    """Add display_price and discount_pct to a raw DB row."""
    price = row.get("price", 0)
    offer = row.get("offer_price")
    display = offer if offer else price
    pct = round((1 - display / price) * 100) if offer and price else 0
    return {**row, "display_price": display, "discount_pct": pct}


async def list_products(
    db: Client,
    *,
    category: Optional[str] = None,
    in_stock: Optional[bool] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    cache_key = (
        f"{_CACHE_PREFIX}:list:{category}:{in_stock}:{tag}:{search}"
        f":{sort_by}:{sort_order}:{page}:{page_size}"
    )
    cached = await cache_get(cache_key)
    if cached:
        log.debug("cache_hit", key=cache_key)
        return cached

    q = db.table("products").select("*", count="exact")

    if category and category != "All":
        q = q.eq("category", category)
    if in_stock is not None:
        q = q.eq("in_stock", in_stock)
    if tag:
        q = q.eq("tag", tag)
    if search:
        q = q.ilike("name", f"%{search}%")

    # Pagination
    offset = (page - 1) * page_size
    q = q.order(sort_by, desc=(sort_order == "desc")).range(offset, offset + page_size - 1)

    result = q.execute()
    items = [_compute_extras(r) for r in (result.data or [])]
    total = result.count or 0

    out = {"items": items, "total": total, "page": page, "page_size": page_size}
    await cache_set(cache_key, out, ttl=_CACHE_TTL)
    return out


async def get_product(db: Client, product_id: int) -> Dict:
    cache_key = f"{_CACHE_PREFIX}:{product_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = db.table("products").select("*").eq("id", product_id).execute()
    if not result.data:
        raise NotFoundError(f"Product {product_id} not found.")

    row = _compute_extras(result.data[0])
    await cache_set(cache_key, row, ttl=_CACHE_TTL)
    return row


async def create_product(db: Client, data: ProductCreate) -> Dict:
    payload = data.model_dump()
    payload["sizes"] = payload["sizes"]  # already a dict from pydantic

    result = db.table("products").insert(payload).execute()
    if not result.data:
        raise ValidationError("Failed to create product.")

    await cache_delete_pattern(f"{_CACHE_PREFIX}:list:*")
    log.info("product_created", product_id=result.data[0]["id"])
    return _compute_extras(result.data[0])


async def update_product(db: Client, product_id: int, data: ProductUpdate) -> Dict:
    # Verify exists
    await get_product(db, product_id)

    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        raise ValidationError("No fields to update.")

    result = db.table("products").update(payload).eq("id", product_id).execute()
    if not result.data:
        raise NotFoundError(f"Product {product_id} not found after update.")

    # Bust cache
    await cache_delete_pattern(f"{_CACHE_PREFIX}:*")
    log.info("product_updated", product_id=product_id, fields=list(payload.keys()))
    return _compute_extras(result.data[0])


async def delete_product(db: Client, product_id: int) -> None:
    await get_product(db, product_id)  # raises 404 if missing
    db.table("products").delete().eq("id", product_id).execute()
    await cache_delete_pattern(f"{_CACHE_PREFIX}:*")
    log.info("product_deleted", product_id=product_id)


async def update_stock(db: Client, product_id: int, size: str, delta: int) -> Dict:
    """Increment or decrement stock for a specific size."""
    product = await get_product(db, product_id)
    sizes = dict(product["sizes"])

    if size not in sizes:
        raise ValidationError(f"Invalid size: {size}")

    new_qty = sizes[size] + delta
    if new_qty < 0:
        raise ValidationError(f"Insufficient stock for size {size}. Available: {sizes[size]}")

    sizes[size] = new_qty
    in_stock = any(q > 0 for q in sizes.values())

    result = (
        db.table("products")
        .update({"sizes": sizes, "in_stock": in_stock})
        .eq("id", product_id)
        .execute()
    )
    await cache_delete_pattern(f"{_CACHE_PREFIX}:*")
    log.info("stock_updated", product_id=product_id, size=size, delta=delta, new_qty=new_qty)
    return _compute_extras(result.data[0])
