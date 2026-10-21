from django.urls import path

from apps.inventory.views import StockAdjustView

urlpatterns = [
    path("inventory/<str:sku_code>/adjust", StockAdjustView.as_view(), name="inventory-adjust"),
]
