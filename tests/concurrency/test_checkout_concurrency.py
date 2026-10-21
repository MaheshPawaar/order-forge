import itertools

import pytest

from apps.orders.checkout import checkout
from apps.orders.models import Order, OrderStatus
from tests.concurrency.helpers import run_in_threads


@pytest.mark.django_db(transaction=True)
def test_100_buyers_for_1_unit(user, make_stock):
    item = make_stock(on_hand=1)

    orders, errors = run_in_threads(lambda: checkout(user, [(item.sku_id, 1)]), 100)

    assert errors == []
    assert len(orders) == 100
    assert Order.objects.filter(status=OrderStatus.INVENTORY_RESERVED).count() == 1
    assert Order.objects.filter(status=OrderStatus.INVENTORY_FAILED).count() == 99
    item.refresh_from_db()
    assert item.reserved == 1


@pytest.mark.django_db(transaction=True)
def test_1000_buyers_for_100_units(user, make_stock):
    item = make_stock(on_hand=100)

    orders, errors = run_in_threads(lambda: checkout(user, [(item.sku_id, 1)]), 1000)

    assert errors == []
    assert Order.objects.filter(status=OrderStatus.INVENTORY_RESERVED).count() == 100
    assert Order.objects.filter(status=OrderStatus.INVENTORY_FAILED).count() == 900
    item.refresh_from_db()
    assert item.reserved == 100


@pytest.mark.django_db(transaction=True)
def test_opposite_line_order_does_not_deadlock(user, make_stock):
    first = make_stock(on_hand=1000)
    second = make_stock(on_hand=1000)
    flip = itertools.count()

    def task():
        lines = [(first.sku_id, 1), (second.sku_id, 1)]
        if next(flip) % 2:
            lines.reverse()
        return checkout(user, lines)

    orders, errors = run_in_threads(task, 200)

    assert errors == []
    assert Order.objects.filter(status=OrderStatus.INVENTORY_RESERVED).count() == 200
