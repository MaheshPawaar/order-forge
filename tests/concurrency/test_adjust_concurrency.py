import itertools

import pytest

from apps.inventory.models import InventoryLedger, LedgerReason
from apps.inventory.services import InsufficientStock, adjust_stock
from apps.orders.checkout import checkout
from apps.orders.models import OrderStatus
from tests.concurrency.helpers import run_in_threads


@pytest.mark.django_db(transaction=True)
def test_concurrent_adds_lose_no_updates(staff_user, make_stock):
    item = make_stock(on_hand=0)
    code = item.sku.code

    def task():
        return adjust_stock(
            sku_code=code, quantity_change=1, reason=LedgerReason.RECEIVED, user=staff_user
        )

    results, errors = run_in_threads(task, 200)

    assert errors == []
    item.refresh_from_db()
    assert item.on_hand == 200
    assert InventoryLedger.objects.filter(inventory_item=item).count() == 200


@pytest.mark.django_db(transaction=True)
def test_removals_racing_checkouts_keep_stock_consistent(user, staff_user, make_stock):
    item = make_stock(on_hand=100)
    code = item.sku.code
    flip = itertools.count()

    def task():
        if next(flip) % 2:
            return checkout(user, [(item.sku_id, 1)]).status
        try:
            adjust_stock(
                sku_code=code, quantity_change=-1, reason=LedgerReason.DAMAGED, user=staff_user
            )
            return "REMOVED"
        except InsufficientStock:
            return "REJECTED"

    results, errors = run_in_threads(task, 200)

    assert errors == []
    removed = results.count("REMOVED")
    reserved = results.count(OrderStatus.INVENTORY_RESERVED)
    item.refresh_from_db()
    assert item.on_hand == 100 - removed
    assert item.reserved == reserved
    assert 0 <= item.reserved <= item.on_hand
    assert InventoryLedger.objects.filter(inventory_item=item).count() == removed
