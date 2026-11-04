from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.views import APIView

from core.pagination import StandardPagination
from core.responses import success_response
from core.schema import envelope, error_example, error_response

from .serializers import ProductDetailSerializer, ProductListSerializer, ProductQuerySerializer
from .services import get_product_by_id, get_products

EXAMPLE_CATEGORY = {"id": "cb243b5c-19cd-4f99-999f-85bc5ea2c28c", "name": "Men", "slug": "men"}
EXAMPLE_PRODUCT = {
    "id": "cdb50eb8-3e40-4716-91e4-f73d7e81212f",
    "title": "Basic Crew Neck T-Shirt",
    "price": "12.50",
    "category": EXAMPLE_CATEGORY,
    "sizes": ["S", "M", "L", "XL", "XXL"],
    "stock_quantity": 120,
    "in_stock": True,
}


@extend_schema_view(
    get=extend_schema(
        tags=["Products"],
        summary="List products",
        description=(
            "Paginated product list. Filter by `category` (slug) and price range, "
            "sort with `sort`. An unknown category returns an empty list."
        ),
        parameters=[ProductQuerySerializer],
        responses={
            200: ProductListSerializer(many=True),
            400: error_response(
                "Invalid query parameters (`VALIDATION_ERROR`).",
                error_example(
                    "min_price greater than max_price",
                    "VALIDATION_ERROR",
                    "Invalid input.",
                    {"min_price": ["min_price must be less than or equal to max_price."]},
                ),
                error_example(
                    "Unknown sort option",
                    "VALIDATION_ERROR",
                    "Invalid input.",
                    {"sort": ['"cheapest" is not a valid choice.']},
                ),
            ),
            404: error_response(
                "Page out of range (`NOT_FOUND`).",
                error_example("Invalid page", "NOT_FOUND", "Invalid page."),
            ),
        },
        examples=[
            OpenApiExample(
                "Men, cheapest first",
                value={
                    "success": True,
                    "data": [EXAMPLE_PRODUCT],
                    "meta": {"page": 1, "limit": 1, "total": 7, "total_pages": 7},
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    ),
)
class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = ProductQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return get_products(params.validated_data)


class ProductDetailView(APIView):
    @extend_schema(
        tags=["Products"],
        summary="Get a product",
        responses={
            200: envelope("ProductDetailResponse", ProductDetailSerializer()),
            404: error_response(
                "Product does not exist (`NOT_FOUND`).",
                error_example("Product not found", "NOT_FOUND", "Product not found"),
            ),
        },
        examples=[
            OpenApiExample(
                "Product",
                value={
                    "success": True,
                    "data": {
                        **EXAMPLE_PRODUCT,
                        "description": "Everyday 100% cotton tee.",
                        "created_at": "2026-11-03T00:11:10.716512Z",
                        "updated_at": "2026-11-03T00:11:10.716512Z",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request, product_id):
        product = get_product_by_id(product_id)
        return success_response(ProductDetailSerializer(product).data)
