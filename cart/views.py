from rest_framework import status
from rest_framework.views import APIView

from core.responses import success_response

from .serializers import AddToCartSerializer, CartSerializer, RemoveFromCartQuerySerializer
from .services import add_to_cart, get_cart, remove_from_cart


class CartView(APIView):
    """POST /api/cart — add a product to a cart (creates the cart if no cart_id)."""

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

    def get(self, request, pk):
        return success_response(CartSerializer(get_cart(pk)).data)

    def delete(self, request, pk):
        params = RemoveFromCartQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        cart = remove_from_cart(pk, quantity=params.validated_data.get("quantity"))
        return success_response(CartSerializer(cart).data)
