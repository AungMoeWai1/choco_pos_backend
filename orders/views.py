from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema_view, extend_schema

from config.permissions import IsManagerOrAdmin
from products.models import Product, StockMovement
from customers.models import Customer, LoyaltyTransaction
from .models import Order, OrderItem, ReturnOrder, ReturnItem
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderUpdateSerializer,
    ReturnOrderSerializer,
    ReturnOrderCreateSerializer,
)

LOYALTY_POINTS_PER_UNIT = 1  # 1 point per currency unit spent


@extend_schema_view(
    list=extend_schema(summary="List orders"),
    retrieve=extend_schema(summary="Retrieve order"),
    create=extend_schema(summary="Create order"),
    update=extend_schema(summary="Update order"),
    destroy=extend_schema(summary="Delete/cancel order"),
)
class OrderViewSet(viewsets.ModelViewSet):
    queryset = (
        Order.objects.select_related("customer", "cashier", "store", "terminal", "shift")
        .prefetch_related("items__product")
        .all()
    )
    permission_classes = [IsAuthenticated]
    filterset_fields = ["payment_status", "order_status", "cashier", "store", "customer"]
    search_fields = ["order_number", "customer__full_name", "cashier__email"]
    ordering_fields = ["created_at", "grand_total"]

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "create":
            return OrderCreateSerializer
        if self.action in ("update", "partial_update"):
            return OrderUpdateSerializer
        return OrderDetailSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = None
        if data.get("customer_id"):
            try:
                customer = Customer.objects.get(pk=data["customer_id"])
            except Customer.DoesNotExist:
                return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        order = Order.objects.create(
            customer=customer,
            cashier=request.user,
            store=getattr(request.user, "store", None),
            discount_percent=data.get("discount_percent", 0),
            discount_amount=data.get("discount_amount", 0),
            notes=data.get("notes", ""),
            loyalty_points_redeemed=data.get("loyalty_points_redeemed", 0),
        )

        for item_data in data["items"]:
            product = Product.objects.select_for_update().get(pk=item_data["product_id"])
            if product.stock_quantity < item_data["quantity"]:
                raise serializers.ValidationError(
                    {"items": f"Insufficient stock for {product.name}."}
                )
            unit_price = item_data.get("unit_price") or product.selling_price
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                sku=product.sku,
                quantity=item_data["quantity"],
                unit_price=unit_price,
                cost_price=product.cost_price,
                tax_rate=product.tax_rate,
                discount_amount=item_data.get("discount_amount", 0),
            )
            # Deduct stock
            StockMovement.objects.create(
                product=product,
                movement_type=StockMovement.MovementType.OUT,
                quantity=item_data["quantity"],
                quantity_before=product.stock_quantity,
                quantity_after=product.stock_quantity - item_data["quantity"],
                reference=order.order_number,
                created_by=request.user,
            )
            product.stock_quantity -= item_data["quantity"]
            product.save(update_fields=["stock_quantity", "updated_at"])

        order.recalculate_totals()
        order.save()

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        order = self.get_object()
        if order.order_status != Order.OrderStatus.OPEN:
            return Response({"detail": "Only open orders can be suspended."}, status=400)
        order.order_status = Order.OrderStatus.SUSPENDED
        order.save(update_fields=["order_status"])
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        order = self.get_object()
        if order.order_status != Order.OrderStatus.SUSPENDED:
            return Response({"detail": "Order is not suspended."}, status=400)
        order.order_status = Order.OrderStatus.OPEN
        order.save(update_fields=["order_status"])
        return Response(OrderDetailSerializer(order).data)

    @action(detail=False, methods=["get"])
    def suspended(self, request):
        orders = Order.objects.filter(
            order_status=Order.OrderStatus.SUSPENDED,
            cashier=request.user,
        ).select_related("customer")
        return Response(OrderListSerializer(orders, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.order_status == Order.OrderStatus.COMPLETED:
            return Response({"detail": "Completed orders cannot be cancelled."}, status=400)
        with transaction.atomic():
            # Restore stock
            for item in order.items.select_related("product"):
                item.product.stock_quantity += item.quantity
                item.product.save(update_fields=["stock_quantity", "updated_at"])
            order.order_status = Order.OrderStatus.CANCELLED
            order.save(update_fields=["order_status"])
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def return_order(self, request, pk=None):
        order = self.get_object()
        if order.order_status != Order.OrderStatus.COMPLETED:
            return Response({"detail": "Only completed orders can be returned."}, status=400)
        serializer = ReturnOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            total_refund = 0
            return_obj = ReturnOrder.objects.create(
                original_order=order,
                cashier=request.user,
                reason=serializer.validated_data["reason"],
                refund_amount=0,
                notes=serializer.validated_data.get("notes", ""),
            )
            for item_data in serializer.validated_data["items"]:
                order_item = OrderItem.objects.get(pk=item_data["order_item_id"], order=order)
                qty = item_data["quantity"]
                refund = (order_item.unit_price * qty)
                ReturnItem.objects.create(
                    return_order=return_obj,
                    order_item=order_item,
                    quantity=qty,
                    refund_amount=refund,
                )
                total_refund += refund
                # Restore stock
                order_item.product.stock_quantity += qty
                order_item.product.save(update_fields=["stock_quantity", "updated_at"])

            return_obj.refund_amount = total_refund
            return_obj.status = ReturnOrder.ReturnStatus.APPROVED
            return_obj.processed_at = timezone.now()
            return_obj.save()

            order.order_status = Order.OrderStatus.RETURNED
            order.payment_status = Order.PaymentStatus.REFUNDED
            order.save(update_fields=["order_status", "payment_status"])

        return Response(ReturnOrderSerializer(return_obj).data, status=status.HTTP_201_CREATED)


class ReturnOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReturnOrder.objects.select_related("original_order", "cashier").prefetch_related("items").all()
    serializer_class = ReturnOrderSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["status", "cashier"]
    ordering_fields = ["created_at"]


# Fix missing import
import rest_framework.serializers as serializers
