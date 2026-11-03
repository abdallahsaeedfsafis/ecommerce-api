from core.exceptions import NotFoundError

from .models import Product

SORT_ORDERING = {
    "price_asc": ["price"],
    "price_desc": ["-price"],
    "newest": ["-created_at"],
    "oldest": ["created_at"],
}


def get_products(filters):
    """Return products matching already-validated filters, in a stable order."""
    queryset = Product.objects.select_related("category")

    if filters.get("category"):
        queryset = queryset.filter(category__slug=filters["category"])
    if filters.get("min_price") is not None:
        queryset = queryset.filter(price__gte=filters["min_price"])
    if filters.get("max_price") is not None:
        queryset = queryset.filter(price__lte=filters["max_price"])

    ordering = SORT_ORDERING[filters.get("sort", "newest")]
    # "id" breaks ties (equal price / created_at) so pages never overlap or skip rows.
    return queryset.order_by(*ordering, "id")


def get_product_by_id(product_id):
    try:
        return Product.objects.select_related("category").get(pk=product_id)
    except Product.DoesNotExist:
        raise NotFoundError("Product not found")
