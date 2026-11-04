from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from core.responses import success_response
from core.schema import envelope, error_example, error_response

from .serializers import AddToCartSerializer, CartSerializer, RemoveFromCartQuerySerializer
from .services import add_to_cart, get_cart, remove_from_cart

CART_RESPONSE = envelope("CartResponse", CartSerializer())

EXAMPLE_CART = {
    "success": True,
    "data": {
        "id": "61005ec1-ae3c-4df2-95ca-138645482cb0",
        "status": "active",
        "items": [
            {
                "id": "78dec8ec-3526-4a6f-b337-a31ef48bdb54",
                "product": {"id": "77ed3f4a-d5ca-4504-8b43-7ef0a312073b", "title": "Floral Midi Dress"},
                "size": "M",
                "quantity": 2,
                "unit_price": "59.99",
                "subtotal": "119.98",
            }
        ],
        "total_items": 2,
        "total_price": "119.98",
    },
}

CART_NOT_FOUND = error_example("Cart not found", "NOT_FOUND", "Cart not found")
CART_NOT_ACTIVE = error_example("Cart not active", "CONFLICT", "Cart is not active.", {"status": "checked_out"})


class CartView(APIView):
    """POST /api/cart — add a product to a cart (creates the cart if no cart_id)."""

    @extend_schema(
        tags=["Cart"],
        summary="Add a product to a cart",
        description=(
            "Reserves stock immediately. Omit `cart_id` to create a new cart. "
            "Adding the same product and size again increases the quantity."
        ),
        request=AddToCartSerializer,
        responses={
            201: CART_RESPONSE,
            400: error_response(
                "Invalid body (`VALIDATION_ERROR`) or size not offered (`BAD_REQUEST`).",
                error_example(
                    "Invalid size",
                    "BAD_REQUEST",
                    "Size 'XXL' is not available for this product.",
                    {"size": "XXL", "available_sizes": ["XS", "S", "M", "L"]},
                ),
                error_example(
                    "Invalid quantity",
                    "VALIDATION_ERROR",
                    "Invalid input.",
                    {"quantity": ["Ensure this value is less than or equal to 100."]},
                ),
            ),
            404: error_response(
                "Product or cart does not exist (`NOT_FOUND`).",
                error_example("Product not found", "NOT_FOUND", "Product not found"),
                CART_NOT_FOUND,
            ),
            409: error_response(
                "Not enough stock (`INSUFFICIENT_STOCK`) or cart not active (`CONFLICT`).",
                error_example(
                    "Insufficient stock",
                    "INSUFFICIENT_STOCK",
                    "Not enough stock available for this product.",
                    {"requested": 2, "available": 1},
                ),
                CART_NOT_ACTIVE,
            ),
        },
        examples=[
            OpenApiExample(
                "New cart",
                value={"product_id": "77ed3f4a-d5ca-4504-8b43-7ef0a312073b", "size": "M", "quantity": 2},
                request_only=True,
            ),
            OpenApiExample(
                "Existing cart",
                value={
                    "cart_id": "61005ec1-ae3c-4df2-95ca-138645482cb0",
                    "product_id": "77ed3f4a-d5ca-4504-8b43-7ef0a312073b",
                    "size": "M",
                    "quantity": 1,
                },
                request_only=True,
            ),
            OpenApiExample("Cart", value=EXAMPLE_CART, response_only=True, status_codes=["201"]),
        ],
    )
    def post(self, request):
        payload = AddToCartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cart = add_to_cart(**payload.validated_data)
        return success_response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartResourceView(APIView):
    """/api/cart/<uuid:pk> — one URL, two meanings depending on the method.

    GET    -> `pk` is a CART id: return that cart.
    DELETE -> `pk` is a CART ITEM id: remove the item (or `?quantity=N` of it),
              return its stock, and respond with the updated cart.

    Both endpoints share the same URL pattern, so Django can only route it to
    one view; this view dispatches on the HTTP method instead.
    """

    @extend_schema(
        tags=["Cart"],
        summary="Get a cart",
        # drf-spectacular documents the `pk` path segment as `id`.
        parameters=[OpenApiParameter("id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Cart id.")],
        responses={
            200: CART_RESPONSE,
            404: error_response("Cart does not exist (`NOT_FOUND`).", CART_NOT_FOUND),
        },
        examples=[OpenApiExample("Cart", value=EXAMPLE_CART, response_only=True, status_codes=["200"])],
    )
    def get(self, request, pk):
        return success_response(CartSerializer(get_cart(pk)).data)

    @extend_schema(
        tags=["Cart"],
        summary="Remove a cart item (or part of it)",
        description=(
            "`id` is a **cart item** id (not a cart id). Without `quantity` the whole item is removed; "
            "with `quantity` only that many units are removed. Removed units go back to stock."
        ),
        parameters=[
            OpenApiParameter("id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Cart item id."),
            RemoveFromCartQuerySerializer,
        ],
        responses={
            200: CART_RESPONSE,
            400: error_response(
                "Invalid quantity (`VALIDATION_ERROR`) or more than in the cart (`BAD_REQUEST`).",
                error_example(
                    "More than in cart",
                    "BAD_REQUEST",
                    "Cannot remove more than the quantity in the cart.",
                    {"requested": 5, "in_cart": 3},
                ),
            ),
            404: error_response(
                "Cart item does not exist (`NOT_FOUND`).",
                error_example("Cart item not found", "NOT_FOUND", "Cart item not found"),
            ),
            409: error_response("Cart is not active (`CONFLICT`).", CART_NOT_ACTIVE),
        },
        examples=[OpenApiExample("Updated cart", value=EXAMPLE_CART, response_only=True, status_codes=["200"])],
    )
    def delete(self, request, pk):
        params = RemoveFromCartQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        cart = remove_from_cart(pk, quantity=params.validated_data.get("quantity"))
        return success_response(CartSerializer(cart).data)
