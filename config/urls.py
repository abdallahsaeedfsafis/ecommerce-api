from django.contrib import admin
from django.urls import include, path, re_path

from core.views import health_check, not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health_check),
    path("api/", include("products.urls")),
    path("api/", include("cart.urls")),
    # Must stay last: unknown routes return JSON even when DEBUG=True
    # (Django ignores handler404 in DEBUG mode).
    re_path(r"^.*$", not_found),
]

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"
