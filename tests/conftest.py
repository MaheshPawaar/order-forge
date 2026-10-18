from decimal import Decimal

import pytest

from apps.orders.models import Order, OrderStatus


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pass")


@pytest.fixture
def make_order(user):
    def _make(status=OrderStatus.CREATED):
        return Order.objects.create(user=user, total=Decimal("0.00"), status=status)

    return _make
