import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from .responses import error_body

logger = logging.getLogger(__name__)


class AppError(APIException):
    """Base class for our domain errors; accepts an optional `details` dict."""

    def __init__(self, message=None, details=None):
        super().__init__(detail=message or self.default_detail, code=self.default_code)
        self.details = details or {}


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "NOT_FOUND"
    default_detail = "The requested resource was not found."


class InsufficientStockError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "INSUFFICIENT_STOCK"
    default_detail = "Not enough stock available for this product."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "CONFLICT"
    default_detail = "The request conflicts with the current state of the resource."


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "BAD_REQUEST"
    default_detail = "The request is invalid."


def custom_exception_handler(exc, context):
    """Convert every exception into {"success": false, "error": {...}}."""
    # Translate Django/DB exceptions into APIExceptions so every branch below
    # can rely on `default_code` / `detail`.
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        exc = NotFoundError()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied()
    elif isinstance(exc, IntegrityError):
        logger.warning("IntegrityError in %s: %s", _view_name(context), exc)
        exc = ConflictError()

    # DRF builds the response for APIExceptions (and rolls back the
    # transaction). Anything else comes back as None.
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in %s", _view_name(context), exc_info=exc)
        set_rollback()
        return Response(
            error_body("INTERNAL_ERROR", "An unexpected error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        code = "VALIDATION_ERROR"
        message = "Invalid input."
        details = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
    elif isinstance(exc, Throttled):
        code = "TOO_MANY_REQUESTS"
        message = "Request was throttled."
        details = {"retry_after_seconds": exc.wait}
    else:
        code = str(exc.default_code).upper()
        message = str(exc.detail) if isinstance(exc.detail, str) else str(exc.default_detail)
        details = getattr(exc, "details", {})

    # Keep the response object so DRF-set headers (e.g. Retry-After) survive.
    response.data = error_body(code, message, details)
    return response


def _view_name(context):
    view = context.get("view")
    return view.__class__.__name__ if view else "unknown view"
