"""
app/api/v1/routers/products.py
------------------------------
Public:
  GET  /products             — list with filters, search, pagination
  GET  /products/{id}        — single product

Admin (require_admin):
  POST   /products           — create
  PATCH  /products/{id}      — update
  DELETE /products/{id}      — delete
  PATCH  /products/{id}/stock — adjust stock for a size
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from supabase import Client

from app.core.dependencies import AdminDep
from app.db.client import get_db
from app.schemas.products import ProductCreate, ProductListOut, ProductOut, ProductUpdate
from app.services import products as svc

router = APIRouter()


# ─── Public ───────────────────────────────────────────────────────────────────

@router.get("", response_model=ProductListOut, summary="List products")
async def list_products(
    db: Client = Depends(get_db),
    category: Optional[str] = Query(None, description="Club | National | Retro"),
    in_stock: Optional[bool] = Query(None),
    tag: Optional[str] = Query(None, description="bestseller | new | retro | soldout"),
    search: Optional[str] = Query(None, max_length=80),
    sort_by: str = Query("id", pattern="^(id|price|name|created_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await svc.list_products(
        db,
        category=category,
        in_stock=in_stock,
        tag=tag,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductOut, summary="Get product")
async def get_product(product_id: int, db: Client = Depends(get_db)):
    return await svc.get_product(db, product_id)


# ─── Admin ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProductOut,
    status_code=201,
    summary="[Admin] Create product",
    dependencies=[AdminDep],
)
async def create_product(data: ProductCreate, db: Client = Depends(get_db)):
    return await svc.create_product(db, data)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="[Admin] Update product",
    dependencies=[AdminDep],
)
async def update_product(
    product_id: int, data: ProductUpdate, db: Client = Depends(get_db)
):
    return await svc.update_product(db, product_id, data)


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="[Admin] Delete product",
    dependencies=[AdminDep],
)
async def delete_product(product_id: int, db: Client = Depends(get_db)):
    await svc.delete_product(db, product_id)


class StockBody(BaseModel):
    size: str = Field(..., pattern="^(S|M|L|XL|XXL)$")
    delta: int = Field(..., description="Positive = restock, negative = remove")


@router.patch(
    "/{product_id}/stock",
    response_model=ProductOut,
    summary="[Admin] Adjust stock for a size",
    dependencies=[AdminDep],
)
async def adjust_stock(
    product_id: int, body: StockBody, db: Client = Depends(get_db)
):
    return await svc.update_stock(db, product_id, body.size, body.delta)
