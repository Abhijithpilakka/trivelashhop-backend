"""
app/core/exceptions.py
----------------------
Domain exceptions + FastAPI exception handlers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.logging import get_logger

log = get_logger(__name__)


# ─── Domain Exceptions ────────────────────────────────────────────────────────

class KitDropException(Exception):
    """Base for all domain errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(KitDropException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(KitDropException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class ValidationError(KitDropException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed."


class OutOfStockError(KitDropException):
    status_code = status.HTTP_409_CONFLICT
    detail = "One or more items are out of stock."


class InvalidCouponError(KitDropException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Coupon code is invalid or expired."


class UnauthorizedError(KitDropException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class ForbiddenError(KitDropException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


# ─── Handlers ─────────────────────────────────────────────────────────────────

def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"detail": detail, "status_code": status_code}},
    )


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(KitDropException)
    async def kitdrop_handler(request: Request, exc: KitDropException):
        log.warning("domain_error", detail=exc.detail, path=request.url.path)
        return _error_response(exc.status_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        log.warning("validation_error", errors=errors, path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"detail": "Request validation failed.", "errors": errors}},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        log.exception("unhandled_error", path=request.url.path)
        return _error_response(500, "Internal server error.")
