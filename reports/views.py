from datetime import date, timedelta
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import (
    Sum, Count, Avg, F, Q,
    ExpressionWrapper, DecimalField, IntegerField,
)
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers as drf_serializers

from config.permissions import IsManagerOrAdmin
from orders.models import Order, OrderItem
from products.models import Product
from customers.models import Customer
from payments.models import Payment


def _date_range(request):
    today = date.today()
    start_str = request.query_params.get("start_date")
    end_str = request.query_params.get("end_date")
    try:
        start = date.fromisoformat(start_str) if start_str else today - timedelta(days=29)
        end = date.fromisoformat(end_str) if end_str else today
    except ValueError:
        start, end = today - timedelta(days=29), today
    return start, end


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Dashboard KPI summary",
        responses={200: inline_serializer("DashboardSummary", fields={
            "today": drf_serializers.DictField(),
            "this_month": drf_serializers.DictField(),
            "total_customers": drf_serializers.IntegerField(),
            "low_stock_products": drf_serializers.IntegerField(),
        })},
    )
    def get(self, request):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)

        base_qs = Order.objects.filter(payment_status=Order.PaymentStatus.PAID)

        today_sales = base_qs.filter(created_at__date=today).aggregate(
            revenue=Sum("grand_total"), orders=Count("id")
        )
        month_sales = base_qs.filter(created_at__date__gte=start_of_month).aggregate(
            revenue=Sum("grand_total"), orders=Count("id")
        )
        total_customers = Customer.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity__lte=F("reorder_level"),
        ).count()

        return Response(
            {
                "today": {
                    "revenue": today_sales["revenue"] or 0,
                    "orders": today_sales["orders"] or 0,
                },
                "this_month": {
                    "revenue": month_sales["revenue"] or 0,
                    "orders": month_sales["orders"] or 0,
                },
                "total_customers": total_customers,
                "low_stock_products": low_stock_count,
            }
        )


class SalesReportView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        responses={200: inline_serializer("SalesReport", fields={"results": drf_serializers.ListField()})},
        summary="Daily / weekly / monthly sales report",
        parameters=[
            OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("group_by", str, description="day | week | month (default: day)"),
        ],
    )
    def get(self, request):
        start, end = _date_range(request)
        group_by = request.query_params.get("group_by", "day")

        trunc_fn = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}.get(group_by, TruncDate)

        data = (
            Order.objects.filter(
                payment_status=Order.PaymentStatus.PAID,
                created_at__date__gte=start,
                created_at__date__lte=end,
            )
            .annotate(period=trunc_fn("created_at"))
            .values("period")
            .annotate(
                revenue=Sum("grand_total"),
                orders=Count("id"),
                avg_order_value=Avg("grand_total"),
                discount_total=Sum("discount_amount"),
                tax_total=Sum("tax_amount"),
            )
            .order_by("period")
        )

        return Response(list(data))


class TopProductsView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Best selling products by quantity and revenue",
        responses={200: inline_serializer("TopProducts", fields={"results": drf_serializers.ListField()})},
    )
    def get(self, request):
        start, end = _date_range(request)
        limit = int(request.query_params.get("limit", 10))

        data = (
            OrderItem.objects.filter(
                order__payment_status=Order.PaymentStatus.PAID,
                order__created_at__date__gte=start,
                order__created_at__date__lte=end,
            )
            .values("product_id", "product_name", "sku")
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum("line_total"),
                total_profit=Sum(
                    ExpressionWrapper(
                        (F("unit_price") - F("cost_price")) * F("quantity"),
                        output_field=DecimalField(),
                    )
                ),
            )
            .order_by("-total_revenue")[:limit]
        )
        return Response(list(data))


class TopCustomersView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Top customers by spend",
        responses={200: inline_serializer("TopCustomers", fields={"results": drf_serializers.ListField()})},
    )
    def get(self, request):
        start, end = _date_range(request)
        limit = int(request.query_params.get("limit", 10))

        data = (
            Order.objects.filter(
                payment_status=Order.PaymentStatus.PAID,
                customer__isnull=False,
                created_at__date__gte=start,
                created_at__date__lte=end,
            )
            .values("customer_id", "customer__full_name", "customer__phone")
            .annotate(
                total_spent=Sum("grand_total"),
                total_orders=Count("id"),
            )
            .order_by("-total_spent")[:limit]
        )
        return Response(list(data))


class PaymentMethodBreakdownView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Payment method breakdown",
        responses={200: inline_serializer("PaymentBreakdown", fields={"results": drf_serializers.ListField()})},
    )
    def get(self, request):
        start, end = _date_range(request)

        data = (
            Payment.objects.filter(
                status=Payment.Status.COMPLETED,
                payment_date__date__gte=start,
                payment_date__date__lte=end,
            )
            .values("payment_method")
            .annotate(
                total_amount=Sum("paid_amount"),
                transaction_count=Count("id"),
            )
            .order_by("-total_amount")
        )
        return Response(list(data))


class CashDrawerSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Cash drawer summary for a shift or date",
        responses={200: inline_serializer("CashDrawer", fields={
            "total_cash_in": drf_serializers.DecimalField(max_digits=12, decimal_places=2),
            "total_change": drf_serializers.DecimalField(max_digits=12, decimal_places=2),
            "transaction_count": drf_serializers.IntegerField(),
            "net_cash": drf_serializers.DecimalField(max_digits=12, decimal_places=2),
        })},
    )
    def get(self, request):
        shift_id = request.query_params.get("shift_id")
        target_date = request.query_params.get("date", date.today().isoformat())

        qs = Payment.objects.filter(
            status=Payment.Status.COMPLETED,
            payment_method=Payment.Method.CASH,
        )

        if shift_id:
            qs = qs.filter(order__shift_id=shift_id)
        else:
            qs = qs.filter(payment_date__date=target_date)

        agg = qs.aggregate(
            total_cash_in=Sum("paid_amount"),
            total_change=Sum("change_amount"),
            transaction_count=Count("id"),
        )
        net_cash = (agg["total_cash_in"] or 0) - (agg["total_change"] or 0)
        return Response({**agg, "net_cash": net_cash})


class InventoryReportView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    @extend_schema(
        summary="Current inventory status",
        responses={200: inline_serializer("InventoryReport", fields={
            "total_products": drf_serializers.IntegerField(),
            "low_stock_count": drf_serializers.IntegerField(),
            "total_stock_value": drf_serializers.DecimalField(max_digits=14, decimal_places=2),
            "low_stock_products": drf_serializers.ListField(),
            "all_products": drf_serializers.ListField(),
        })},
    )
    def get(self, request):
        products = (
            Product.objects.select_related("category", "product_type")
            .filter(status=Product.Status.ACTIVE)
            .annotate(
                stock_value=ExpressionWrapper(
                    F("stock_quantity") * F("cost_price"),
                    output_field=DecimalField(),
                )
            )
            .values(
                "id", "name", "sku", "category__name",
                "stock_quantity", "reorder_level",
                "cost_price", "selling_price", "stock_value",
            )
            .order_by("stock_quantity")
        )
        low_stock = [p for p in products if p["stock_quantity"] <= p["reorder_level"]]
        total_value = sum(p["stock_value"] or 0 for p in products)

        return Response(
            {
                "total_products": len(products),
                "low_stock_count": len(low_stock),
                "total_stock_value": total_value,
                "low_stock_products": low_stock,
                "all_products": list(products),
            }
        )
