from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Application routes
    path(API_V1, include("accounts.urls")),
    path(API_V1, include("customers.urls")),
    path(API_V1, include("products.urls")),
    path(API_V1, include("orders.urls")),
    path(API_V1, include("payments.urls")),
    path(API_V1, include("reports.urls")),
    path(API_V1, include("store_settings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
