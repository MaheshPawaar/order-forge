from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class InventoryItem(TimeStampedModel):
    sku = models.OneToOneField("catalog.sku", on_delete=models.PROTECT, related_name="inventory")
    on_hand = models.IntegerField(default=0)
    reserved = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(on_hand__gte=0), name="inventory_on_hand_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(reserved__gte=0), name="inventory_reserved_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(reserved__lte=models.F("on_hand")),
                name="inventory_reserved_lte_on_hand",
            ),
        ]

    @property
    def available(self):
        return self.on_hand - self.reserved

    def __str__(self):
        return f"{self.sku.code}: {self.on_hand} on hand, {self.reserved} reserved."


class LedgerReason(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    DAMAGED = "DAMAGED", "Damaged"
    CORRECTION = "CORRECTION", "Correction"
    RETURNED = "RETURNED", "Returned"


class InventoryLedger(models.Model):
    inventory_item = models.ForeignKey(
        "InventoryItem", on_delete=models.PROTECT, related_name="ledger_entries"
    )
    quantity_change = models.IntegerField()
    reason = models.CharField(max_length=20, choices=LedgerReason.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_adjustments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity_change=0),
                name="inventory_ledger_quantity_change_non_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(reason__in=LedgerReason.values),
                name="inventory_ledger_reason_valid",
            ),
        ]

    def __str__(self):
        return f"{self.inventory_item.sku}: {self.quantity_change:+d}"


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMMITTED = "COMMITTED", "Committed"
    RELEASED = "RELEASED", "Released"
    EXPIRED = "EXPIRED", "Expired"


class InventoryReservation(TimeStampedModel):
    order = models.OneToOneField(
        "orders.order", on_delete=models.PROTECT, related_name="inventory_reservation"
    )
    status = models.CharField(
        max_length=15, choices=ReservationStatus.choices, default=ReservationStatus.ACTIVE
    )
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ReservationStatus.values),
                name="inventory_reservation_status_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["expires_at"],
                condition=models.Q(status=ReservationStatus.ACTIVE),
                name="inv_res_active_expires_idx",
            )
        ]


class ReservationItem(models.Model):
    reservation = models.ForeignKey(
        "InventoryReservation", on_delete=models.CASCADE, related_name="items"
    )
    inventory_item = models.ForeignKey(
        "InventoryItem", on_delete=models.PROTECT, related_name="reservation_items"
    )
    quantity = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="inventory_reservation_item_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=["reservation", "inventory_item"],
                name="inventory_reservation_item_unique_sku",
            ),
        ]

    def __str__(self):
        return f"{self.inventory_item.sku}: {self.quantity}"
