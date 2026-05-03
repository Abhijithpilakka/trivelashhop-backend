"""
app/schemas/products.py
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ProductSizes(BaseModel):
    S: int = Field(0, ge=0)
    M: int = Field(0, ge=0)
    L: int = Field(0, ge=0)
    XL: int = Field(0, ge=0)
    XXL: int = Field(0, ge=0)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    club: str = Field(..., min_length=1, max_length=80)
    category: str = Field(..., pattern="^(Club|National|Retro)$")
    description: str = Field(..., min_length=10, max_length=1000)
    price: int = Field(..., gt=0, le=99_999)
    offer_price: Optional[int] = Field(None, gt=0, le=99_999)
    logo: str = Field(..., pattern="^(Embroidery|Heat Pressed)$")
    in_stock: bool = True
    sizes: ProductSizes = Field(default_factory=ProductSizes)
    versions: List[str] = Field(default_factory=list)
    photos: List[str] = Field(default_factory=list)
    tag: Optional[str] = Field(None, pattern="^(bestseller|new|retro|soldout)$")

    @field_validator("offer_price")
    @classmethod
    def offer_must_be_less_than_price(cls, v, info):
        if v is not None and "price" in info.data and v >= info.data["price"]:
            raise ValueError("offer_price must be less than price")
        return v

    @field_validator("photos")
    @classmethod
    def at_least_one_photo(cls, v):
        if len(v) == 0:
            raise ValueError("At least one photo is required")
        return v

    @field_validator("versions")
    @classmethod
    def at_least_one_version(cls, v):
        if len(v) == 0:
            raise ValueError("At least one version is required")
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    """All fields optional for PATCH."""
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    club: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(Club|National|Retro)$")
    description: Optional[str] = None
    price: Optional[int] = Field(None, gt=0)
    offer_price: Optional[int] = Field(None, gt=0)
    logo: Optional[str] = Field(None, pattern="^(Embroidery|Heat Pressed)$")
    in_stock: Optional[bool] = None
    sizes: Optional[ProductSizes] = None
    versions: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    tag: Optional[str] = Field(None, pattern="^(bestseller|new|retro|soldout)$")


class ProductOut(ProductBase):
    id: int
    display_price: int
    discount_pct: int

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int
