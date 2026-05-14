from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from drf_spectacular.utils import extend_schema

from config.permissions import IsManagerOrAdmin
from orders.models import Order
from customers.models import LoyaltyTransaction
from .models import Payment, Refund
from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    RefundSerializer,
    RefundCreateSerializer,
)

LOYALTY_POINTS_RATE = 1  # 1 point per 1000 currency unit


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order", "processed_by").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["payment_method", "status", "order"]
    search_fields = ["transaction_id", "order__order_number"]
    ordering_fields = ["payment_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()

    @extend_schema(summary="Process payment for an order (supports split payment)")
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.select_for_update().get(pk=serializer.validated_data["order_id"])
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response({"detail": "Order already paid."}, status=status.HTTP_400_BAD_REQUEST)

        total_paid = Decimal("0")
        created_payments = []

        for pdata in serializer.validated_data["payments"]:
            paid = Decimal(str(pdata["paid_amount"]))
            payment = Payment.objects.create(
                order=order,
                payment_method=pdata["payment_method"],
                paid_amount=paid,
                transaction_id=pdata.get("transaction_id", ""),
                reference_number=pdata.get("reference_number", ""),
                status=Payment.Status.COMPLETED,
                processed_by=request.user,
                notes=pdata.get("notes", ""),
            )
            created_payments.append(payment)
            total_paid += paid

        order.paid_amount = (order.paid_amount or 0) + total_paid
        order.change_amount = max(order.paid_amount - order.grand_total, Decimal("0"))

        if order.paid_amount >= order.grand_total:
            order.payment_status = Order.PaymentStatus.PAID
            order.order_status = Order.OrderStatus.COMPLETED
            # Award loyalty points
            if order.customer:
                points_earned = int(order.grand_total / 1000)
                if points_earned > 0:
                    order.customer.loyalty_points += points_earned
                    order.customer.save(update_fields=["loyalty_points"])
                    LoyaltyTransaction.objects.create(
                        customer=order.customer,
                        transaction_type=LoyaltyTransaction.TransactionType.EARN,
                        points=points_earned,
                        balance_after=order.customer.loyalty_points,
                        reference=order.order_number,
                        description=f"Points earned from order {order.order_number}",
                        created_by=request.user,
                    )
                    order.loyalty_points_earned = points_earned
        else:
            order.payment_status = Order.PaymentStatus.PARTIAL

        order.save()
        return Response(
            PaymentSerializer(created_payments, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.select_related("payment", "processed_by").all()
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["payment"]
    ordering_fields = ["created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return RefundCreateSerializer
        return RefundSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = Payment.objects.select_for_update().get(pk=serializer.validated_data["payment_id"])
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        refund_amount = serializer.validated_data["amount"]
        if refund_amount > payment.paid_amount:
            return Response({"detail": "Refund exceeds paid amount."}, status=status.HTTP_400_BAD_REQUEST)

        refund = Refund.objects.create(
            payment=payment,
            amount=refund_amount,
            reason=serializer.validated_data["reason"],
            transaction_id=serializer.validated_data.get("transaction_id", ""),
            processed_by=request.user,
        )
        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status"])

        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)
