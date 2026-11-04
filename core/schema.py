"""OpenAPI helpers (documentation only — no runtime behaviour).

They describe the response envelopes produced by core.responses and
core.exceptions so Swagger shows the real shapes.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, inline_serializer
from rest_framework import serializers

from .responses import error_body


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="Machine-readable error code, e.g. NOT_FOUND.")
    message = serializers.CharField(help_text="Human-readable message.")
    details = serializers.DictField(help_text="Extra context (field errors, stock numbers, ...).")


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    error = ErrorSerializer()


def envelope(name, data_serializer):
    """Schema for {"success": true, "data": <data_serializer>}. Create once per name."""
    return inline_serializer(
        name=name,
        fields={"success": serializers.BooleanField(default=True), "data": data_serializer},
    )


def error_example(name, code, message, details=None):
    return OpenApiExample(name, value=error_body(code, message, details), response_only=True)


def error_response(description, *examples):
    return OpenApiResponse(response=ErrorResponseSerializer, description=description, examples=list(examples))
