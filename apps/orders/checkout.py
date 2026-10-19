from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import InventoryItem, InventoryReservation, ReservationItem
from apps.orders.models import Order, OrderItem, OrderStatus, OrderStatusHistory
from apps.orders.services import transition


class InvalidCheckout(Exception):
    pass


def _merge_items(items):
    if not items:
        raise InvalidCheckout("Checkout needs at least one item")

    merged = defaultdict(int)
    for sku_id, quantity in items:
        if quantity <= 0:
            raise InvalidCheckout(f"Quantity for SKU {sku_id} must be positive")
        merged[sku_id] += quantity
    return dict(merged)


def checkout(user, items):
    wanted = _merge_items(items)

    with transaction.atomic():
        rows = list(
            InventoryItem.objects.select_for_update(of=("self",))
            .select_related("sku")
            .filter(sku_id__in=wanted.keys())
            .order_by("sku_id")
        )

        stock = {row.sku_id: row for row in rows}

        missing = set(wanted) - set(stock)

        if missing:
            raise InvalidCheckout(f"Unknown SKUs: {sorted(missing)}")

        inactive = [row.sku_id for row in rows if not row.sku.is_active]
        if inactive:
            raise InvalidCheckout(f"SKUs not for sale: {inactive}")

        is_short = any(stock[sku_id].available < qty for sku_id, qty in wanted.items())

        total = sum(stock[sku_id].sku.price * qty for sku_id, qty in wanted.items())
        order = Order.objects.create(user=user, total=total)
        OrderStatusHistory.objects.create(
            order=order, from_status=None, to_status=OrderStatus.CREATED
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    sku=stock[sku_id].sku,
                    quantity=qty,
                    unit_price=stock[sku_id].sku.price,
                )
                for sku_id, qty in wanted.items()
            ]
        )

        if is_short:
            transition(order, OrderStatus.INVENTORY_FAILED)
            return order

        reservation = InventoryReservation.objects.create(
            order=order,
            expires_at=timezone.now() + timedelta(minutes=settings.RESERVATION_TTL_MINUTES),
        )
        for sku_id, qty in wanted.items():
            row = stock[sku_id]
            row.reserved += qty
            row.save(update_fields=["reserved", "updated_at"])
        ReservationItem.objects.bulk_create(
            [
                ReservationItem(reservation=reservation, inventory_item=stock[sku_id], quantity=qty)
                for sku_id, qty in wanted.items()
            ]
        )
        transition(order, OrderStatus.INVENTORY_RESERVED)
    return order
