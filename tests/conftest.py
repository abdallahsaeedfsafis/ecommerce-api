from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from products.models import Category, Product

# key: (category slug, title, price, sizes, stock)
PRODUCT_DATA = {
    "tee": ("men", "Basic Tee", "10.00", ["S", "M", "L"], 10),
    "jeans": ("men", "Slim Jeans", "50.00", ["30", "32"], 5),
    "jacket": ("men", "Bomber Jacket", "120.00", ["M", "L"], 1),
    "dress": ("women", "Midi Dress", "60.00", ["S", "M"], 3),
    "coat": ("women", "Trench Coat", "150.00", ["M"], 0),
    "hoodie": ("kids", "Dino Hoodie", "25.00", ["6Y", "8Y"], 20),
}


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Throttle counters live in the cache; reset them so tests never hit 429."""
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def categories(db):
    return {
        slug: Category.objects.create(name=name, slug=slug)
        for slug, name in [("men", "Men"), ("women", "Women"), ("kids", "Kids")]
    }


@pytest.fixture
def products(categories):
    """Six products; created_at goes back one day per item, so dict order == newest first."""
    now = timezone.now()
    result = {}
    for i, (key, (category, title, price, sizes, stock)) in enumerate(PRODUCT_DATA.items()):
        product = Product.objects.create(
            category=categories[category],
            title=title,
            description=f"{title} description",
            price=Decimal(price),
            sizes=sizes,
            stock_quantity=stock,
        )
        # auto_now_add ignores passed values, so set deterministic timestamps afterwards.
        Product.objects.filter(pk=product.pk).update(created_at=now - timedelta(days=i))
        product.refresh_from_db()
        result[key] = product
    return result
