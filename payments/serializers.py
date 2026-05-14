from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["payment_date", "processed_by"]


class PaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payments = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate_payments(self, value):
        allowed_methods = [m[0] for m in Payment.Method.choices]
        for p in value:
            if "payment_method" not in p or p["payment_method"] not in allowed_methods:
                raise serializers.ValidationError(f"Invalid payment method.")
            if "paid_amount" not in p or float(p["paid_amount"]) <= 0:
                raise serializers.ValidationError("paid_amount must be positive.")
        return value


class RefundSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.CharField(source="processed_by.get_full_name", read_only=True)

    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = ["created_at", "processed_by"]


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField()
    transaction_id = serializers.CharField(required=False, allow_blank=True)
