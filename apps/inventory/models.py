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
