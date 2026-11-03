import uuid

import pytest

from cart.models import Cart, CartItem

pytestmark = pytest.mark.django_db

URL = "/api/cart"


def add(client, product, size, quantity=None, cart_id=None):
    payload = {"product_id": str(product.id), "size": size}
    if quantity is not None:
        payload["quantity"] = quantity
    if cart_id is not None:
        payload["cart_id"] = str(cart_id)
    return client.post(URL, payload, format="json")


def stock_of(product):
    product.refresh_from_db()
    return product.stock_quantity


def error_code(response):
    return response.json()["error"]["code"]


# --- POST /api/cart ----------------------------------------------------------

def test_add_to_new_cart_returns_201_and_reserves_stock(api_client, products):
    tee = products["tee"]

    response = add(api_client, tee, "M", 3)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    cart = body["data"]
    assert cart["status"] == "active"
    assert len(cart["items"]) == 1
    item = cart["items"][0]
    assert item["product"] == {"id": str(tee.id), "title": "Basic Tee"}
    assert item["size"] == "M"
    assert item["quantity"] == 3
    assert item["unit_price"] == "10.00"
    assert item["subtotal"] == "30.00"
    assert stock_of(tee) == 7


def test_quantity_defaults_to_one(api_client, products):
    response = add(api_client, products["tee"], "M")

    assert response.status_code == 201
    assert response.json()["data"]["items"][0]["quantity"] == 1


def test_add_same_product_and_size_merges_quantity(api_client, products):
    tee = products["tee"]
    cart_id = add(api_client, tee, "M", 2).json()["data"]["id"]

    response = add(api_client, tee, "M", 3, cart_id=cart_id)

    assert response.status_code == 201
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 5
    assert CartItem.objects.count() == 1
    assert stock_of(tee) == 5


def test_add_same_product_different_size_creates_new_item(api_client, products):
    tee = products["tee"]
    cart_id = add(api_client, tee, "M", 1).json()["data"]["id"]

    response = add(api_client, tee, "L", 2, cart_id=cart_id)

    items = response.json()["data"]["items"]
    assert sorted((i["size"], i["quantity"]) for i in items) == [("L", 2), ("M", 1)]
    assert stock_of(tee) == 7


def test_unit_price_is_a_snapshot(api_client, products):
    tee = products["tee"]
    cart_id = add(api_client, tee, "M", 1).json()["data"]["id"]
    tee.price = "99.00"
    tee.save()

    cart = api_client.get(f"{URL}/{cart_id}").json()["data"]

    assert cart["items"][0]["unit_price"] == "10.00"


def test_add_invalid_size_returns_400_with_available_sizes(api_client, products):
    tee = products["tee"]

    response = add(api_client, tee, "XXL", 1)

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "BAD_REQUEST"
    assert error["details"] == {"size": "XXL", "available_sizes": ["S", "M", "L"]}
    assert stock_of(tee) == 10


@pytest.mark.parametrize("quantity", [0, -1, 101])
def test_add_invalid_quantity_returns_400(api_client, products, quantity):
    response = add(api_client, products["tee"], "M", quantity)

    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"
    assert "quantity" in response.json()["error"]["details"]


def test_add_missing_fields_returns_400(api_client, db):
    response = api_client.post(URL, {}, format="json")

    assert response.status_code == 400
    assert set(response.json()["error"]["details"]) == {"product_id", "size"}


def test_add_unknown_product_returns_404(api_client, db):
    response = api_client.post(URL, {"product_id": str(uuid.uuid4()), "size": "M"}, format="json")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Product not found"
    assert Cart.objects.count() == 0  # the new cart was rolled back


def test_add_to_unknown_cart_returns_404(api_client, products):
    response = add(api_client, products["tee"], "M", 1, cart_id=uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Cart not found"
    assert stock_of(products["tee"]) == 10


def test_add_more_than_stock_returns_409_and_stock_unchanged(api_client, products):
    jeans = products["jeans"]  # stock 5

    response = add(api_client, jeans, "32", 6)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INSUFFICIENT_STOCK"
    assert error["details"] == {"requested": 6, "available": 5}
    assert stock_of(jeans) == 5
    assert Cart.objects.count() == 0
    assert CartItem.objects.count() == 0


def test_add_out_of_stock_product_returns_409(api_client, products):
    response = add(api_client, products["coat"], "M", 1)  # stock 0

    assert response.status_code == 409
    assert error_code(response) == "INSUFFICIENT_STOCK"


def test_add_exact_remaining_stock_succeeds(api_client, products):
    jacket = products["jacket"]  # stock 1

    assert add(api_client, jacket, "M", 1).status_code == 201
    assert stock_of(jacket) == 0
    assert add(api_client, jacket, "M", 1).status_code == 409


def test_add_to_checked_out_cart_returns_409(api_client, products):
    tee = products["tee"]
    cart = Cart.objects.create(status=Cart.Status.CHECKED_OUT)

    response = add(api_client, tee, "M", 1, cart_id=cart.id)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFLICT"
    assert error["details"] == {"status": "checked_out"}
    assert stock_of(tee) == 10


# --- GET /api/cart/<cart_id> ----------------------------------------------------

def test_get_cart_returns_correct_totals(api_client, products):
    cart_id = add(api_client, products["tee"], "M", 3).json()["data"]["id"]   # 3 x 10.00
    add(api_client, products["dress"], "S", 2, cart_id=cart_id)              # 2 x 60.00

    response = api_client.get(f"{URL}/{cart_id}")

    assert response.status_code == 200
    cart = response.json()["data"]
    assert cart["id"] == cart_id
    assert cart["total_items"] == 5
    assert cart["total_price"] == "150.00"
    assert sorted(i["subtotal"] for i in cart["items"]) == ["120.00", "30.00"]


def test_get_empty_cart_totals_are_zero(api_client, db):
    cart = Cart.objects.create()

    data = api_client.get(f"{URL}/{cart.id}").json()["data"]

    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["total_price"] == "0.00"


def test_get_unknown_cart_returns_404(api_client, db):
    response = api_client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Cart not found"


def test_get_cart_uses_constant_number_of_queries(api_client, products, django_assert_num_queries):
    cart_id = add(api_client, products["tee"], "M", 1).json()["data"]["id"]
    for key, size in [("dress", "S"), ("hoodie", "6Y"), ("jeans", "30")]:
        add(api_client, products[key], size, 1, cart_id=cart_id)

    # cart + items (with products joined), whatever the number of items.
    with django_assert_num_queries(2):
        api_client.get(f"{URL}/{cart_id}")


# --- DELETE /api/cart/<item_id> -------------------------------------------------

@pytest.fixture
def cart_with_tee(api_client, products):
    """A cart holding 4 x Basic Tee (M); tee stock is 10 - 4 = 6."""
    cart = add(api_client, products["tee"], "M", 4).json()["data"]
    return cart["id"], cart["items"][0]["id"]


def test_delete_with_quantity_reduces_item_and_returns_stock(api_client, products, cart_with_tee):
    cart_id, item_id = cart_with_tee

    response = api_client.delete(f"{URL}/{item_id}?quantity=3")

    assert response.status_code == 200
    cart = response.json()["data"]
    assert cart["id"] == cart_id
    assert cart["items"][0]["quantity"] == 1
    assert cart["total_items"] == 1
    assert stock_of(products["tee"]) == 9


def test_delete_with_quantity_equal_to_item_removes_it(api_client, products, cart_with_tee):
    _, item_id = cart_with_tee

    response = api_client.delete(f"{URL}/{item_id}?quantity=4")

    assert response.json()["data"]["items"] == []
    assert stock_of(products["tee"]) == 10


def test_delete_without_quantity_removes_item_and_returns_all_stock(api_client, products, cart_with_tee):
    cart_id, item_id = cart_with_tee

    response = api_client.delete(f"{URL}/{item_id}")

    assert response.status_code == 200
    cart = response.json()["data"]
    assert cart["id"] == cart_id
    assert cart["items"] == []
    assert cart["total_price"] == "0.00"
    assert not CartItem.objects.filter(pk=item_id).exists()
    assert stock_of(products["tee"]) == 10


def test_delete_quantity_greater_than_item_returns_400(api_client, products, cart_with_tee):
    _, item_id = cart_with_tee

    response = api_client.delete(f"{URL}/{item_id}?quantity=5")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "BAD_REQUEST"
    assert error["details"] == {"requested": 5, "in_cart": 4}
    assert stock_of(products["tee"]) == 6


@pytest.mark.parametrize("quantity", ["0", "abc"])
def test_delete_invalid_quantity_returns_400(api_client, products, cart_with_tee, quantity):
    _, item_id = cart_with_tee

    response = api_client.delete(f"{URL}/{item_id}?quantity={quantity}")

    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_delete_unknown_item_returns_404(api_client, db):
    response = api_client.delete(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Cart item not found"


def test_delete_from_checked_out_cart_returns_409(api_client, products, cart_with_tee):
    cart_id, item_id = cart_with_tee
    Cart.objects.filter(pk=cart_id).update(status=Cart.Status.CHECKED_OUT)

    response = api_client.delete(f"{URL}/{item_id}")

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert stock_of(products["tee"]) == 6
