from decimal import Decimal

from rest_framework import serializers

from products.models import Product

from .models import Cart, CartItem


class AddToCartSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="Existing active cart. Omit to create a new cart."
    )
    product_id = serializers.UUIDField()
    size = serializers.CharField(max_length=20, help_text="Must be one of the product's sizes.")
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)


class RemoveFromCartQuerySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1, required=False, help_text="Units to remove. Omit to remove the whole item."
    )


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "title"]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "size", "quantity", "unit_price", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "status", "items", "total_items", "total_price"]

    # Both use obj.items.all(), which hits the prefetch cache (no extra queries).
    def get_total_items(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj) -> str:
        total = sum((item.subtotal for item in obj.items.all()), Decimal("0"))
        # Returned as a string like DecimalField does, never as a float.
        return str(total.quantize(Decimal("0.01")))
