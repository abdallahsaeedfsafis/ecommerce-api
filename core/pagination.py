from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """?page=1&limit=10 (max 100), wrapped in the standard success envelope."""

    page_query_param = "page"
    page_size_query_param = "limit"
    page_size = 10
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": data,
            "meta": {
                "page": self.page.number,
                "limit": self.page.paginator.per_page,
                "total": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
            },
        })

    def get_paginated_response_schema(self, schema):
        """OpenAPI shape of get_paginated_response (used by drf-spectacular)."""
        integer = {"type": "integer"}
        return {
            "type": "object",
            "required": ["success", "data", "meta"],
            "properties": {
                "success": {"type": "boolean", "example": True},
                "data": schema,
                "meta": {
                    "type": "object",
                    "required": ["page", "limit", "total", "total_pages"],
                    "properties": {
                        "page": {**integer, "example": 1},
                        "limit": {**integer, "example": 10},
                        "total": {**integer, "example": 20},
                        "total_pages": {**integer, "example": 2},
                    },
                },
            },
        }
