from rest_framework import serializers
from .models import Store, Terminal, Shift


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class TerminalSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Terminal
        fields = "__all__"
        read_only_fields = ["created_at"]


class ShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    terminal_name = serializers.CharField(source="terminal.name", read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = ["opened_at"]


class ShiftCloseSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)
