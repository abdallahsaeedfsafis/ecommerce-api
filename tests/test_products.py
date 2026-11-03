import uuid
from decimal import Decimal

import pytest

from .conftest import PRODUCT_DATA

pytestmark = pytest.mark.django_db

URL = "/api/products"


def titles(response):
    return [p["title"] for p in response.json()["data"]]


# --- list & envelope -------------------------------------------------------

def test_list_returns_success_data_and_meta(api_client, products):
    response = api_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 6
    assert body["meta"] == {"page": 1, "limit": 10, "total": 6, "total_pages": 1}

    item = body["data"][0]
    assert set(item) == {"id", "title", "price", "category", "sizes", "stock_quantity", "in_stock"}
    assert set(item["category"]) == {"id", "name", "slug"}


def test_in_stock_flag(api_client, products):
    data = {p["title"]: p for p in api_client.get(URL).json()["data"]}

    assert data["Trench Coat"]["in_stock"] is False
    assert data["Basic Tee"]["in_stock"] is True


# --- pagination ------------------------------------------------------------

def test_pagination_limit_and_page(api_client, products):
    first = api_client.get(URL, {"limit": 2, "page": 1}).json()
    second = api_client.get(URL, {"limit": 2, "page": 2}).json()

    assert first["meta"] == {"page": 1, "limit": 2, "total": 6, "total_pages": 3}
    assert second["meta"]["page"] == 2
    assert len(second["data"]) == 2
    assert not {p["id"] for p in first["data"]} & {p["id"] for p in second["data"]}


def test_pagination_pages_cover_every_product_exactly_once(api_client, products):
    seen = []
    for page in (1, 2, 3):
        seen += [p["id"] for p in api_client.get(URL, {"limit": 2, "page": page}).json()["data"]]

    assert sorted(seen) == sorted(str(p.id) for p in products.values())


def test_pagination_limit_is_capped_at_100(api_client, products):
    response = api_client.get(URL, {"limit": 500})

    assert response.status_code == 200
    assert response.json()["meta"]["limit"] == 100


def test_pagination_page_out_of_range_returns_404(api_client, products):
    response = api_client.get(URL, {"page": 99})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("params", [{"limit": 0}, {"page": 0}, {"limit": "abc"}])
def test_pagination_invalid_params_return_400(api_client, products, params):
    response = api_client.get(URL, params)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# --- filters ---------------------------------------------------------------

def test_filter_by_category(api_client, products):
    response = api_client.get(URL, {"category": "women"})

    assert response.status_code == 200
    assert sorted(titles(response)) == ["Midi Dress", "Trench Coat"]
    assert all(p["category"]["slug"] == "women" for p in response.json()["data"])


def test_filter_by_unknown_category_returns_empty_list(api_client, products):
    response = api_client.get(URL, {"category": "does-not-exist"})

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == 0


def test_filter_by_min_and_max_price(api_client, products):
    response = api_client.get(URL, {"min_price": "50", "max_price": "120"})

    assert sorted(titles(response)) == ["Bomber Jacket", "Midi Dress", "Slim Jeans"]


def test_filter_by_min_price_only(api_client, products):
    prices = [Decimal(p["price"]) for p in api_client.get(URL, {"min_price": "100"}).json()["data"]]

    assert sorted(prices) == [Decimal("120.00"), Decimal("150.00")]


def test_filter_by_max_price_only(api_client, products):
    prices = [Decimal(p["price"]) for p in api_client.get(URL, {"max_price": "25"}).json()["data"]]

    assert sorted(prices) == [Decimal("10.00"), Decimal("25.00")]


@pytest.mark.parametrize("value", ["-1", "abc"])
def test_invalid_min_price_returns_400(api_client, products, value):
    response = api_client.get(URL, {"min_price": value})

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "min_price" in error["details"]


def test_min_price_greater_than_max_price_returns_400(api_client, products):
    response = api_client.get(URL, {"min_price": "100", "max_price": "10"})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "min_price" in body["error"]["details"]


# --- sorting ---------------------------------------------------------------

ALL_BY_NEWEST = [data[1] for data in PRODUCT_DATA.values()]


@pytest.mark.parametrize(
    "sort, expected",
    [
        ("price_asc", ["Basic Tee", "Dino Hoodie", "Slim Jeans", "Midi Dress", "Bomber Jacket", "Trench Coat"]),
        ("price_desc", ["Trench Coat", "Bomber Jacket", "Midi Dress", "Slim Jeans", "Dino Hoodie", "Basic Tee"]),
        ("newest", ALL_BY_NEWEST),
        ("oldest", list(reversed(ALL_BY_NEWEST))),
    ],
)
def test_sort_options(api_client, products, sort, expected):
    assert titles(api_client.get(URL, {"sort": sort})) == expected


def test_default_sort_is_newest(api_client, products):
    assert titles(api_client.get(URL)) == ALL_BY_NEWEST


def test_invalid_sort_returns_400(api_client, products):
    response = api_client.get(URL, {"sort": "cheapest"})

    assert response.status_code == 400
    assert "sort" in response.json()["error"]["details"]


# --- detail ----------------------------------------------------------------

def test_detail_returns_product(api_client, products):
    product = products["dress"]

    response = api_client.get(f"{URL}/{product.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == str(product.id)
    assert data["title"] == "Midi Dress"
    assert data["price"] == "60.00"
    assert data["description"] == "Midi Dress description"
    assert data["category"]["slug"] == "women"
    assert {"created_at", "updated_at"} <= set(data)
    assert "meta" not in body


def test_detail_unknown_id_returns_404(api_client, products):
    response = api_client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "Product not found", "details": {}},
    }


def test_detail_non_uuid_returns_json_404(api_client, products):
    response = api_client.get(f"{URL}/not-a-uuid")

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_unknown_route_returns_json_404(api_client, db):
    response = api_client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


# --- N+1 guard --------------------------------------------------------------

def test_list_uses_constant_number_of_queries(api_client, products, django_assert_num_queries):
    # 1 COUNT for pagination + 1 SELECT ... JOIN categories, regardless of page size.
    with django_assert_num_queries(2):
        api_client.get(URL, {"limit": 100})
