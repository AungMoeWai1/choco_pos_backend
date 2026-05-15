from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Customer, LoyaltyTransaction


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = LoyaltyTransaction
        fields = "__all__"
        read_only_fields = ["created_at", "balance_after"]


class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "phone", "email",
            "loyalty_points", "is_active", "created_at",
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    total_purchases = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "phone", "email", "address", "notes",
            "loyalty_points", "is_active", "created_at", "updated_at",
            "total_purchases", "total_spent",
        ]
        read_only_fields = ["created_at", "updated_at", "loyalty_points"]

    @extend_schema_field(serializers.IntegerField())
    def get_total_purchases(self, obj):
        return obj.total_purchases

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_spent(self, obj):
        return obj.total_spent


class CustomerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["full_name", "phone", "email", "address", "notes", "is_active"]

    def validate_phone(self, value):
        qs = Customer.objects.filter(phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if value and qs.exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value


class LoyaltyAdjustSerializer(serializers.Serializer):
    points = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
