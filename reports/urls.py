from django.urls import path
from .views import (
    DashboardSummaryView,
    SalesReportView,
    TopProductsView,
    TopCustomersView,
    PaymentMethodBreakdownView,
    CashDrawerSummaryView,
    InventoryReportView,
)

urlpatterns = [
    path("reports/dashboard/", DashboardSummaryView.as_view(), name="report-dashboard"),
    path("reports/sales/", SalesReportView.as_view(), name="report-sales"),
    path("reports/top-products/", TopProductsView.as_view(), name="report-top-products"),
    path("reports/top-customers/", TopCustomersView.as_view(), name="report-top-customers"),
    path("reports/payment-methods/", PaymentMethodBreakdownView.as_view(), name="report-payment-methods"),
    path("reports/cash-drawer/", CashDrawerSummaryView.as_view(), name="report-cash-drawer"),
    path("reports/inventory/", InventoryReportView.as_view(), name="report-inventory"),
]
