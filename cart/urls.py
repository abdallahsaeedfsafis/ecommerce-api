from django.urls import path

from .views import CartResourceView, CartView

urlpatterns = [
    path("cart", CartView.as_view(), name="cart"),
    path("cart/<uuid:pk>", CartResourceView.as_view(), name="cart-resource"),
]
