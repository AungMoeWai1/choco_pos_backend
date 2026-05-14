from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import F
from drf_spectacular.utils import extend_schema_view, extend_schema

from config.permissions import IsManagerOrAdmin
from .models import ProductType, Category, Product, StockMovement
from .serializers import (
    ProductTypeSerializer,
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    StockMovementSerializer,
    StockAdjustSerializer,
)


class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related("product_type").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active", "product_type"]
    search_fields = ["name"]
    ordering_fields = ["sort_order", "name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()


@extend_schema_view(
    list=extend_schema(summary="List products"),
    retrieve=extend_schema(summary="Retrieve product"),
    create=extend_schema(summary="Create product"),
    update=extend_schema(summary="Update product"),
    destroy=extend_schema(summary="Delete product"),
)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "product_type", "store").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "category", "product_type", "store"]
    search_fields = ["name", "sku", "barcode", "description"]
    ordering_fields = ["name", "selling_price", "stock_quantity", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        products = Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity__lte=F("reorder_level"),
        )
        page = self.paginate_queryset(products)
        if page is not None:
            return self.get_paginated_response(ProductListSerializer(page, many=True).data)
        return Response(ProductListSerializer(products, many=True).data)

    @action(detail=False, methods=["get"])
    def by_barcode(self, request):
        barcode = request.query_params.get("barcode")
        if not barcode:
            return Response({"detail": "barcode query param required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.select_related("category", "product_type").get(barcode=barcode)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def adjust_stock(self, request, pk=None):
        product = self.get_object()
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qty = serializer.validated_data["quantity"]
        movement_type = serializer.validated_data["movement_type"]

        with transaction.atomic():
            qty_before = product.stock_quantity
            if movement_type in (StockMovement.MovementType.OUT, StockMovement.MovementType.DAMAGE):
                if product.stock_quantity < qty:
                    return Response(
                        {"detail": "Insufficient stock."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                product.stock_quantity -= qty
            else:
                product.stock_quantity += qty

            product.save(update_fields=["stock_quantity", "updated_at"])
            StockMovement.objects.create(
                product=product,
                movement_type=movement_type,
                quantity=qty,
                quantity_before=qty_before,
                quantity_after=product.stock_quantity,
                notes=serializer.validated_data.get("notes", ""),
                reference=serializer.validated_data.get("reference", ""),
                created_by=request.user,
            )
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["get"])
    def stock_history(self, request, pk=None):
        product = self.get_object()
        movements = product.stock_movements.select_related("created_by").all()
        page = self.paginate_queryset(movements)
        if page is not None:
            return self.get_paginated_response(StockMovementSerializer(page, many=True).data)
        return Response(StockMovementSerializer(movements, many=True).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("product", "created_by").all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["product", "movement_type"]
    ordering_fields = ["created_at"]
