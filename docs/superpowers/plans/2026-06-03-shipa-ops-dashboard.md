# SHIPA Ops Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only Shipa ops dashboard (Orders + Customers, with a geographic delivery map per order) wired to the live FastAPI API, plus the minimal backend read endpoints and coordinate data it needs.

**Architecture:** Add four coordinate columns + four ops-facing read endpoints (`/orders`, `/orders/{id}`, `/customers`, `/customers/{id}`) to the existing FastAPI dashboard router (API-key auth). Build a new `frontend/` Next.js (App Router) app that fetches the API server-side (key stays in server env) and renders tables + a Leaflet/OpenStreetMap map. Mock data is already behind the endpoints, so later real-Twin integration is backend-only.

**Tech Stack:** Backend — FastAPI, SQLAlchemy 2.0, Alembic, pytest, uv. Frontend — Next.js (App Router) + TypeScript + Tailwind CSS, Leaflet + react-leaflet.

**Spec:** `docs/superpowers/specs/2026-06-03-shipa-dashboard-frontend-design.md`

---

## Phase A — Backend

### Task 1: Add coordinate columns to the Order model

**Files:**
- Modify: `app/models/read.py` (the `Order` class)

- [ ] **Step 1: Write the failing test**

Create `tests/test_order_coords.py`:

```python
from app.models import Order


def test_order_has_coordinate_columns():
    cols = Order.__table__.columns.keys()
    for c in ("merchant_lat", "merchant_lng", "delivery_lat", "delivery_lng"):
        assert c in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_order_coords.py -v`
Expected: FAIL — `merchant_lat` not in columns.

- [ ] **Step 3: Add the columns**

In `app/models/read.py`, inside class `Order`, after the `expected_pieces` line and before `last_synced_at`:

```python
    merchant_lat: Mapped[float | None] = mapped_column(nullable=True)
    merchant_lng: Mapped[float | None] = mapped_column(nullable=True)
    delivery_lat: Mapped[float | None] = mapped_column(nullable=True)
    delivery_lng: Mapped[float | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_order_coords.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/read.py tests/test_order_coords.py
git commit -m "feat(db): add lat/lng coordinate columns to orders"
```

---

### Task 2: Plumb coordinates through the Twin adapter + sync

**Files:**
- Modify: `app/twin/base.py` (`OrderRecord`)
- Modify: `app/twin/sync.py` (`upsert_orders`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_sync_coords.py`:

```python
from app.models import Order
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders


def test_upsert_persists_coordinates(db):
    rec = OrderRecord(
        twin_order_ref="TWIN-COORD", customer_name="Coord Tester",
        customer_phone="+971500009999", merchant="Amazon", status="pending",
        delivery_address="Somewhere", merchant_lat=24.918, merchant_lng=55.161,
        delivery_lat=25.0805, delivery_lng=55.1403,
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-COORD").one()
    assert (o.merchant_lat, o.merchant_lng) == (24.918, 55.161)
    assert (o.delivery_lat, o.delivery_lng) == (25.0805, 55.1403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sync_coords.py -v`
Expected: FAIL — `OrderRecord` has no `merchant_lat` kwarg (`TypeError`).

- [ ] **Step 3: Add fields to `OrderRecord`**

In `app/twin/base.py`, add to the `OrderRecord` dataclass after `twin_customer_ref`:

```python
    merchant_lat: float | None = None
    merchant_lng: float | None = None
    delivery_lat: float | None = None
    delivery_lng: float | None = None
```

- [ ] **Step 4: Copy fields through `upsert_orders`**

In `app/twin/sync.py`, in `upsert_orders`, after the `order.expected_pieces = rec.expected_pieces` line:

```python
        order.merchant_lat = rec.merchant_lat
        order.merchant_lng = rec.merchant_lng
        order.delivery_lat = rec.delivery_lat
        order.delivery_lng = rec.delivery_lng
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_sync_coords.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/twin/base.py app/twin/sync.py tests/test_sync_coords.py
git commit -m "feat(twin): carry order coordinates through adapter and sync"
```

---

### Task 3: Seed coordinates in the mock client

**Files:**
- Modify: `app/twin/mock.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mock_coords.py`:

```python
from app.twin.mock import MockTwinClient


def test_mock_orders_all_have_coordinates():
    for rec in MockTwinClient().fetch_all():
        assert rec.merchant_lat is not None and rec.merchant_lng is not None
        assert rec.delivery_lat is not None and rec.delivery_lng is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mock_coords.py -v`
Expected: FAIL — coordinates are `None`.

- [ ] **Step 3: Add coordinates to each seed record**

In `app/twin/mock.py`, add the four coordinate kwargs to each `OrderRecord` in `_SEED`:

```python
_SEED = [
    OrderRecord(
        twin_order_ref="TWIN-1001", customer_name="Aisha Khan", customer_phone="+971500000001",
        merchant="Amazon", status="out_for_delivery", delivery_address="Apt 12, Marina Gate 1, Dubai Marina",
        delivery_area="Dubai Marina", delivery_window="2026-06-03 09:00-12:00", otp_code="4821",
        assigned_driver="Rahul P.", expected_pieces=1, language_pref="en",
        merchant_lat=24.9180, merchant_lng=55.1610, delivery_lat=25.0805, delivery_lng=55.1403,
    ),
    OrderRecord(
        twin_order_ref="TWIN-1002", customer_name="Omar Al Farsi", customer_phone="+971500000002",
        merchant="Temu", status="failed", delivery_address="Villa 7, Al Barsha 2",
        delivery_area="Al Barsha", delivery_window="2026-06-02 14:00-18:00", otp_code="7310",
        assigned_driver="Sara M.", expected_pieces=3, language_pref="ar",
        merchant_lat=24.9700, merchant_lng=55.1800, delivery_lat=25.1107, delivery_lng=55.2014,
    ),
    OrderRecord(
        twin_order_ref="TWIN-1003", customer_name="Fatima Noor", customer_phone="+971500000003",
        merchant="Trendyol", status="delivered", delivery_address="Office 401, Business Bay Tower",
        delivery_area="Business Bay", delivery_window="2026-06-01 10:00-13:00", otp_code="1599",
        assigned_driver="Ali K.", expected_pieces=2, language_pref="en",
        merchant_lat=25.1200, merchant_lng=55.2000, delivery_lat=25.1857, delivery_lng=55.2645,
    ),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mock_coords.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/twin/mock.py tests/test_mock_coords.py
git commit -m "feat(twin): seed Dubai coordinates on mock orders"
```

---

### Task 4: Read-view schemas

**Files:**
- Modify: `app/schemas/dashboard.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_read_view_schemas.py`:

```python
from app.schemas.dashboard import CustomerBrief, OrderDetail


def test_order_detail_excludes_otp():
    assert "otp_code" not in OrderDetail.model_fields
    assert "customer" in OrderDetail.model_fields
    assert "delivery_lat" in OrderDetail.model_fields


def test_customer_brief_fields():
    assert set(CustomerBrief.model_fields) >= {"customer_id", "full_name", "primary_phone", "language_pref"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_read_view_schemas.py -v`
Expected: FAIL — `ImportError: cannot import name 'CustomerBrief'`.

- [ ] **Step 3: Add the schemas**

Append to `app/schemas/dashboard.py` (the file already imports `datetime as dt`, `uuid`, and `BaseModel`):

```python
class CustomerBrief(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    customer_name: str


class OrderDetail(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    expected_pieces: int | None
    merchant_lat: float | None
    merchant_lng: float | None
    delivery_lat: float | None
    delivery_lng: float | None
    last_synced_at: dt.datetime
    customer: CustomerBrief
    # deliberately no otp_code


class CustomerListItem(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    order_count: int


class CustomerDetail(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    orders: list[OrderListItem]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_read_view_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/dashboard.py tests/test_read_view_schemas.py
git commit -m "feat(api): add order/customer read-view schemas"
```

---

### Task 5: Order read services

**Files:**
- Modify: `app/services/orders.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_orders_service.py`:

```python
from app.services.orders import get_order_detail, list_orders
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_list_orders_includes_customer_name(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    items = list_orders(db)
    assert len(items) == 3
    aisha = next(i for i in items if i.twin_order_ref == "TWIN-1001")
    assert aisha.customer_name == "Aisha Khan"


def test_get_order_detail_has_coords_and_customer(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    oid = next(o.order_id for o in orders if o.twin_order_ref == "TWIN-1001")
    detail = get_order_detail(db, oid)
    assert detail.delivery_lat == 25.0805
    assert detail.customer.full_name == "Aisha Khan"


def test_get_order_detail_missing_returns_none(db):
    import uuid
    assert get_order_detail(db, uuid.uuid4()) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orders_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'list_orders'`.

- [ ] **Step 3: Add the services**

In `app/services/orders.py`, add to the imports at top:

```python
from app.models import Customer  # noqa: F401  (kept for type clarity)
from app.schemas.dashboard import CustomerBrief, OrderDetail, OrderListItem
```

Then append:

```python
def _order_list_item(o: Order) -> OrderListItem:
    return OrderListItem(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_area=o.delivery_area, delivery_window=o.delivery_window,
        assigned_driver=o.assigned_driver, customer_name=o.customer.full_name,
    )


def list_orders(db: Session) -> list[OrderListItem]:
    orders = db.query(Order).order_by(Order.twin_order_ref).all()
    return [_order_list_item(o) for o in orders]


def get_order_detail(db: Session, order_id: uuid.UUID) -> OrderDetail | None:
    o = db.get(Order, order_id)
    if o is None:
        return None
    return OrderDetail(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_address=o.delivery_address, delivery_area=o.delivery_area,
        delivery_window=o.delivery_window, assigned_driver=o.assigned_driver,
        expected_pieces=o.expected_pieces, merchant_lat=o.merchant_lat, merchant_lng=o.merchant_lng,
        delivery_lat=o.delivery_lat, delivery_lng=o.delivery_lng, last_synced_at=o.last_synced_at,
        customer=CustomerBrief.model_validate(o.customer),
    )
```

(The `_order_list_item` helper is reused by the customer service in Task 6 — import it there.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_orders_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/orders.py tests/test_orders_service.py
git commit -m "feat(api): add list_orders and get_order_detail services"
```

---

### Task 6: Customer read services

**Files:**
- Create: `app/services/customers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_customers_service.py`:

```python
from app.models import Customer
from app.services.customers import get_customer_detail, list_customers
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_list_customers_counts_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    items = list_customers(db)
    assert len(items) == 3
    assert all(i.order_count == 1 for i in items)


def test_get_customer_detail_lists_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    cid = db.query(Customer).filter_by(full_name="Aisha Khan").one().customer_id
    detail = get_customer_detail(db, cid)
    assert detail.full_name == "Aisha Khan"
    assert detail.orders[0].twin_order_ref == "TWIN-1001"


def test_get_customer_detail_missing_returns_none(db):
    import uuid
    assert get_customer_detail(db, uuid.uuid4()) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_customers_service.py -v`
Expected: FAIL — module `app.services.customers` does not exist.

- [ ] **Step 3: Create the service**

Create `app/services/customers.py`:

```python
import uuid

from sqlalchemy.orm import Session

from app.models import Customer
from app.schemas.dashboard import CustomerDetail, CustomerListItem
from app.services.orders import _order_list_item


def list_customers(db: Session) -> list[CustomerListItem]:
    customers = db.query(Customer).order_by(Customer.full_name).all()
    return [
        CustomerListItem(
            customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
            language_pref=c.language_pref, order_count=len(c.orders),
        )
        for c in customers
    ]


def get_customer_detail(db: Session, customer_id: uuid.UUID) -> CustomerDetail | None:
    c = db.get(Customer, customer_id)
    if c is None:
        return None
    return CustomerDetail(
        customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
        language_pref=c.language_pref,
        orders=[_order_list_item(o) for o in sorted(c.orders, key=lambda o: o.twin_order_ref)],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_customers_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/customers.py tests/test_customers_service.py
git commit -m "feat(api): add list_customers and get_customer_detail services"
```

---

### Task 7: Dashboard read endpoints

**Files:**
- Modify: `app/routers/dashboard.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_read_endpoints.py`:

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

APIKEY = {"X-API-Key": "dev-dashboard-key-change-me"}


@pytest.fixture()
def seeded(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def test_orders_requires_api_key(client, seeded):
    assert client.get("/orders").status_code == 401


def test_orders_list(client, seeded):
    r = client.get("/orders", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    assert body[0]["customer_name"]
    assert "otp_code" not in body[0]


def test_order_detail_has_coords_no_otp(client, seeded):
    oid = client.get("/orders", headers=APIKEY).json()[0]["order_id"]
    r = client.get(f"/orders/{oid}", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    assert "delivery_lat" in body and "merchant_lat" in body
    assert body["customer"]["full_name"]
    assert "otp_code" not in body


def test_order_detail_404(client, seeded):
    import uuid
    assert client.get(f"/orders/{uuid.uuid4()}", headers=APIKEY).status_code == 404


def test_customers_list_and_detail(client, seeded):
    lst = client.get("/customers", headers=APIKEY)
    assert lst.status_code == 200
    assert lst.json()[0]["order_count"] >= 1
    cid = lst.json()[0]["customer_id"]
    det = client.get(f"/customers/{cid}", headers=APIKEY)
    assert det.status_code == 200
    assert "orders" in det.json()


def test_customer_detail_404(client, seeded):
    import uuid
    assert client.get(f"/customers/{uuid.uuid4()}", headers=APIKEY).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_read_endpoints.py -v`
Expected: FAIL — `/orders` returns 404 (route not defined) instead of 401.

- [ ] **Step 3: Add the endpoints**

Replace the top of `app/routers/dashboard.py` imports block with:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Call, Escalation, Investigation, Reschedule
from app.schemas.dashboard import (
    CallSummary, CustomerDetail, CustomerListItem, EscalationSummary, InvestigationSummary,
    Metrics, OrderDetail, OrderListItem, RescheduleSummary,
)
from app.services.customers import get_customer_detail, list_customers
from app.services.metrics import compute_metrics
from app.services.orders import get_order_detail, list_orders
```

Then add these routes (place them after the existing `metrics` route):

```python
@router.get("/orders", response_model=list[OrderListItem])
def orders_list(db: Session = Depends(get_db)):
    return list_orders(db)


@router.get("/orders/{order_id}", response_model=OrderDetail)
def order_detail(order_id: uuid.UUID, db: Session = Depends(get_db)):
    detail = get_order_detail(db, order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="order not found")
    return detail


@router.get("/customers", response_model=list[CustomerListItem])
def customers_list(db: Session = Depends(get_db)):
    return list_customers(db)


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
def customer_detail(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    detail = get_customer_detail(db, customer_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return detail
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_read_endpoints.py -v`
Expected: PASS (all 6).

- [ ] **Step 5: Commit**

```bash
git add app/routers/dashboard.py tests/test_read_endpoints.py
git commit -m "feat(api): add /orders and /customers read endpoints"
```

---

### Task 8: CORS middleware

**Files:**
- Modify: `app/main.py`
- Modify: `app/config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cors.py`:

```python
def test_cors_preflight_allows_frontend(client):
    r = client.options(
        "/orders",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cors.py -v`
Expected: FAIL — no `access-control-allow-origin` header.

- [ ] **Step 3: Add a config setting and the middleware**

In `app/config.py`, add a field to `Settings` after `verification_max_attempts`:

```python
    frontend_origin: str = "http://localhost:3000"
```

In `app/main.py`, inside `create_app()` right after `app = FastAPI(...)`:

```python
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["X-API-Key"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cors.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `uv run pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/config.py tests/test_cors.py
git commit -m "feat(api): allow CORS from the dashboard frontend origin"
```

---

### Task 9: Alembic migration + SQL seed coordinates

**Files:**
- Create: `migrations/versions/<generated>_add_order_coordinates.py`
- Modify: `db/seed_twin_mock.sql`

- [ ] **Step 1: Generate the migration skeleton**

Run: `uv run alembic revision -m "add order coordinates"`
This prints a path like `migrations/versions/<id>_add_order_coordinates.py`. Open it.

- [ ] **Step 2: Fill in upgrade/downgrade**

Replace the generated `upgrade()` and `downgrade()` bodies (keep the auto-generated `revision`/`down_revision` lines — `down_revision` should already be `'a9e1dcce6457'`):

```python
def upgrade() -> None:
    op.add_column("orders", sa.Column("merchant_lat", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("merchant_lng", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("delivery_lat", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("delivery_lng", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_lng")
    op.drop_column("orders", "delivery_lat")
    op.drop_column("orders", "merchant_lng")
    op.drop_column("orders", "merchant_lat")
```

Ensure `import sqlalchemy as sa` and `from alembic import op` are present at the top (the template includes them).

- [ ] **Step 3: Apply and verify the migration**

Run: `docker compose up -d db && uv run alembic upgrade head`
Expected: completes without error.
Run: `uv run alembic downgrade -1 && uv run alembic upgrade head`
Expected: down then up both succeed (confirms `downgrade` works).

- [ ] **Step 4: Add coordinates to the SQL seed**

In `db/seed_twin_mock.sql`, update the `orders` INSERT to include the four coordinate columns. Replace the column list and each VALUES row with coordinates (use the same area→coord mapping as the mock; merchant hub by merchant). Column list:

```sql
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address, delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at) VALUES
```

Append the four coordinate values before `now()` on each row, using this mapping:

| twin_order_ref | merchant_lat, merchant_lng | delivery_lat, delivery_lng |
|---|---|---|
| TWIN-1001 (Amazon / Dubai Marina) | 24.9180, 55.1610 | 25.0805, 55.1403 |
| TWIN-1002 (Temu / Al Barsha) | 24.9700, 55.1800 | 25.1107, 55.2014 |
| TWIN-1003 (Trendyol / Business Bay) | 25.1200, 55.2000 | 25.1857, 55.2645 |
| TWIN-1004 (Amazon / Deira) | 24.9180, 55.1610 | 25.2730, 55.3050 |
| TWIN-1005 (Noon / Deira) | 24.9700, 55.1800 | 25.2730, 55.3050 |
| TWIN-1006 (Trendyol / JLT) | 25.1200, 55.2000 | 25.0693, 55.1440 |

Example for the TWIN-1001 row (insert the four numbers before `now()`):

```sql
  (gen_random_uuid(), 'TWIN-1001', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-1'),
   'Amazon',   'out_for_delivery', 'Apt 12, Marina Gate 1, Dubai Marina', 'Dubai Marina',  '2026-06-03 09:00-12:00', '4821', 'Rahul P.', 1, 24.9180, 55.1610, 25.0805, 55.1403, now()),
```

- [ ] **Step 5: Re-seed and verify**

Run: `uv run alembic upgrade head` (ensure schema current), then load the seed:
`docker compose exec -T db psql -U shipa -d shipa < db/seed_twin_mock.sql`
Verify: `docker compose exec -T db psql -U shipa -d shipa -c "SELECT twin_order_ref, delivery_lat, delivery_lng FROM orders ORDER BY twin_order_ref;"`
Expected: every row has non-null coordinates.

- [ ] **Step 6: Commit**

```bash
git add migrations/versions/*add_order_coordinates*.py db/seed_twin_mock.sql
git commit -m "feat(db): migration + seed for order coordinates"
```

---

## Phase B — Frontend

### Task 10: Scaffold the Next.js app

**Files:**
- Create: `frontend/` (via create-next-app)

- [ ] **Step 1: Scaffold**

Run from the repo root:

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --eslint --no-src-dir --import-alias "@/*" --use-npm
```

Accept defaults for any remaining prompts (Turbopack: yes is fine).

- [ ] **Step 2: Install map dependencies**

```bash
cd frontend && npm install leaflet react-leaflet && npm install -D @types/leaflet && cd ..
```

- [ ] **Step 3: Verify the dev server boots**

Run: `cd frontend && npm run build && cd ..`
Expected: build succeeds (the default starter page compiles).

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "chore(frontend): scaffold Next.js app with Tailwind + Leaflet"
```

---

### Task 11: Brand theme, env, and types

**Files:**
- Modify: `frontend/app/globals.css`
- Create: `frontend/.env.example`
- Create: `frontend/lib/types.ts`

- [ ] **Step 1: Define brand tokens (Tailwind v4 `@theme`)**

In `frontend/app/globals.css`, keep the existing `@import "tailwindcss";` line at the top and add below it:

```css
@theme {
  --color-shipa-blue: #2b3ff2;
  --color-shipa-blue-dark: #1e2fc4;
  --color-shipa-ink: #0b0d12;
  --color-shipa-sky: #e6f2f9;
  --color-shipa-sky-accent: #bbd9e8;
}

body {
  background: var(--color-shipa-sky);
  color: var(--color-shipa-ink);
}
```

> If `create-next-app` scaffolded Tailwind v3 instead (a `tailwind.config.ts` exists and `globals.css` uses `@tailwind base;`), then instead add the colors under `theme.extend.colors` in `tailwind.config.ts`:
> ```ts
> colors: { "shipa-blue": "#2b3ff2", "shipa-blue-dark": "#1e2fc4", "shipa-ink": "#0b0d12", "shipa-sky": "#e6f2f9", "shipa-sky-accent": "#bbd9e8" }
> ```

- [ ] **Step 2: Create the env example**

Create `frontend/.env.example`:

```
# Server-side only — never exposed to the browser
API_BASE_URL=http://localhost:8000
DASHBOARD_API_KEY=dev-dashboard-key-change-me
```

Then create a working `frontend/.env.local` with the same two lines (it is gitignored by the starter).

- [ ] **Step 3: Create TypeScript types mirroring the API**

Create `frontend/lib/types.ts`:

```ts
export type OrderListItem = {
  order_id: string;
  twin_order_ref: string;
  merchant: string;
  status: string;
  delivery_area: string | null;
  delivery_window: string | null;
  assigned_driver: string | null;
  customer_name: string;
};

export type CustomerBrief = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
};

export type OrderDetail = {
  order_id: string;
  twin_order_ref: string;
  merchant: string;
  status: string;
  delivery_address: string;
  delivery_area: string | null;
  delivery_window: string | null;
  assigned_driver: string | null;
  expected_pieces: number | null;
  merchant_lat: number | null;
  merchant_lng: number | null;
  delivery_lat: number | null;
  delivery_lng: number | null;
  last_synced_at: string;
  customer: CustomerBrief;
};

export type CustomerListItem = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
  order_count: number;
};

export type CustomerDetail = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
  orders: OrderListItem[];
};
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css frontend/.env.example frontend/lib/types.ts
git commit -m "feat(frontend): brand theme tokens, env example, API types"
```

---

### Task 12: Server-side API access layer

**Files:**
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create the fetch layer**

Create `frontend/lib/api.ts`:

```ts
import type {
  CustomerDetail,
  CustomerListItem,
  OrderDetail,
  OrderListItem,
} from "@/lib/types";

const BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const KEY = process.env.DASHBOARD_API_KEY ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "X-API-Key": KEY },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getOrders = () => get<OrderListItem[]>("/orders");
export const getOrder = (id: string) => get<OrderDetail>(`/orders/${id}`);
export const getCustomers = () => get<CustomerListItem[]>("/customers");
export const getCustomer = (id: string) => get<CustomerDetail>(`/customers/${id}`);
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): server-side API access layer"
```

---

### Task 13: App shell — TopBar, layout, status badge

**Files:**
- Create: `frontend/components/TopBar.tsx`
- Create: `frontend/components/StatusBadge.tsx`
- Create: `frontend/public/shipa-logo.svg`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Add the logo asset**

Create `frontend/public/shipa-logo.svg` (SHIPA wordmark + blue swoosh):

```svg
<svg width="120" height="28" viewBox="0 0 120 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <text x="0" y="21" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" letter-spacing="3" fill="#0b0d12">SHIPA</text>
  <path d="M96 20 L104 6 L112 24" stroke="#2b3ff2" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

- [ ] **Step 2: Create the TopBar**

Create `frontend/components/TopBar.tsx`:

```tsx
"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/orders", label: "Orders" },
  { href: "/customers", label: "Customers" },
];

export default function TopBar() {
  const pathname = usePathname();
  return (
    <header className="flex items-center gap-8 border-b border-shipa-sky-accent bg-white px-6 py-4">
      <Link href="/orders" className="flex items-center">
        <Image src="/shipa-logo.svg" alt="SHIPA" width={120} height={28} priority />
      </Link>
      <nav className="flex gap-6">
        {links.map((l) => {
          const active = pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={
                active
                  ? "font-semibold text-shipa-blue"
                  : "font-medium text-shipa-ink/70 hover:text-shipa-ink"
              }
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
```

- [ ] **Step 3: Create the StatusBadge**

Create `frontend/components/StatusBadge.tsx`:

```tsx
const STYLES: Record<string, string> = {
  delivered: "bg-green-100 text-green-800",
  out_for_delivery: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-amber-100 text-amber-800",
  rescheduled: "bg-slate-100 text-slate-700",
  returned: "bg-slate-100 text-slate-700",
  cancelled: "bg-slate-100 text-slate-700",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = STYLES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
```

- [ ] **Step 4: Wire the layout and root redirect**

Replace `frontend/app/layout.tsx` body with a version that renders `TopBar`. Keep the generated font setup if present; the key change is wrapping `children`:

```tsx
import type { Metadata } from "next";
import TopBar from "@/components/TopBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHIPA Ops Dashboard",
  description: "Orders, customers, and delivery map",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopBar />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

Replace `frontend/app/page.tsx` with a redirect:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/orders");
}
```

- [ ] **Step 5: Type-check**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components frontend/public/shipa-logo.svg frontend/app/layout.tsx frontend/app/page.tsx
git commit -m "feat(frontend): app shell with SHIPA top bar and status badge"
```

---

### Task 14: Orders list page

**Files:**
- Create: `frontend/app/orders/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/app/orders/page.tsx`:

```tsx
import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { getOrders } from "@/lib/api";

export default async function OrdersPage() {
  const orders = await getOrders();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Orders</h1>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Customer</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Area</th>
              <th className="px-4 py-3 font-semibold">Driver</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {o.twin_order_ref}
                  </Link>
                </td>
                <td className="px-4 py-3">{o.customer_name}</td>
                <td className="px-4 py-3">{o.merchant}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3">{o.delivery_area ?? "—"}</td>
                <td className="px-4 py-3">{o.assigned_driver ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/orders/page.tsx
git commit -m "feat(frontend): orders list page"
```

---

### Task 15: DeliveryMap component (Leaflet)

**Files:**
- Create: `frontend/components/DeliveryMap.tsx`
- Create: `frontend/components/MapClient.tsx`

- [ ] **Step 1: Create the Leaflet map**

Create `frontend/components/DeliveryMap.tsx`:

```tsx
"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";

type LatLng = [number, number];

function pin(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:18px;height:18px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 18],
    popupAnchor: [0, -18],
  });
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) {
      map.setView(points[0], 13);
    } else if (points.length > 1) {
      map.fitBounds(points, { padding: [60, 60] });
    }
  }, [map, points]);
  return null;
}

export type DeliveryMapProps = {
  merchant: string;
  deliveryAddress: string;
  status: string;
  merchantLatLng: LatLng | null;
  deliveryLatLng: LatLng | null;
};

export default function DeliveryMap({
  merchant,
  deliveryAddress,
  status,
  merchantLatLng,
  deliveryLatLng,
}: DeliveryMapProps) {
  const points = [merchantLatLng, deliveryLatLng].filter(Boolean) as LatLng[];
  if (points.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
        Coordinates unavailable for this order.
      </div>
    );
  }
  return (
    <MapContainer
      center={points[0]}
      zoom={12}
      scrollWheelZoom={false}
      style={{ height: "420px", width: "100%", borderRadius: "0.75rem" }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {merchantLatLng && (
        <Marker position={merchantLatLng} icon={pin("#0b0d12")}>
          <Popup>
            <strong>{merchant}</strong>
            <br />
            Merchant origin
          </Popup>
        </Marker>
      )}
      {deliveryLatLng && (
        <Marker position={deliveryLatLng} icon={pin("#2b3ff2")}>
          <Popup>
            <strong>Delivery</strong>
            <br />
            {deliveryAddress}
            <br />
            Status: {status.replace(/_/g, " ")}
          </Popup>
        </Marker>
      )}
      {merchantLatLng && deliveryLatLng && (
        <Polyline positions={[merchantLatLng, deliveryLatLng]} pathOptions={{ color: "#2b3ff2", weight: 3, dashArray: "6 8" }} />
      )}
      <FitBounds points={points} />
    </MapContainer>
  );
}
```

- [ ] **Step 2: Create the SSR-safe client wrapper**

Create `frontend/components/MapClient.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import type { DeliveryMapProps } from "@/components/DeliveryMap";

const DeliveryMap = dynamic(() => import("@/components/DeliveryMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[420px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
      Loading map…
    </div>
  ),
});

export default function MapClient(props: DeliveryMapProps) {
  return <DeliveryMap {...props} />;
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/DeliveryMap.tsx frontend/components/MapClient.tsx
git commit -m "feat(frontend): Leaflet delivery map with merchant/delivery pins and route line"
```

---

### Task 16: Order detail page

**Files:**
- Create: `frontend/app/orders/[id]/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/app/orders/[id]/page.tsx`:

```tsx
import Link from "next/link";
import MapClient from "@/components/MapClient";
import StatusBadge from "@/components/StatusBadge";
import { getOrder } from "@/lib/api";

type LatLng = [number, number];

function pair(lat: number | null, lng: number | null): LatLng | null {
  return lat != null && lng != null ? [lat, lng] : null;
}

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const o = await getOrder(id);
  const rows: [string, string][] = [
    ["Merchant", o.merchant],
    ["Delivery address", o.delivery_address],
    ["Area", o.delivery_area ?? "—"],
    ["Window", o.delivery_window ?? "—"],
    ["Driver", o.assigned_driver ?? "—"],
    ["Pieces", o.expected_pieces?.toString() ?? "—"],
    ["Customer", `${o.customer.full_name} · ${o.customer.primary_phone}`],
  ];
  return (
    <div>
      <Link href="/orders" className="text-sm text-shipa-blue hover:underline">← Orders</Link>
      <div className="mb-6 mt-2 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-shipa-ink">{o.twin_order_ref}</h1>
        <StatusBadge status={o.status} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-shipa-sky-accent bg-white p-5">
          <dl className="divide-y divide-shipa-sky-accent">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
                <dt className="text-shipa-ink/60">{k}</dt>
                <dd className="text-right font-medium text-shipa-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
        <MapClient
          merchant={o.merchant}
          deliveryAddress={o.delivery_address}
          status={o.status}
          merchantLatLng={pair(o.merchant_lat, o.merchant_lng)}
          deliveryLatLng={pair(o.delivery_lat, o.delivery_lng)}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/orders/[id]/page.tsx"
git commit -m "feat(frontend): order detail page with delivery map"
```

---

### Task 17: Customers list + detail pages

**Files:**
- Create: `frontend/app/customers/page.tsx`
- Create: `frontend/app/customers/[id]/page.tsx`

- [ ] **Step 1: Create the customers list page**

Create `frontend/app/customers/page.tsx`:

```tsx
import Link from "next/link";
import { getCustomers } from "@/lib/api";

export default async function CustomersPage() {
  const customers = await getCustomers();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Customers</h1>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Phone</th>
              <th className="px-4 py-3 font-semibold">Language</th>
              <th className="px-4 py-3 font-semibold">Orders</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.customer_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">
                  <Link href={`/customers/${c.customer_id}`} className="font-medium text-shipa-blue hover:underline">
                    {c.full_name}
                  </Link>
                </td>
                <td className="px-4 py-3">{c.primary_phone}</td>
                <td className="px-4 py-3">{c.language_pref ?? "—"}</td>
                <td className="px-4 py-3">{c.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the customer detail page**

Create `frontend/app/customers/[id]/page.tsx`:

```tsx
import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { getCustomer } from "@/lib/api";

export default async function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await getCustomer(id);
  return (
    <div>
      <Link href="/customers" className="text-sm text-shipa-blue hover:underline">← Customers</Link>
      <h1 className="mb-1 mt-2 text-2xl font-bold text-shipa-ink">{c.full_name}</h1>
      <p className="mb-6 text-sm text-shipa-ink/60">
        {c.primary_phone}
        {c.language_pref ? ` · ${c.language_pref}` : ""}
      </p>
      <h2 className="mb-3 text-lg font-semibold text-shipa-ink">Orders</h2>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Area</th>
            </tr>
          </thead>
          <tbody>
            {c.orders.map((o) => (
              <tr key={o.order_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {o.twin_order_ref}
                  </Link>
                </td>
                <td className="px-4 py-3">{o.merchant}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3">{o.delivery_area ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build && cd ..`
Expected: type-check clean; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/customers
git commit -m "feat(frontend): customers list and detail pages"
```

---

### Task 18: End-to-end verification + README + push

**Files:**
- Create: `frontend/README.md`
- Modify: `README.md` (add a Dashboard section)

- [ ] **Step 1: Bring up backend with seeded data**

```bash
docker compose up -d db
uv run alembic upgrade head
docker compose exec -T db psql -U shipa -d shipa < db/seed_twin_mock.sql
uv run uvicorn app.main:app --reload
```

In another shell, confirm the API:
`curl -s -H "X-API-Key: dev-dashboard-key-change-me" http://localhost:8000/orders | head`
Expected: JSON array of orders with `customer_name`.

- [ ] **Step 2: Run the frontend and verify manually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Verify:
- Redirects to `/orders`; table lists seeded orders with status badges.
- Click an order → detail shows the info card AND a map with **two pins** (dark merchant, blue delivery) joined by a dashed **route line**, auto-fitted to both.
- `/customers` lists customers with order counts; a customer detail lists their orders, each linking to the order map.
- SHIPA logo + blue accent present throughout.

- [ ] **Step 3: Write the frontend README**

Create `frontend/README.md`:

```markdown
# SHIPA Ops Dashboard (frontend)

Next.js + Tailwind + Leaflet dashboard for Shipa ops: orders, customers, and a per-order delivery map.

## Run
```bash
cp .env.example .env.local   # set API_BASE_URL + DASHBOARD_API_KEY
npm install
npm run dev                  # http://localhost:3000
```

Requires the FastAPI backend running and seeded (see repo root README). Data is fetched
server-side; the API key never reaches the browser.
```

Add to the repo-root `README.md`, after the "Seed mock orders" section:

```markdown
## Dashboard (frontend)
A Next.js ops dashboard lives in `frontend/` (orders, customers, delivery map). See `frontend/README.md`.
```

- [ ] **Step 4: Commit**

```bash
git add frontend/README.md README.md
git commit -m "docs(frontend): dashboard run instructions"
```

- [ ] **Step 5: Push to GitHub**

```bash
git push -u origin HEAD
```

Then open a PR (the work is on a feature branch off `main`).

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** schema/coords (T1–3, T9), endpoints (T4–8), CORS (T8), Next scaffold (T10), brand (T11/T13), API layer (T12), orders screens (T14, T16), map (T15), customers screens (T17), verification + push (T18). All §4–§7 spec items map to a task.
- **OTP safety:** `OrderDetail` has no `otp_code` (T4) and an endpoint test pins its absence (T7) — matches the backend spec's OTP discipline.
- **Type consistency:** `DeliveryMapProps` is defined in `DeliveryMap.tsx` (T15) and imported by `MapClient.tsx` (T15) and used in the order detail page (T16). API `lib/types.ts` (T11) field names match the Pydantic schemas (T4) exactly.
- **Tailwind version caveat:** Task 11 covers both v4 (`@theme` in CSS) and v3 (`tailwind.config.ts`) — check which `create-next-app` produced before editing.
- **Next params:** dynamic route pages `await params` (Next 15+ Promise params) in T16/T17.
```
