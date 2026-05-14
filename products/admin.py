from django.contrib import admin
from .models import ProductType, Category, Product, StockMovement


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    search_fields = ["name"]
    list_filter = ["is_active"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "product_type", "sort_order", "is_active"]
    list_filter = ["product_type", "is_active"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "selling_price", "stock_quantity", "status"]
    list_filter = ["status", "category", "product_type"]
    search_fields = ["name", "sku", "barcode"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["product", "movement_type", "quantity", "quantity_before", "quantity_after", "created_at"]
    list_filter = ["movement_type"]
    search_fields = ["product__name"]
    readonly_fields = ["created_at"]
