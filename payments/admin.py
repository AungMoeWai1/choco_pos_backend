from django.contrib import admin
from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["pk", "order", "payment_method", "paid_amount", "status", "payment_date"]
    list_filter = ["payment_method", "status", "payment_date"]
    search_fields = ["order__order_number", "transaction_id"]
    readonly_fields = ["payment_date"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["pk", "payment", "amount", "created_at"]
    search_fields = ["payment__order__order_number"]
    readonly_fields = ["created_at"]
