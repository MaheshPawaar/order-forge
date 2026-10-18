from django.db import transaction

from apps.orders.models import Order, OrderStatus, OrderStatusHistory

ALLOWED_TRANSITIONS = {
    OrderStatus.CREATED: frozenset(
        {OrderStatus.INVENTORY_RESERVED, OrderStatus.INVENTORY_FAILED, OrderStatus.CANCELLED}
    ),
    OrderStatus.INVENTORY_RESERVED: frozenset(
        {OrderStatus.PAYMENT_PENDING, OrderStatus.EXPIRED, OrderStatus.CANCELLED}
    ),
    OrderStatus.PAYMENT_PENDING: frozenset(
        {OrderStatus.CONFIRMED, OrderStatus.PAYMENT_FAILED, OrderStatus.EXPIRED}
    ),
    OrderStatus.CONFIRMED: frozenset(),
    OrderStatus.INVENTORY_FAILED: frozenset(),
    OrderStatus.PAYMENT_FAILED: frozenset(),
    OrderStatus.EXPIRED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class InvalidTransition(Exception):
    pass


def transition(order, to_state):
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        from_state = locked.status

        if to_state not in ALLOWED_TRANSITIONS[from_state]:
            raise InvalidTransition(
                f"Cannot move order {locked.pk} from {from_state} to {to_state}"
            )

        locked.status = to_state
        locked.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(order=locked, from_status=from_state, to_status=to_state)

    order.status = locked.status
    order.updated_at = locked.updated_at
    return locked
