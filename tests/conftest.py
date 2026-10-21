import itertools
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import SKU, Product
from apps.inventory.models import InventoryItem
from apps.orders.models import Order, OrderStatus


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pass")


@pytest.fixture
def make_order(user):
    def _make(status=OrderStatus.CREATED):
        return Order.objects.create(user=user, total=Decimal("0.00"), status=status)

    return _make


@pytest.fixture
def make_stock():
    counter = itertools.count(1)

    def _make(on_hand=10, price="100.00", is_active=True):
        n = next(counter)
        product = Product.objects.create(name=f"Product {n}")
        sku = SKU.objects.create(
            product=product, code=f"SKU-{n}", price=Decimal(price), is_active=is_active
        )
        return InventoryItem.objects.create(sku=sku, on_hand=on_hand)

    return _make


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user("staff", password="pass", is_staff=True)


@pytest.fixture
def customer_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client
