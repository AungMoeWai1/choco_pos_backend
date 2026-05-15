from django.contrib import admin
from .models import Order, OrderItem, ReturnOrder, ReturnItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["line_total"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "customer", "cashier", "grand_total", "payment_status", "order_status", "created_at"]
    list_filter = ["payment_status", "order_status", "created_at"]
    search_fields = ["order_number", "customer__full_name", "cashier__email"]
    readonly_fields = ["order_number", "subtotal", "tax_amount", "grand_total", "created_at", "updated_at"]
    inlines = [OrderItemInline]


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


@admin.register(ReturnOrder)
class ReturnOrderAdmin(admin.ModelAdmin):
    list_display = ["pk", "original_order", "cashier", "refund_amount", "status", "created_at"]
    list_filter = ["status"]
    inlines = [ReturnItemInline]
