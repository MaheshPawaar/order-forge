import pytest

from apps.catalog.models import SKU, Product
from apps.inventory.models import InventoryItem

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/products"
SKUS = "/api/v1/skus"


def create_product(name="Keyboard", is_active=True):
    return Product.objects.create(name=name, is_active=is_active)


def create_sku(product, code, is_active=True, price="50.00"):
    return SKU.objects.create(product=product, code=code, price=price, is_active=is_active)


@pytest.fixture
def mixed_catalog():
    visible = create_product("Visible")
    create_sku(visible, "V-ON")
    create_sku(visible, "V-OFF", is_active=False)
    hidden = create_product("Hidden", is_active=False)
    create_sku(hidden, "H-ON")


def test_anonymous_can_list_products_with_pagination(api_client):
    product = create_product()
    create_sku(product, "KB-1")

    response = api_client.get(PRODUCTS)

    assert response.status_code == 200
    assert {"count", "next", "previous", "results"} <= response.data.keys()
    assert response.data["count"] == 1
    assert response.data["results"][0]["skus"][0]["code"] == "KB-1"


def test_customer_sees_only_active_products_and_skus(customer_client, mixed_catalog):
    response = customer_client.get(PRODUCTS)

    results = response.data["results"]
    assert [p["name"] for p in results] == ["Visible"]
    assert [s["code"] for s in results[0]["skus"]] == ["V-ON"]


def test_staff_sees_inactive_products_and_skus(staff_client, mixed_catalog):
    response = staff_client.get(PRODUCTS)

    results = response.data["results"]
    assert [p["name"] for p in results] == ["Visible", "Hidden"]
    assert [s["code"] for s in results[0]["skus"]] == ["V-ON", "V-OFF"]


@pytest.mark.parametrize(
    ("client_name", "expected_status"),
    [("api_client", 401), ("customer_client", 403), ("staff_client", 201)],
)
def test_only_staff_can_create_product(request, client_name, expected_status):
    client = request.getfixturevalue(client_name)

    response = client.post(PRODUCTS, {"name": "Mouse"}, format="json")

    assert response.status_code == expected_status
    assert Product.objects.filter(name="Mouse").exists() == (expected_status == 201)


def test_customer_cannot_use_sku_endpoints(customer_client):
    product = create_product()

    list_response = customer_client.get(SKUS)
    create_response = customer_client.post(
        SKUS, {"product": product.id, "code": "KB-2", "price": "75.00"}, format="json"
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403


def test_staff_creating_sku_also_creates_inventory_row(staff_client):
    product = create_product()

    response = staff_client.post(
        SKUS, {"product": product.id, "code": "KB-2", "price": "75.00"}, format="json"
    )

    assert response.status_code == 201
    inventory = InventoryItem.objects.get(sku__code="KB-2")
    assert inventory.on_hand == 0
    assert inventory.reserved == 0


def test_negative_price_is_rejected_with_400(staff_client):
    product = create_product()

    response = staff_client.post(
        SKUS, {"product": product.id, "code": "KB-2", "price": "-1.00"}, format="json"
    )

    assert response.status_code == 400
    assert "price" in response.data
    assert not SKU.objects.filter(code="KB-2").exists()


def test_delete_is_not_allowed(staff_client):
    product = create_product()

    response = staff_client.delete(f"{PRODUCTS}/{product.id}")

    assert response.status_code == 405
    assert Product.objects.filter(pk=product.pk).exists()


@pytest.mark.parametrize(
    ("term", "expected_names"),
    [("keyb", ["Keyboard"]), ("MS-1", ["Mouse"]), ("nothing", [])],
)
def test_search_matches_product_name_and_sku_code(api_client, term, expected_names):
    create_sku(create_product("Keyboard"), "KB-1")
    create_sku(create_product("Mouse"), "MS-1")

    response = api_client.get(PRODUCTS, {"search": term})

    assert [p["name"] for p in response.data["results"]] == expected_names


def test_product_list_query_count_does_not_grow(api_client, django_assert_num_queries):
    for n in range(5):
        product = create_product(f"P{n}")
        create_sku(product, f"P{n}-A")
        create_sku(product, f"P{n}-B")

    # 1 COUNT for pagination + 1 for products + 1 prefetch for all their SKUs
    with django_assert_num_queries(3):
        response = api_client.get(PRODUCTS)

    assert response.data["count"] == 5
