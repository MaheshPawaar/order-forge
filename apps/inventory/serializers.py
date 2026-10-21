from rest_framework import serializers

from apps.inventory.models import InventoryItem, LedgerReason


class StockAdjustmentSerializer(serializers.Serializer):
    quantity_change = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=LedgerReason.choices)

    def validate_quantity_change(self, value):
        if value == 0:
            raise serializers.ValidationError("Must not be zero.")
        return value


class InventoryItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="sku.code", read_only=True)
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ["sku", "on_hand", "reserved", "available", "updated_at"]
