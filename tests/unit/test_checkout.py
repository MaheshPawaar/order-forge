from decimal import Decimal

import pytest

from apps.inventory.models import InventoryReservation, ReservationStatus
from apps.orders.checkout import InvalidCheckout, checkout
from apps.orders.models import Order, OrderStatus


@pytest.mark.django_db
def test_checkout_reserves_stock(user, make_stock):
    item = make_stock(on_hand=10)

    order = checkout(user, [(item.sku_id, 3)])

    assert order.status == OrderStatus.INVENTORY_RESERVED
    item.refresh_from_db()
    assert item.reserved == 3
    assert order.inventory_reservation.status == ReservationStatus.ACTIVE


@pytest.mark.django_db
def test_checkout_writes_creation_and_reserved_history(user, make_stock):
    item = make_stock(on_hand=10)

    order = checkout(user, [(item.sku_id, 3)])

    history = list(order.status_history.values_list("from_status", "to_status"))
    assert history == [
        (None, OrderStatus.CREATED),
        (OrderStatus.CREATED, OrderStatus.INVENTORY_RESERVED),
    ]


@pytest.mark.django_db
def test_short_stock_fails_without_touching_stock(user, make_stock):
    item = make_stock(on_hand=2)

    order = checkout(user, [(item.sku_id, 3)])

    assert order.status == OrderStatus.INVENTORY_FAILED
    item.refresh_from_db()
    assert item.reserved == 0
    assert InventoryReservation.objects.count() == 0


@pytest.mark.django_db
def test_price_is_snapshot(user, make_stock):
    item = make_stock(price="100.00")

    order = checkout(user, [(item.sku_id, 2)])
    item.sku.price = Decimal("150.00")
    item.sku.save()

    order_item = order.items.get()
    order_item.refresh_from_db()
    order.refresh_from_db()
    assert order_item.unit_price == Decimal("100.00")
    assert order.total == Decimal("200.00")


@pytest.mark.django_db
def test_duplicate_lines_are_merged(user, make_stock):
    item = make_stock()

    order = checkout(user, [(item.sku_id, 1), (item.sku_id, 2)])

    assert order.items.count() == 1
    assert order.items.get().quantity == 3


@pytest.mark.django_db
def test_total_covers_all_lines(user, make_stock):
    first = make_stock(price="100.00")
    second = make_stock(price="25.50")

    order = checkout(user, [(first.sku_id, 1), (second.sku_id, 2)])

    assert order.total == Decimal("151.00")


@pytest.mark.django_db
@pytest.mark.parametrize("case", ["empty", "zero", "unknown", "inactive"])
def test_invalid_input_is_rejected(user, make_stock, case):
    if case == "empty":
        items = []
    elif case == "zero":
        items = [(make_stock().sku_id, 0)]
    elif case == "unknown":
        items = [(999999, 1)]
    else:
        items = [(make_stock(is_active=False).sku_id, 1)]

    with pytest.raises(InvalidCheckout):
        checkout(user, items)

    assert Order.objects.count() == 0
