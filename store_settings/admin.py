from django.contrib import admin
from .models import Store, Terminal, Shift


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "phone", "currency", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ["name", "terminal_id", "store", "is_active"]
    list_filter = ["store", "is_active"]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["pk", "cashier", "terminal", "status", "opening_cash", "closing_cash", "opened_at"]
    list_filter = ["status"]
    search_fields = ["cashier__email"]
