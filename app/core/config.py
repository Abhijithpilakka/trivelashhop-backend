"""
app/core/config.py
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "KitDrop API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", pattern="^(development|staging|production)$")
    DEBUG: bool = False

    # ─── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # ─── Auth / JWT ───────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ─── Admin credentials ────────────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    # Option A — plain text (set this in Railway, simplest):
    ADMIN_PASSWORD: str = ""
    # Option B — bcrypt hash (generate with: python scripts/hash_password.py):
    ADMIN_PASSWORD_HASH: str = ""

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return ",".join(str(o).strip() for o in parsed)
                except json.JSONDecodeError:
                    pass
            return value
        return v

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ─── WhatsApp ─────────────────────────────────────────────────────────────
    WA_NUMBER: str = "919999999999"

    # ─── Business Rules ───────────────────────────────────────────────────────
    FREE_SHIP_THRESHOLD: int = 1499
    DEFAULT_SHIP_COST: int = 79
    MAX_CART_ITEMS: int = 20
    MAX_QTY_PER_ITEM: int = 10

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = ""

    # ─── Sentry ───────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ORDERS_PER_HOUR: int = 10

    # ─── Cloudinary ───────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cloudinary_configured(self) -> bool:
        return bool(self.CLOUDINARY_CLOUD_NAME and self.CLOUDINARY_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()