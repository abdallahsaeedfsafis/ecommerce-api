"""Cart business logic.

Stock rule: adding to a cart RESERVES stock immediately; removing or reducing
an item RETURNS it. Stock is only ever changed with conditional/atomic UPDATEs
using F() expressions, never "read in Python, then save".

Lock order is always cart -> (product / item), so two operations on the same
cart are serialized and can't deadlock each other.
"""

from django.db import transaction
from django.db.models import F, Prefetch
from django.utils import timezone

from core.exceptions import BadRequestError, ConflictError, InsufficientStockError, NotFoundError
from products.models import Product
from products.services import get_product_by_id

from .models import Cart, CartItem


@transaction.atomic
def add_to_cart(product_id, size, quantity, cart_id=None):
    cart = _lock_active_cart(cart_id) if cart_id else Cart.objects.create()

    product = get_product_by_id(product_id)
    if size not in product.sizes:
        raise BadRequestError(
            f"Size '{size}' is not available for this product.",
            details={"size": size, "available_sizes": product.sizes},
        )

    # Reserve stock in ONE conditional UPDATE: the row is only changed if enough
    # stock is left at the moment the UPDATE runs, so concurrent requests can't oversell.
    reserved = Product.objects.filter(pk=product.pk, stock_quantity__gte=quantity).update(
        stock_quantity=F("stock_quantity") - quantity,
        updated_at=timezone.now(),
    )
    if not reserved:
        available = Product.objects.filter(pk=product.pk).values_list("stock_quantity", flat=True).first()
        raise InsufficientStockError(details={"requested": quantity, "available": available})

    # The cart row is locked (or brand new), so nobody else can touch its items now.
    # An existing line keeps its original unit_price snapshot.
    updated = CartItem.objects.filter(cart=cart, product=product, size=size).update(
        quantity=F("quantity") + quantity,
        updated_at=timezone.now(),
    )
    if not updated:
        CartItem.objects.create(
            cart=cart,
            product=product,
            size=size,
            quantity=quantity,
            unit_price=product.price,
        )

    return _load_cart(cart.pk)


@transaction.atomic
def remove_from_cart(item_id, quantity=None):
    cart_id = CartItem.objects.filter(pk=item_id).values_list("cart_id", flat=True).first()
    if cart_id is None:
        raise NotFoundError("Cart item not found")

    # Lock the cart first (same order as add_to_cart), then the item.
    _lock_active_cart(cart_id)
    item = CartItem.objects.select_for_update().filter(pk=item_id).first()
    if item is None:  # Deleted by a concurrent request while we waited for the lock.
        raise NotFoundError("Cart item not found")

    if quantity is not None and quantity > item.quantity:
        raise BadRequestError(
            "Cannot remove more than the quantity in the cart.",
            details={"requested": quantity, "in_cart": item.quantity},
        )

    returned = item.quantity if quantity is None else quantity
    if returned == item.quantity:
        item.delete()
    else:
        CartItem.objects.filter(pk=item.pk).update(
            quantity=F("quantity") - returned,
            updated_at=timezone.now(),
        )

    Product.objects.filter(pk=item.product_id).update(
        stock_quantity=F("stock_quantity") + returned,
        updated_at=timezone.now(),
    )

    return _load_cart(cart_id)


def get_cart(cart_id):
    return _load_cart(cart_id)


def _lock_active_cart(cart_id):
    """SELECT ... FOR UPDATE on the cart; must be called inside a transaction."""
    cart = Cart.objects.select_for_update().filter(pk=cart_id).first()
    if cart is None:
        raise NotFoundError("Cart not found")
    if cart.status != Cart.Status.ACTIVE:
        raise ConflictError("Cart is not active.", details={"status": cart.status})
    return cart


def _load_cart(cart_id):
    """Cart with items and their products in 2 extra queries total (no N+1)."""
    items = CartItem.objects.select_related("product").order_by("created_at", "id")
    cart = Cart.objects.prefetch_related(Prefetch("items", queryset=items)).filter(pk=cart_id).first()
    if cart is None:
        raise NotFoundError("Cart not found")
    return cart
