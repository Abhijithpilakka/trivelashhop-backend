"""
app/main.py
-----------
Application factory. Import `app` to run with uvicorn.
"""

from __future__ import annotations

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.cache import close_cache, init_cache
from app.middleware.logging import RequestLoggingMiddleware

# ─── Logging ──────────────────────────────────────────────────────────────────
setup_logging()
log = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    # ── Sentry ────────────────────────────────────────────────────────────────
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )
        log.info("sentry_enabled")

    # ── Rate limiter ──────────────────────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])

    # ── FastAPI ───────────────────────────────────────────────────────────────
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "KitDrop backend API. "
            "Public endpoints serve the storefront. "
            "Admin endpoints require a Bearer JWT from `POST /api/v1/auth/login`."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ── Attach limiter ────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # ── Request logging ───────────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        log.info("app_startup", env=settings.ENVIRONMENT, version=settings.APP_VERSION)
        await init_cache()

    @app.on_event("shutdown")
    async def shutdown():
        log.info("app_shutdown")
        await close_cache()

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    def health():
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    def dashboard() -> HTMLResponse:
        return HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\" />
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
                <title>{settings.APP_NAME} Dashboard</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f5f7fb; color: #111; }}
                    .page {{ max-width: 980px; margin: 0 auto; padding: 40px; }}
                    .card {{ background: #fff; border-radius: 16px; box-shadow: 0 18px 40px rgba(17, 24, 39, 0.08); margin-bottom: 24px; padding: 26px; }}
                    h1 {{ margin-top: 0; }}
                    a {{ color: #0366d6; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
                    .meta {{ margin: 0 0 16px; color: #555; }}
                    .endpoint {{ margin: 0 0 10px; padding: 12px 14px; background: #f3f6fb; border-radius: 12px; font-family: 'SFMono-Regular', Consolas, monospace; }}
                    ul {{ padding-left: 18px; margin: 0; }}
                </style>
            </head>
            <body>
                <div class=\"page\">
                    <div class=\"card\">
                        <h1>{settings.APP_NAME} Dashboard</h1>
                        <p class=\"meta\">Version: {settings.APP_VERSION} · Environment: {settings.ENVIRONMENT}</p>
                        <p class=\"meta\">Quick access to health, docs, and the main API endpoints.</p>
                    </div>
                    <div class=\"grid\">
                        <div class=\"card\">
                            <h2>App links</h2>
                            <ul>
                                <li><a href=\"/health\">Health Check</a></li>
                                <li><a href=\"/docs\">API Docs</a></li>
                                <li><a href=\"/api/v1/products\">Products</a></li>
                            </ul>
                        </div>
                        <div class=\"card\">
                            <h2>Public endpoints</h2>
                            <p class=\"endpoint\">GET /api/v1/products</p>
                            <p class=\"endpoint\">GET /api/v1/products/{'{id}'}</p>
                            <p class=\"endpoint\">POST /api/v1/orders</p>
                            <p class=\"endpoint\">POST /api/v1/orders/shipping/estimate</p>
                        </div>
                        <div class=\"card\">
                            <h2>Admin endpoints</h2>
                            <p class=\"endpoint\">POST /api/v1/auth/login</p>
                            <p class=\"endpoint\">POST /api/v1/products</p>
                            <p class=\"endpoint\">PATCH /api/v1/products/{'{id}'}</p>
                            <p class=\"endpoint\">PATCH /api/v1/products/{'{id}'}/stock</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
        )
    @app.get("/", include_in_schema=False)
    def root():
        return JSONResponse({"message": f"{settings.APP_NAME} is running."})

    return app


app = create_app()
