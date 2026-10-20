from rest_framework import serializers

from apps.catalog.models import SKU, Product


class SKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ["id", "product", "code", "name", "price", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"price": {"min_value": 0}}


class ProductSerializer(serializers.ModelSerializer):
    skus = SKUSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "is_active", "skus", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
