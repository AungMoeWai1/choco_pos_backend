from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductTypeViewSet, CategoryViewSet, ProductViewSet, StockMovementViewSet

router = DefaultRouter()
router.register("product-types", ProductTypeViewSet, basename="product-type")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = [path("", include(router.urls))]
