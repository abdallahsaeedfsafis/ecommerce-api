# E-commerce API

A REST API for a clothing store, covering a product catalogue and a shopping cart. Stock is reserved safely, so the store never sells more units than it has, even under concurrent requests.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.18-A30000?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-required-4169E1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-57%20passed-brightgreen?logo=pytest&logoColor=white)
![Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen)

## Live Demo

| | URL |
|---|---|
| API | `https://<your-app>.onrender.com` *(coming soon)* |
| Swagger UI | `https://<your-app>.onrender.com/api/docs` *(coming soon)* |

## Features

- **Products:** list with filtering (category, price range), sorting, and pagination, plus a detail view.
- **Cart:** add items, merge repeated items, reduce or remove items, and view totals.
- **Safe stock reservation:** adding to the cart reserves stock atomically, and removing an item returns it.
- **Proven against race conditions:** 20 concurrent requests for 5 units give exactly 5 successes.
- **Unified response format:** every success and every error has the same JSON shape.
- **Validated inputs:** query parameters and request bodies are checked by serializers, so bad input gets a 400 and never reaches the database.
- **Rate limiting:** anonymous clients get 100 requests per minute.
- **Documentation and tooling:** OpenAPI and Swagger UI, a Postman collection with automated tests, and a seed command.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| Framework | Django 5.2 + Django REST Framework 3.18 |
| Database | PostgreSQL (`ArrayField`, row-level locks, `CHECK` constraints) |
| Docs | drf-spectacular (OpenAPI 3, Swagger UI) |
| Tests | pytest, pytest-django, pytest-cov |
| Config | django-environ (`.env`) |

**Why Django REST Framework?**
- It provides serializers for validation and output in one place, generic views, pagination, throttling, and a pluggable exception handler. That let this project focus on the business rules instead of plumbing.
- The Django ORM exposes the database tools that stock safety depends on: `transaction.atomic()`, `select_for_update()`, `F()` expressions, and database constraints.
- It is mature, well documented, and familiar to most Python teams.

## Project Structure

```
ecommerce-api/
├── config/                 # settings, root urls, wsgi/asgi
├── core/                   # shared, app-agnostic building blocks
│   ├── exceptions.py       # custom errors + unified exception handler
│   ├── pagination.py       # ?page=&limit= pagination
│   ├── responses.py        # success/error envelopes
│   ├── schema.py           # OpenAPI helpers (docs only)
│   └── views.py            # /health, JSON 404/500 handlers
├── products/
│   ├── models.py           # Category, Product
│   ├── serializers.py      # output + query-param validation
│   ├── services.py         # filtering/sorting queries
│   ├── views.py            # thin HTTP layer
│   ├── urls.py
│   └── management/commands/seed.py
├── cart/
│   ├── models.py           # Cart, CartItem
│   ├── serializers.py
│   ├── services.py         # stock reservation + locking
│   ├── views.py
│   └── urls.py
├── tests/                  # pytest suite (products, cart, concurrency)
├── scripts/concurrency_check.py
├── postman/ecommerce-api.postman_collection.json
├── requirements.txt / requirements-dev.txt
└── pytest.ini
```

**How the assessment's layers map to Django:**

| Assessment term | In this project | Responsibility |
|---|---|---|
| Models | `<app>/models.py` | Tables, constraints, indexes |
| Controllers | `<app>/views.py` | Parse the request, call a service, return a response (no business logic) |
| Routes | `<app>/urls.py` + `config/urls.py` | URL → view mapping |
| Services | `<app>/services.py` | Business rules, transactions, locking |
| Validation / DTOs | `<app>/serializers.py` | Validate input, shape output |
| Error middleware | `core/exceptions.py` | Map every exception to the unified error format |

## Getting Started

**Prerequisites:** Python 3.11+, PostgreSQL 14+, Git.

```bash
# 1. Clone
git clone https://github.com/abdallahsaeedfsafis/ecommerce-api.git
cd ecommerce-api

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # macOS / Linux

# 3. Install dependencies (requirements-dev.txt includes requirements.txt + test tools)
pip install -r requirements-dev.txt

# 4. Environment variables
cp .env.example .env             # Windows: copy .env.example .env
# then edit DATABASE_URL and SECRET_KEY

# 5. Create the database
psql -U postgres -c "CREATE DATABASE ecommerce_db;"

# 6. Migrate, seed, run
python manage.py migrate
python manage.py seed            # 3 categories, 20 products (use --reset to start over)
python manage.py runserver
```

`.env.example`:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgres://postgres:password@localhost:5432/ecommerce_db
```

Once it is running:
- Swagger UI: http://127.0.0.1:8000/api/docs
- Health check: http://127.0.0.1:8000/health

## Running Tests

The tests run against a real PostgreSQL test database (`test_ecommerce_db`), which pytest-django creates automatically.

```bash
pytest                                              # 57 tests
pytest -v --cov=products --cov=cart --cov=core      # with coverage (84%)
pytest --create-db                                  # after changing models
python scripts/concurrency_check.py                 # standalone race-condition demo
```

## API Reference

### Endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| GET | `/health` | API and database status | 200 |
| GET | `/api/products` | List products (filter, sort, paginate) | 200 |
| GET | `/api/products/{product_id}` | Product detail | 200 |
| POST | `/api/cart` | Add a product to a cart (creates the cart if `cart_id` is omitted) | 201 |
| GET | `/api/cart/{cart_id}` | Get a cart with its items and totals | 200 |
| DELETE | `/api/cart/{item_id}` | Remove a cart item, or `?quantity=N` units of it | 200 |
| GET | `/api/docs` · `/api/schema` | Swagger UI · OpenAPI schema | 200 |

> `GET` and `DELETE` share the `/api/cart/{id}` route. For `GET` the id is a **cart** id; for `DELETE` it is a **cart item** id.

### Query parameters for `GET /api/products`

| Param | Type | Default | Notes |
|---|---|---|---|
| `category` | slug | — | e.g. `men`; an unknown slug returns an empty list |
| `min_price` | decimal ≥ 0 | — | inclusive |
| `max_price` | decimal ≥ 0 | — | inclusive; must be ≥ `min_price` |
| `sort` | `price_asc` · `price_desc` · `newest` · `oldest` | `newest` | `id` is always added as a tie-breaker |
| `page` | int ≥ 1 | 1 | |
| `limit` | int ≥ 1 | 10 | capped at 100 |

### Examples

**`GET /api/products?category=men&sort=price_asc&limit=1`** returns `200`:

```json
{
  "success": true,
  "data": [
    {
      "id": "cdb50eb8-3e40-4716-91e4-f73d7e81212f",
      "title": "Basic Crew Neck T-Shirt",
      "price": "12.50",
      "category": { "id": "cb243b5c-19cd-4f99-999f-85bc5ea2c28c", "name": "Men", "slug": "men" },
      "sizes": ["S", "M", "L", "XL", "XXL"],
      "stock_quantity": 120,
      "in_stock": true
    }
  ],
  "meta": { "page": 1, "limit": 1, "total": 7, "total_pages": 7 }
}
```

**`POST /api/cart`**

```json
{ "product_id": "77ed3f4a-d5ca-4504-8b43-7ef0a312073b", "size": "M", "quantity": 2 }
```

This returns `201`. Send the returned `id` as `cart_id` to keep adding items to the same cart.

```json
{
  "success": true,
  "data": {
    "id": "61005ec1-ae3c-4df2-95ca-138645482cb0",
    "status": "active",
    "items": [
      {
        "id": "78dec8ec-3526-4a6f-b337-a31ef48bdb54",
        "product": { "id": "77ed3f4a-d5ca-4504-8b43-7ef0a312073b", "title": "Floral Midi Dress" },
        "size": "M",
        "quantity": 2,
        "unit_price": "59.99",
        "subtotal": "119.98"
      }
    ],
    "total_items": 2,
    "total_price": "119.98"
  }
}
```

**`DELETE /api/cart/{item_id}?quantity=1`** returns `200` with the updated cart, in the same shape as above. Leave out `quantity` to remove the whole item.

### Error format

Every error, including unknown routes and unexpected exceptions, has this shape:

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Not enough stock available for this product.",
    "details": { "requested": 2, "available": 1 }
  }
}
```

### Status codes

| Status | `error.code` | When |
|---|---|---|
| 200 / 201 | — | Success (201 for adding to cart) |
| 400 | `VALIDATION_ERROR` | Invalid body or query params (field errors in `details`) |
| 400 | `BAD_REQUEST` | Size not offered; removing more than is in the cart |
| 404 | `NOT_FOUND` | Unknown product, cart, cart item, page, or route |
| 409 | `INSUFFICIENT_STOCK` | Requested quantity is more than the available stock |
| 409 | `CONFLICT` | Cart is not active; database integrity conflict |
| 429 | `TOO_MANY_REQUESTS` | Rate limit hit (`Retry-After` header is set) |
| 500 | `INTERNAL_ERROR` | Unexpected error (logged server-side, no traceback returned) |
| 503 | `SERVICE_UNAVAILABLE` | `/health` only: database unreachable |

## Design Decisions

### Stock reservation on add-to-cart
Adding an item **decrements `stock_quantity` immediately**. Removing or reducing an item gives the units back. Customers never see an item in their cart that can't actually be bought.

### Race-condition handling
Stock is reserved with **one conditional UPDATE**, and its value is never read in Python and then saved:

```python
Product.objects.filter(pk=product.pk, stock_quantity__gte=quantity) \
               .update(stock_quantity=F("stock_quantity") - quantity)
# 0 rows updated → InsufficientStockError (409)
```

- **Conditional UPDATE with `F()`:** the check and the decrement run as one SQL statement. PostgreSQL locks the row while it runs and re-checks `stock_quantity >= quantity` against the latest value. No other request can slip in between "read" and "write", so overselling can't happen.
- **`transaction.atomic()`:** every service function is all-or-nothing. If any later step fails, the stock decrement and any newly created cart roll back together.
- **`select_for_update()` on the cart:** serializes concurrent operations on the *same* cart. For example, two requests can't merge into the same item at once.
- **Consistent lock ordering:** every operation locks the **cart first**, then the item or product row. Two operations can never wait on each other in a cycle, so they can't deadlock.

**Concurrency test result** (`tests/test_concurrency.py`, `scripts/concurrency_check.py`): stock is set to 5, and 20 threads each add 1 unit to their own new cart at the same moment.

```
Succeeded:         5
Failed with 409:   15
Final stock:       0
Carts created:     5      ← failed attempts rolled back their carts
RESULT: PASS - no overselling
```

### Database-level integrity
- **`CHECK` constraints:** `stock_quantity >= 0`, `price >= 0`, and `quantity > 0` are enforced by PostgreSQL itself. They are the last line of defence, even against bugs or raw SQL.
- **Unique `(cart, product, size)`:** a repeated add merges into the existing line instead of duplicating it.
- **`PROTECT` vs `CASCADE`:** you can't delete a category that has products, or a product that is in someone's cart. Deleting a cart removes its items.

### Data types
- **UUID primary keys:** ids can't be guessed. You can't walk `/api/cart/1`, `/api/cart/2`, and so on to read other people's carts.
- **`Decimal` for money:** exact arithmetic with no floating-point drift. Prices are serialized as strings, like `"59.99"`.
- **Price snapshot:** `CartItem.unit_price` stores the price at the moment the item was added, so later price changes don't silently change an existing cart.

### Query performance
- **Indexes** on `price`, `created_at`, and `(category, price)` match the filters and sorts the API supports.
- **No N+1 queries:** `select_related("category")` on products, and `prefetch_related` + `select_related("product")` on cart items. Listing 100 products or loading a cart with many items takes **2 queries**, and tests enforce that number.
- **Stable pagination:** `id` is always the last sort key, so rows with equal sort values never repeat or go missing across pages.

## Postman

1. In Postman, go to **Import** and choose `postman/ecommerce-api.postman_collection.json`.
2. Make sure the server is running and the database is seeded. `base_url` defaults to `http://127.0.0.1:8000`; change it in the collection's **Variables** tab if you need to.
3. Right-click the collection, choose **Run collection**, then **Run**.

The test scripts save `product_id`, `cart_id`, and `item_id` into collection variables, so the requests chain together in order: Health → Products → Cart → Error Cases. Every request has assertions, and the cart flow returns all reserved stock by the end.

## Future Improvements

- **Reservation expiry:** a scheduled job (Celery beat or cron) that releases the stock held by carts left inactive for N minutes.
- **Authentication:** JWT or session auth, with carts linked to users and per-user rate limits.
- **Checkout and orders:** turn a cart into an order (`status = checked_out`), with payment integration and an order history.
- **Caching:** cache product lists and details (for example in Redis) and invalidate them when stock or prices change.
- **Docker:** a `Dockerfile` and `docker-compose.yml` (API + PostgreSQL) for one-command setup and deployment.
