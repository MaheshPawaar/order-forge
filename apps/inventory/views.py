from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import InventoryItem
from apps.inventory.serializers import InventoryItemSerializer, StockAdjustmentSerializer
from apps.inventory.services import InsufficientStock, adjust_stock


class StockAdjustView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, sku_code):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = adjust_stock(sku_code=sku_code, user=request.user, **serializer.validated_data)
        except InventoryItem.DoesNotExist:
            raise NotFound(f"No inventory for SKU {sku_code}.") from None
        except InsufficientStock as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(InventoryItemSerializer(item).data)
