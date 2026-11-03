import logging

from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .responses import error_body, success_response

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health_check(request):
    """Check that the API and the database are reachable."""
    try:
        connection.ensure_connection()
    except Exception:
        logger.exception("Health check: database unavailable")
        return Response(
            error_body("SERVICE_UNAVAILABLE", "Database is unavailable."),
            status=503,
        )
    return success_response({"status": "ok", "database": "connected"})


def not_found(request, exception=None):
    """JSON 404 for unknown routes (used as handler404 and as the catch-all route)."""
    return JsonResponse(
        error_body("NOT_FOUND", f"Route '{request.path}' was not found."),
        status=404,
    )


def server_error(request):
    """JSON 500 for errors raised outside DRF views (DRF ones use the exception handler)."""
    return JsonResponse(
        error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        status=500,
    )
