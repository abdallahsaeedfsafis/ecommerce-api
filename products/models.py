import uuid
from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    sizes = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["price"], name="products_price_idx"),
            models.Index(fields=["created_at"], name="products_created_at_idx"),
            models.Index(fields=["category", "price"], name="products_category_price_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="products_stock_quantity_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="products_price_gte_0",
            ),
        ]

    def __str__(self):
        return self.title
