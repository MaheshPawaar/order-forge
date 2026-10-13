from django.db import models

from apps.common.models import TimeStampedModel


# Create your models here.
class Product(TimeStampedModel):
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)


class SKU(TimeStampedModel):
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="skus")
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=256, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="sku_price_non_negative")
        ]

    def __str__(self):
        return self.code
