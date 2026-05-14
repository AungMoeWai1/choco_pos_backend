from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import ProductType, Category, Product, StockMovement


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = "__all__"
        read_only_fields = ["created_at"]


class CategorySerializer(serializers.ModelSerializer):
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)

    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ["created_at"]


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "barcode", "category_name",
            "selling_price", "stock_quantity", "reorder_level",
            "is_low_stock", "status", "image",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    is_low_stock = serializers.SerializerMethodField()
    profit_margin = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    price_with_tax = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    @extend_schema_field(serializers.BooleanField())
    def get_is_low_stock(self, obj):
        return obj.is_low_stock

    @extend_schema_field(serializers.FloatField())
    def get_profit_margin(self, obj):
        return obj.profit_margin

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_tax_amount(self, obj):
        return obj.tax_amount

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_price_with_tax(self, obj):
        return obj.price_with_tax


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "name", "sku", "barcode", "category", "product_type",
            "cost_price", "selling_price", "tax_rate",
            "stock_quantity", "reorder_level", "image",
            "description", "status", "store",
        ]

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    def validate(self, attrs):
        cost = attrs.get("cost_price", 0)
        sell = attrs.get("selling_price", 0)
        if sell < cost:
            raise serializers.ValidationError(
                {"selling_price": "Selling price should not be less than cost price."}
            )
        return attrs


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ["created_at", "quantity_before", "quantity_after"]


class StockAdjustSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=StockMovement.MovementType.choices)
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    reference = serializers.CharField(required=False, allow_blank=True)
