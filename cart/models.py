import uuid

from django.db import models
from django.db.models import Q


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CHECKED_OUT = "checked_out", "Checked out"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart {self.id} ({self.status})"


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    size = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    # Price snapshot taken when the item is added, so later price
    # changes on the product don't silently change the cart total.
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "size"],
                name="cart_items_unique_cart_product_size",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="cart_items_quantity_gt_0",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_id} ({self.size})"

    @property
    def subtotal(self):
        if self.unit_price is None or self.quantity is None:
            return None
        return self.unit_price * self.quantity
