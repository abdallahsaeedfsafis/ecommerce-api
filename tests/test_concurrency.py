import threading

import pytest
from django.db import connection

from cart.models import Cart
from cart.services import add_to_cart
from core.exceptions import InsufficientStockError
from products.models import Category, Product

THREADS = 20
STOCK = 5


@pytest.mark.django_db(transaction=True)
def test_concurrent_add_to_cart_never_oversells():
    category = Category.objects.create(name="Men", slug="men")
    product = Product.objects.create(
        category=category, title="Limited Tee", price="10.00", sizes=["M"], stock_quantity=STOCK
    )

    succeeded, insufficient, unexpected = [], [], []
    lock = threading.Lock()
    start = threading.Barrier(THREADS)  # release every thread at the same moment

    def worker():
        try:
            start.wait()
            cart = add_to_cart(product.id, "M", 1)
            with lock:
                succeeded.append(cart.id)
        except InsufficientStockError:
            with lock:
                insufficient.append(1)
        except Exception as exc:
            with lock:
                unexpected.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    product.refresh_from_db()
    assert unexpected == []
    assert len(succeeded) == STOCK
    assert len(insufficient) == THREADS - STOCK
    assert product.stock_quantity == 0
    # Failed calls rolled back the cart they had created: no orphans.
    assert Cart.objects.count() == STOCK
    assert set(Cart.objects.values_list("id", flat=True)) == set(succeeded)
