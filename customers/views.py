from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from drf_spectacular.utils import extend_schema_view, extend_schema

from config.permissions import IsManagerOrAdmin
from .models import Customer, LoyaltyTransaction
from .serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerCreateUpdateSerializer,
    LoyaltyTransactionSerializer,
    LoyaltyAdjustSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List customers"),
    create=extend_schema(summary="Create customer"),
    retrieve=extend_schema(summary="Retrieve customer"),
    update=extend_schema(summary="Update customer"),
    partial_update=extend_schema(summary="Partial update customer"),
    destroy=extend_schema(summary="Delete customer"),
)
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["full_name", "phone", "email"]
    ordering_fields = ["full_name", "loyalty_points", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CustomerCreateUpdateSerializer
        return CustomerDetailSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def purchase_history(self, request, pk=None):
        customer = self.get_object()
        orders = customer.orders.select_related("cashier").prefetch_related("items__product").order_by("-created_at")
        from orders.serializers import OrderListSerializer
        page = self.paginate_queryset(orders)
        if page is not None:
            return self.get_paginated_response(OrderListSerializer(page, many=True).data)
        return Response(OrderListSerializer(orders, many=True).data)

    @action(detail=True, methods=["get"])
    def loyalty_history(self, request, pk=None):
        customer = self.get_object()
        transactions = customer.loyalty_transactions.select_related("created_by").all()
        page = self.paginate_queryset(transactions)
        if page is not None:
            return self.get_paginated_response(LoyaltyTransactionSerializer(page, many=True).data)
        return Response(LoyaltyTransactionSerializer(transactions, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def adjust_loyalty(self, request, pk=None):
        customer = self.get_object()
        serializer = LoyaltyAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        points = serializer.validated_data["points"]
        description = serializer.validated_data.get("description", "Manual adjustment")

        with transaction.atomic():
            customer.loyalty_points += points
            if customer.loyalty_points < 0:
                return Response(
                    {"detail": "Insufficient loyalty points."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            customer.save(update_fields=["loyalty_points"])
            tx_type = LoyaltyTransaction.TransactionType.EARN if points > 0 else LoyaltyTransaction.TransactionType.REDEEM
            LoyaltyTransaction.objects.create(
                customer=customer,
                transaction_type=tx_type if points != 0 else LoyaltyTransaction.TransactionType.ADJUST,
                points=points,
                balance_after=customer.loyalty_points,
                description=description,
                created_by=request.user,
            )
        return Response(CustomerDetailSerializer(customer).data)


class LoyaltyTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoyaltyTransaction.objects.select_related("customer", "created_by").all()
    serializer_class = LoyaltyTransactionSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["customer", "transaction_type"]
    ordering_fields = ["created_at"]
