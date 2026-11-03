from rest_framework.response import Response


def success_response(data=None, status=200, meta=None):
    """Wrap a successful payload in the standard envelope."""
    body = {"success": True, "data": data}
    if meta is not None:
        body["meta"] = meta
    return Response(body, status=status)


def error_body(code, message, details=None):
    """Build the standard error envelope (shared by DRF and plain Django views)."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
