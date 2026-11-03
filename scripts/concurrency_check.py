"""Concurrency check for stock reservation.

Sets a product's stock to 5, then fires 20 concurrent add_to_cart(quantity=1)
calls, each on its own new cart. Expected: 5 succeed, 15 fail with 409, stock 0.
The product's original stock is restored and the test carts are deleted afterwards.

Usage:  python scripts/concurrency_check.py
"""

import os
import sys
import threading
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

from cart.models import Cart  # noqa: E402
from cart.services import add_to_cart  # noqa: E402
from core.exceptions import InsufficientStockError  # noqa: E402
from products.models import Product  # noqa: E402

INITIAL_STOCK = 5
THREADS = 20


def main():
    product = Product.objects.exclude(sizes=[]).order_by("title").first()
    if product is None:
        sys.exit("No products found. Run `python manage.py seed` first.")

    original_stock = product.stock_quantity
    size = product.sizes[0]
    Product.objects.filter(pk=product.pk).update(stock_quantity=INITIAL_STOCK)

    results = Counter()
    cart_ids = []
    lock = threading.Lock()
    start = threading.Barrier(THREADS)  # release all threads at the same moment

    def worker():
        try:
            start.wait()
            cart = add_to_cart(product.pk, size, 1)
            outcome = "succeeded"
            with lock:
                cart_ids.append(cart.pk)
        except InsufficientStockError:
            outcome = "failed_409"
        except Exception as exc:  # anything else is a bug worth seeing
            outcome = f"error: {type(exc).__name__}: {exc}"
        finally:
            connection.close()  # each thread has its own DB connection
        with lock:
            results[outcome] += 1

    print(f"Product:  {product.title} (size {size})")
    print(f"Stock set to {INITIAL_STOCK}; firing {THREADS} concurrent add_to_cart(quantity=1) calls...")

    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_stock = Product.objects.get(pk=product.pk).stock_quantity
    print()
    print(f"Succeeded:         {results.pop('succeeded', 0)}")
    print(f"Failed with 409:   {results.pop('failed_409', 0)}")
    for outcome, count in results.items():
        print(f"Unexpected ({count}): {outcome}")
    print(f"Final stock:       {final_stock}")
    print(f"Carts created:     {len(cart_ids)}")

    ok = len(cart_ids) == INITIAL_STOCK and final_stock == 0 and not results
    print()
    print("RESULT: PASS - no overselling" if ok else "RESULT: FAIL")

    # Clean up: CASCADE removes the items; then put the stock back.
    Cart.objects.filter(pk__in=cart_ids).delete()
    Product.objects.filter(pk=product.pk).update(stock_quantity=original_stock)
    print(f"Cleanup: deleted {len(cart_ids)} test carts, restored stock to {original_stock}.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
