from django.contrib import admin
from .models import Customer, LoyaltyTransaction


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "email", "loyalty_points", "is_active", "created_at"]
    search_fields = ["full_name", "phone", "email"]
    list_filter = ["is_active"]
    ordering = ["full_name"]


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ["customer", "transaction_type", "points", "balance_after", "created_at"]
    list_filter = ["transaction_type"]
    search_fields = ["customer__full_name"]
    readonly_fields = ["created_at"]
