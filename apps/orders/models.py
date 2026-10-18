from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    INVENTORY_RESERVED = "INVENTORY_RESERVED", "Inventory Reserved"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    INVENTORY_FAILED = "INVENTORY_FAILED", "Inventory Failed"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.CREATED
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=OrderStatus.values), name="orders_order_status_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0), name="orders_order_total_non_negative"
            ),
        ]

    def __str__(self):
        return f"Order {self.pk}: {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey("catalog.sku", on_delete=models.PROTECT, related_name="order_items")
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="orders_order_item_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="orders_order_item_unit_price_non_negative",
            ),
            models.UniqueConstraint(fields=["order", "sku"], name="orders_order_item_unique_sku"),
        ]

    def __str__(self):
        return f"{self.sku}: {self.quantity} x {self.unit_price}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class OrderStatusHistory(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(  # noqa: DJ001  NULL = creation row; "" is blocked by the check constraint
        max_length=20, choices=OrderStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(to_status__in=OrderStatus.values),
                name="orders_status_history_to_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(from_status__isnull=True)
                | models.Q(from_status__in=OrderStatus.values),
                name="orders_status_history_from_status_valid",
            ),
        ]

    def __str__(self):
        return f"Order {self.order_id}: {self.from_status} -> {self.to_status}"
