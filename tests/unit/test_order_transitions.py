import pytest

from apps.orders.models import OrderStatus
from apps.orders.services import ALLOWED_TRANSITIONS, InvalidTransition, transition


@pytest.mark.django_db
def test_valid_transition_updates_status(make_order):
    order = make_order()

    transition(order, OrderStatus.INVENTORY_RESERVED)
    order.refresh_from_db()
    assert order.status == OrderStatus.INVENTORY_RESERVED


@pytest.mark.django_db
def test_valid_transition_writes_one_history_row(make_order):
    order = make_order()
    transition(order, OrderStatus.INVENTORY_RESERVED)
    assert order.status_history.count() == 1
    row = order.status_history.get()
    assert row.from_status == OrderStatus.CREATED
    assert row.to_status == OrderStatus.INVENTORY_RESERVED


@pytest.mark.django_db
def test_invalid_transition_raises(make_order):
    order = make_order()

    with pytest.raises(InvalidTransition):
        transition(order, OrderStatus.CONFIRMED)


@pytest.mark.django_db
def test_invalid_transition_changes_nothing(make_order):
    order = make_order()

    with pytest.raises(InvalidTransition):
        transition(order, OrderStatus.CONFIRMED)

    order.refresh_from_db()
    assert order.status == OrderStatus.CREATED
    assert order.status_history.count() == 0


TERMINAL = [
    OrderStatus.CONFIRMED,
    OrderStatus.INVENTORY_FAILED,
    OrderStatus.PAYMENT_FAILED,
    OrderStatus.EXPIRED,
    OrderStatus.CANCELLED,
]


@pytest.mark.django_db
@pytest.mark.parametrize("from_state", TERMINAL)
@pytest.mark.parametrize("to_state", list(OrderStatus))
def test_terminal_states_allow_no_moves(make_order, from_state, to_state):
    order = make_order(from_state)

    with pytest.raises(InvalidTransition):
        transition(order, to_state)


@pytest.mark.django_db
def test_happy_path_writes_history_in_order(make_order):
    order = make_order()

    transition(order, OrderStatus.INVENTORY_RESERVED)
    transition(order, OrderStatus.PAYMENT_PENDING)
    transition(order, OrderStatus.CONFIRMED)

    history = list(order.status_history.values_list("from_status", "to_status"))
    assert history == [
        (OrderStatus.CREATED, OrderStatus.INVENTORY_RESERVED),
        (OrderStatus.INVENTORY_RESERVED, OrderStatus.PAYMENT_PENDING),
        (OrderStatus.PAYMENT_PENDING, OrderStatus.CONFIRMED),
    ]


@pytest.mark.django_db
def test_caller_order_is_updated(make_order):
    order = make_order()

    transition(order, OrderStatus.INVENTORY_RESERVED)

    assert order.status == OrderStatus.INVENTORY_RESERVED


@pytest.mark.django_db
def test_every_status_has_a_table_entry():
    assert set(ALLOWED_TRANSITIONS) == set(OrderStatus)
