from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Order, OrderItem, ReturnOrder, ReturnItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "product_name", "sku",
            "quantity", "unit_price", "cost_price",
            "tax_rate", "discount_amount", "line_total",
        ]
        read_only_fields = ["product_name", "sku", "line_total"]


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer_name", "cashier_name",
            "grand_total", "payment_status", "order_status",
            "item_count", "created_at",
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["order_number", "created_at", "updated_at", "subtotal", "tax_amount", "grand_total"]


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    items = OrderItemCreateSerializer(many=True)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    loyalty_points_redeemed = serializers.IntegerField(default=0)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["notes", "discount_percent", "discount_amount", "order_status"]


class ReturnItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnItem
        fields = "__all__"


class ReturnOrderSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)

    class Meta:
        model = ReturnOrder
        fields = "__all__"
        read_only_fields = ["created_at", "processed_at", "refund_amount"]


class ReturnOrderCreateSerializer(serializers.Serializer):
    reason = serializers.CharField()
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        min_length=1,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
