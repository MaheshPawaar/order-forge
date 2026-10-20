from django.db import transaction
from django.db.models import Prefetch
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAdminUser

from apps.catalog.models import SKU, Product
from apps.catalog.serializers import ProductSerializer, SKUSerializer
from apps.common.permissions import IsStaffOrReadOnly
from apps.inventory.models import InventoryItem

WRITE_METHODS_WITHOUT_DELETE = ["get", "post", "patch", "head", "options"]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsStaffOrReadOnly]
    http_method_names = WRITE_METHODS_WITHOUT_DELETE
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "skus__code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["id"]

    def get_queryset(self):
        products = Product.objects.all()
        skus = SKU.objects.order_by("id")
        if not self.request.user.is_staff:
            products = products.filter(is_active=True)
            skus = skus.filter(is_active=True)
        return products.prefetch_related(Prefetch("skus", queryset=skus))


class SKUViewSet(viewsets.ModelViewSet):
    queryset = SKU.objects.order_by("id")
    serializer_class = SKUSerializer
    permission_classes = [IsAdminUser]
    http_method_names = WRITE_METHODS_WITHOUT_DELETE

    def perform_create(self, serializer):
        with transaction.atomic():
            sku = serializer.save()
            InventoryItem.objects.create(sku=sku)
