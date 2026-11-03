from decimal import Decimal

from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "title", "price", "category", "sizes", "stock_quantity", "in_stock"]

    def get_in_stock(self, obj) -> bool:
        return obj.stock_quantity > 0


class ProductDetailSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["description", "created_at", "updated_at"]


class ProductQuerySerializer(serializers.Serializer):
    """Validates the query params of GET /api/products."""

    SORT_CHOICES = ["price_asc", "price_desc", "newest", "oldest"]

    category = serializers.SlugField(required=False)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False
    )
    sort = serializers.ChoiceField(choices=SORT_CHOICES, default="newest")
    # Only validated here; StandardPagination reads them and caps `limit`.
    page = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError(
                {"min_price": ["min_price must be less than or equal to max_price."]}
            )
        return attrs
