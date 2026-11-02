from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = ("subtotal",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "updated_at")
    list_filter = ("status",)
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "size", "quantity", "unit_price")
    raw_id_fields = ("cart", "product")
    list_select_related = ("product",)
