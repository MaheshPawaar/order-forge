import pytest

from apps.inventory.models import InventoryItem, InventoryLedger, LedgerReason

pytestmark = pytest.mark.django_db


def adjust_url(item):
    return f"/api/v1/inventory/{item.sku.code}/adjust"


def adjust(client, item, quantity_change, reason=LedgerReason.RECEIVED):
    payload = {"quantity_change": quantity_change, "reason": reason}
    return client.post(adjust_url(item), payload, format="json")


def reserve(item, quantity):
    InventoryItem.objects.filter(pk=item.pk).update(reserved=quantity)


def test_staff_adds_stock_and_ledger_row_is_written(staff_client, staff_user, make_stock):
    item = make_stock(on_hand=10)

    response = adjust(staff_client, item, 5)

    assert response.status_code == 200
    assert response.data["on_hand"] == 15
    assert response.data["available"] == 15
    item.refresh_from_db()
    assert item.on_hand == 15
    entry = InventoryLedger.objects.get(inventory_item=item)
    assert entry.quantity_change == 5
    assert entry.reason == LedgerReason.RECEIVED
    assert entry.created_by == staff_user


def test_staff_can_remove_stock_down_to_reserved(staff_client, make_stock):
    item = make_stock(on_hand=10)
    reserve(item, 4)

    response = adjust(staff_client, item, -6, LedgerReason.DAMAGED)

    assert response.status_code == 200
    assert response.data["on_hand"] == 4
    assert response.data["reserved"] == 4
    assert response.data["available"] == 0


def test_removing_reserved_units_returns_409_and_writes_nothing(staff_client, make_stock):
    item = make_stock(on_hand=10)
    reserve(item, 4)

    response = adjust(staff_client, item, -7, LedgerReason.DAMAGED)

    assert response.status_code == 409
    item.refresh_from_db()
    assert item.on_hand == 10
    assert not InventoryLedger.objects.filter(inventory_item=item).exists()


@pytest.mark.parametrize(
    ("payload", "error_field"),
    [
        ({"quantity_change": 0, "reason": "RECEIVED"}, "quantity_change"),
        ({"quantity_change": 5, "reason": "STOLEN"}, "reason"),
        ({"reason": "RECEIVED"}, "quantity_change"),
    ],
    ids=["zero", "unknown_reason", "missing_quantity"],
)
def test_invalid_payload_returns_400(staff_client, make_stock, payload, error_field):
    item = make_stock(on_hand=10)

    response = staff_client.post(adjust_url(item), payload, format="json")

    assert response.status_code == 400
    assert error_field in response.data
    assert not InventoryLedger.objects.exists()


def test_unknown_sku_returns_404(staff_client):
    payload = {"quantity_change": 5, "reason": "RECEIVED"}

    response = staff_client.post("/api/v1/inventory/NOPE/adjust", payload, format="json")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("client_name", "expected_status"),
    [("api_client", 401), ("customer_client", 403)],
)
def test_only_staff_can_adjust(request, make_stock, client_name, expected_status):
    client = request.getfixturevalue(client_name)
    item = make_stock(on_hand=10)

    response = adjust(client, item, 5)

    assert response.status_code == expected_status
    item.refresh_from_db()
    assert item.on_hand == 10
