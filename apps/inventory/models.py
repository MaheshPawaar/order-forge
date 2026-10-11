from django.db import models

from apps.common.models import TimeStampedModel


class InventoryItem(TimeStampedModel):
    sku=models.OneToOneField('catalog.sku', on_delete=models.PROTECT, related_name='inventory')
    on_hand=models.IntegerField(default=0)
    reserved=models.IntegerField(default=0)

    class Meta:
        constraints=[
            models.CheckConstraint(condition=models.Q(on_hand__gte=0),
                                   name='inventory_on_hand_non_negative'),
            models.CheckConstraint(condition=models.Q(reserved__gte=0),
                                   name='inventory_reserved_non_negative'),
            models.CheckConstraint(condition=models.Q(reserved__lte=models.F('on_hand')),
                                   name='inventory_reserved_lte_on_hand')
        ]

    @property
    def available(self):
        return self.on_hand - self.reserved

    def __str__(self):
        return f'{self.sku.code}: {self.on_hand} on hand, {self.reserved} reserved.'