from django.db import transaction

from apps.inventory.models import InventoryItem, InventoryLedger


class InsufficientStock(Exception):
    pass


def adjust_stock(*, sku_code, quantity_change, reason, user):
    with transaction.atomic():
        item = (
            InventoryItem.objects.select_for_update(of=("self",))
            .select_related("sku")
            .get(sku__code=sku_code)
        )

        new_on_hand = item.on_hand + quantity_change
        if new_on_hand < item.reserved:
            raise InsufficientStock(
                f"{sku_code}: on_hand would be {new_on_hand}, but {item.reserved} are reserved"
            )

        item.on_hand = new_on_hand
        item.save(update_fields=["on_hand", "updated_at"])
        InventoryLedger.objects.create(
            inventory_item=item, quantity_change=quantity_change, reason=reason, created_by=user
        )
    return item
