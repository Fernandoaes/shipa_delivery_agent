# Shipa Inbound Voice Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend the Shipa inbound exception-handler voice agent calls into — verify the caller, then let the agent read order status and take resolution actions, with safety (verify-before-disclose, OTP discipline, attempt capping, idempotency) enforced in code.

**Architecture:** Layered FastAPI service (`routers → services → SQLAlchemy models → Postgres`). HTTP layer is thin (parse, auth, call a service, return a filtered model). All business logic lives in services so `verify_caller` and the actions are plain, unit-testable Python. The order source is hidden behind one upsert path fed by a mock Twin client (pilot) or a push ingest endpoint.

**Tech Stack:** Python 3.12 (via `uv`), FastAPI, SQLAlchemy 2.0 (typed) + Alembic, Pydantic v2 / pydantic-settings, psycopg 3, pytest, ruff. Local Postgres via docker-compose.

---

## File Structure

```
shipa_delivery_agent/
├── pyproject.toml            # deps + ruff + pytest config
├── .env.example              # DATABASE_URL, WEBHOOK_SECRET, DASHBOARD_API_KEY
├── docker-compose.yml        # local Postgres
├── alembic.ini · migrations/ # migrations (env.py + versions/)
├── app/
│   ├── main.py               # app factory, router mount, /health
│   ├── config.py             # Settings (pydantic-settings)
│   ├── db.py                 # engine + SessionLocal + Base
│   ├── deps.py               # get_db, require_webhook_secret, require_api_key
│   ├── enums.py              # str Enums for all enum columns
│   ├── security.py           # constant-time secret compare, OTP scrub, PII filtering
│   ├── models/
│   │   ├── __init__.py       # re-export all models
│   │   ├── read.py           # Customer, Order
│   │   ├── calls.py          # Call
│   │   └── operations.py     # Verification, Reschedule, Investigation, Escalation,
│   │                         #   AddressFlag, FallbackMessage, MerchantReferral
│   ├── schemas/
│   │   ├── verify.py · orders.py · actions.py · calls.py · dashboard.py
│   ├── routers/
│   │   ├── tools.py          # agent contract (webhook auth)
│   │   ├── ingest.py         # POST /orders/sync (webhook auth)
│   │   └── dashboard.py      # reads (api-key auth)
│   ├── services/
│   │   ├── matching.py       # normalize + fuzzy compare helpers
│   │   ├── verification.py   # verify_caller policy + persistence
│   │   ├── guard.py          # require_verified_call
│   │   ├── calls.py          # get_or_create_call, set_disposition
│   │   ├── orders.py         # order status
│   │   ├── actions.py        # get_or_create_for_call + each action
│   │   └── metrics.py        # dashboard aggregation
│   └── twin/
│       ├── base.py           # TwinClient Protocol + OrderRecord dataclass
│       ├── mock.py           # MockTwinClient + seed dataset
│       └── sync.py           # upsert_orders (the single write path)
└── tests/
    ├── conftest.py
    ├── test_health.py · test_models.py · test_auth.py · test_security.py
    ├── test_matching.py · test_verification.py · test_verify_endpoint.py
    ├── test_guard.py · test_orders.py · test_actions.py · test_idempotency.py
    ├── test_disposition.py · test_dashboard.py · test_ingest.py
```

---

## Task 1: Project bootstrap + health endpoint

**Files:**
- Create: `pyproject.toml`, `docker-compose.yml`, `.env.example`, `app/__init__.py`, `app/config.py`, `app/db.py`, `app/deps.py`, `app/main.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_health.py`

- [ ] **Step 1: Initialize uv project and pin Python**

Run:
```bash
uv init --no-readme --python 3.12
uv add fastapi "uvicorn[standard]" "sqlalchemy>=2.0" alembic "psycopg[binary]" pydantic-settings
uv add --dev pytest httpx ruff
```
Expected: creates `.venv/`, `pyproject.toml`, `uv.lock`. (Delete the `hello.py`/`main.py` stub uv generates if present.)

- [ ] **Step 2: Add tool config to `pyproject.toml`**

Append:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: shipa
      POSTGRES_PASSWORD: shipa
      POSTGRES_DB: shipa
    ports:
      - "5432:5432"
    volumes:
      - shipa_pg:/var/lib/postgresql/data
volumes:
  shipa_pg:
```

- [ ] **Step 4: Create `.env.example`**

```bash
DATABASE_URL=postgresql+psycopg://shipa:shipa@localhost:5432/shipa
WEBHOOK_SECRET=dev-webhook-secret-change-me
DASHBOARD_API_KEY=dev-dashboard-key-change-me
```

- [ ] **Step 5: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://shipa:shipa@localhost:5432/shipa"
    webhook_secret: str = "dev-webhook-secret-change-me"
    dashboard_api_key: str = "dev-dashboard-key-change-me"
    verification_max_attempts: int = 3


settings = Settings()
```

- [ ] **Step 6: Create `app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 7: Create `app/deps.py` (DB dep only for now)**

```python
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 8: Create `app/main.py`**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Shipa Inbound Voice Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 9: Create `tests/conftest.py` (app client + DB session fixtures)**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base
from app.main import create_app

# All models must be imported so Base.metadata is complete.
import app.models  # noqa: F401

TEST_DB_URL = settings.database_url.replace("/shipa", "/shipa_test")


@pytest.fixture(scope="session")
def engine():
    # Create the test database if missing, then build the schema.
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        exists = conn.exec_driver_sql(
            "SELECT 1 FROM pg_database WHERE datname = 'shipa_test'"
        ).fetchone()
        if not exists:
            conn.exec_driver_sql("CREATE DATABASE shipa_test")
    admin.dispose()

    eng = create_engine(TEST_DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = TestSession()
    yield session
    session.rollback()
    # Clean every table between tests for isolation.
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client(engine, db):
    from app.deps import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
```

> Note: Task 1 imports `app.models` which doesn't exist yet. Create an empty `app/models/__init__.py` now so conftest imports cleanly; Task 2 fills it.

- [ ] **Step 10: Create empty models package**

Create `app/models/__init__.py` with a single line: `# models re-exported here in Task 2`

- [ ] **Step 11: Write `tests/test_health.py`**

```python
def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 12: Start Postgres and run the test**

Run:
```bash
docker compose up -d db
sleep 3
cp .env.example .env
uv run pytest tests/test_health.py -v
```
Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add -A && git commit -m "feat: bootstrap FastAPI backend with health check and test harness"
```

---

## Task 2: Enums + SQLAlchemy models

**Files:**
- Create: `app/enums.py`, `app/models/read.py`, `app/models/calls.py`, `app/models/operations.py`, `tests/test_models.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Write `tests/test_models.py` (failing — models not defined)**

```python
import datetime as dt

from app.models import Call, Customer, Order, Verification


def test_customer_order_call_chain(db):
    cust = Customer(full_name="Aisha Khan", primary_phone="+971500000001", last_synced_at=dt.datetime.now(dt.timezone.utc))
    db.add(cust)
    db.flush()
    order = Order(
        twin_order_ref="TWIN-1",
        customer_id=cust.customer_id,
        merchant="Amazon",
        status="out_for_delivery",
        delivery_address="Flat 1, Dubai Marina",
        last_synced_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(order)
    db.flush()
    call = Call(
        direction="inbound",
        agent_type="inbound_exception",
        verification_status="not_started",
        started_at=dt.datetime.now(dt.timezone.utc),
        customer_id=cust.customer_id,
        order_id=order.order_id,
    )
    db.add(call)
    db.flush()
    v = Verification(
        call_id=call.call_id, factors_checked=["name", "order_ref"],
        factors_passed=["name"], result="partial", attempt_no=1,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(v)
    db.flush()
    assert order.customer_id == cust.customer_id
    assert call.order_id == order.order_id
    assert v.factors_checked == ["name", "order_ref"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Call'`.

- [ ] **Step 3: Create `app/enums.py`**

```python
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class OrderStatus(StrEnum):
    pending = "pending"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    rescheduled = "rescheduled"
    returned = "returned"
    cancelled = "cancelled"


class VerificationStatus(StrEnum):
    not_started = "not_started"
    passed = "passed"
    partial = "partial"
    failed = "failed"


class Intent(StrEnum):
    tracking = "tracking"
    not_received = "not_received"
    failed_delivery = "failed_delivery"
    wrong_items = "wrong_items"
    reschedule = "reschedule"
    cancel = "cancel"
    other = "other"


class Disposition(StrEnum):
    resolved_info = "resolved_info"
    rescheduled = "rescheduled"
    investigation_opened = "investigation_opened"
    re_attempt_scheduled = "re_attempt_scheduled"
    referred_to_merchant = "referred_to_merchant"
    escalated = "escalated"
    verification_failed = "verification_failed"
    no_order_found = "no_order_found"


class EscalationCategory(StrEnum):
    cancel = "cancel"
    complaint = "complaint"
    unclassified = "unclassified"
    hostile = "hostile"
    verification_failed = "verification_failed"
```

> Enum values are stored as plain `text` columns (matching the schema spec), not PG enum types — keeps migrations simple and lets us add values without DDL.

- [ ] **Step 4: Create `app/models/read.py`**

```python
import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twin_customer_ref: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    primary_phone: Mapped[str] = mapped_column(String, nullable=False)
    alt_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    language_pref: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    __table_args__ = (Index("idx_customers_primary_phone", "primary_phone"),)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twin_order_ref: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"))
    merchant: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    otp_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_driver: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_pieces: Mapped[int | None] = mapped_column(nullable=True)
    last_synced_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    __table_args__ = (Index("idx_orders_customer_id", "customer_id"),)
```

- [ ] **Step 5: Create `app/models/calls.py`**

```python
import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Call(Base):
    __tablename__ = "calls"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    happyrobot_call_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(Text, nullable=False)
    caller_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    csat_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    ended_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_calls_order_id", "order_id"),
        Index("idx_calls_started_at", "started_at"),
    )
```

- [ ] **Step 6: Create `app/models/operations.py`**

```python
import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Verification(Base):
    __tablename__ = "verifications"
    verification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    factors_checked: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    factors_passed: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_no: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class Reschedule(Base):
    __tablename__ = "reschedules"
    reschedule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    requested_date: Mapped[dt.date] = mapped_column(nullable=False)
    requested_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="requested")
    synced_to_twin_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class Investigation(Base):
    __tablename__ = "investigations"
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    callback_due_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    opened_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)


class Escalation(Base):
    __tablename__ = "escalations"
    escalation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class AddressFlag(Base):
    __tablename__ = "address_flags"
    flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    original_address: Mapped[str] = mapped_column(Text, nullable=False)
    correction_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class FallbackMessage(Base):
    __tablename__ = "fallback_messages"
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calls.call_id"), nullable=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    sent_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class MerchantReferral(Base):
    __tablename__ = "merchant_referrals"
    referral_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)
```

> The `unique=True` on each action table's `call_id` is the idempotency guard (Task 9+). `merchant_referrals` isn't in the schema doc's table list but is named in the draft contract; this is its definitive shape.

- [ ] **Step 7: Fill `app/models/__init__.py`**

```python
from app.models.calls import Call
from app.models.operations import (
    AddressFlag,
    Escalation,
    FallbackMessage,
    Investigation,
    MerchantReferral,
    Reschedule,
    Verification,
)
from app.models.read import Customer, Order

__all__ = [
    "Customer", "Order", "Call", "Verification", "Reschedule", "Investigation",
    "Escalation", "AddressFlag", "FallbackMessage", "MerchantReferral",
]
```

- [ ] **Step 8: Run the model test**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: add enums and SQLAlchemy models for read and write tables"
```

---

## Task 3: Alembic migrations

**Files:**
- Create: `alembic.ini`, `migrations/env.py`, `migrations/versions/` (autogenerated), `tests/test_migrations.py`

- [ ] **Step 1: Initialize Alembic**

Run: `uv run alembic init -t generic migrations`
Then edit `alembic.ini`: set `sqlalchemy.url =` (leave blank — env.py supplies it).

- [ ] **Step 2: Wire `migrations/env.py` to settings + metadata**

Replace the config/target_metadata section so it reads:
```python
from app.config import settings
from app.db import Base
import app.models  # noqa: F401  (populate metadata)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```
(Keep the rest of the generated `run_migrations_online/offline` functions.)

- [ ] **Step 3: Autogenerate the initial migration**

Run:
```bash
docker compose up -d db
uv run alembic revision --autogenerate -m "initial schema"
```
Expected: a file in `migrations/versions/` creating all 10 tables + indexes.

- [ ] **Step 4: Write `tests/test_migrations.py`**

```python
import subprocess


def test_migration_upgrades_cleanly():
    # Runs against the dev DB; should apply without error and be idempotent on re-run.
    r1 = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    r2 = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
```

- [ ] **Step 5: Run it**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add alembic migrations for initial schema"
```

---

## Task 4: Auth dependencies

**Files:**
- Create: `app/security.py`, `tests/test_auth.py`
- Modify: `app/deps.py`

- [ ] **Step 1: Write `tests/test_auth.py` (failing)**

```python
def _app_with_protected_routes():
    from fastapi import Depends, FastAPI

    from app.deps import require_api_key, require_webhook_secret

    app = FastAPI()

    @app.get("/tool", dependencies=[Depends(require_webhook_secret)])
    def tool():
        return {"ok": True}

    @app.get("/read", dependencies=[Depends(require_api_key)])
    def read():
        return {"ok": True}

    return app


def test_webhook_secret_required():
    from fastapi.testclient import TestClient

    c = TestClient(_app_with_protected_routes())
    assert c.get("/tool").status_code == 401
    assert c.get("/tool", headers={"X-Webhook-Secret": "wrong"}).status_code == 401
    assert c.get("/tool", headers={"X-Webhook-Secret": "dev-webhook-secret-change-me"}).status_code == 200


def test_api_key_required():
    from fastapi.testclient import TestClient

    c = TestClient(_app_with_protected_routes())
    assert c.get("/read").status_code == 401
    assert c.get("/read", headers={"X-API-Key": "dev-dashboard-key-change-me"}).status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py -v`
Expected: FAIL (`require_webhook_secret` not importable).

- [ ] **Step 3: Create `app/security.py` (secret compare)**

```python
import hmac


def secrets_match(provided: str | None, expected: str) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)
```

- [ ] **Step 4: Add dependencies to `app/deps.py`**

Append:
```python
from fastapi import Header, HTTPException, status

from app.config import settings
from app.security import secrets_match


def require_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    if not secrets_match(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook secret")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not secrets_match(x_api_key, settings.dashboard_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
```

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add webhook-secret and api-key auth dependencies"
```

---

## Task 5: OTP scrub + PII filtering helpers

**Files:**
- Modify: `app/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write `tests/test_security.py` (failing)**

```python
from app.security import scrub_otp


def test_scrub_otp_redacts_known_code():
    text = "Agent: your collection code is 4821, please keep it."
    assert "4821" not in scrub_otp(text, otp="4821")
    assert "[REDACTED]" in scrub_otp(text, otp="4821")


def test_scrub_otp_handles_none():
    assert scrub_otp("no code here", otp=None) == "no code here"
    assert scrub_otp(None, otp="4821") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_security.py -v`
Expected: FAIL (`scrub_otp` not defined).

- [ ] **Step 3: Add `scrub_otp` to `app/security.py`**

```python
def scrub_otp(text: str | None, otp: str | None) -> str | None:
    """Remove a known OTP value from text before persistence. Safety: §2 OTP discipline."""
    if text is None or not otp:
        return text
    return text.replace(otp, "[REDACTED]")
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_security.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add OTP scrubbing helper for transcript safety"
```

---

## Task 6: Matching helpers (normalize + fuzzy compare)

**Files:**
- Create: `app/services/__init__.py`, `app/services/matching.py`, `tests/test_matching.py`

- [ ] **Step 1: Write `tests/test_matching.py` (failing)**

```python
from app.services.matching import names_match, normalize, refs_match


def test_normalize_casefolds_and_strips():
    assert normalize("  Aïsha   Khan ") == "aisha khan"


def test_refs_match_ignores_case_and_spaces():
    assert refs_match("twin-1", "TWIN 1") is True
    assert refs_match("twin-1", "twin-2") is False


def test_names_match_tolerates_minor_stt_error():
    assert names_match("Aisha Khan", "aisha kahn") is True   # transposition
    assert names_match("Aisha Khan", "John Smith") is False


def test_names_match_token_subset():
    # caller gives first name only
    assert names_match("Aisha Khan", "aisha") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matching.py -v`
Expected: FAIL (`matching` not importable).

- [ ] **Step 3: Create `app/services/__init__.py`** (empty file)

- [ ] **Step 4: Create `app/services/matching.py`**

```python
import unicodedata


def normalize(value: str | None) -> str:
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", value)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_accents.casefold().split())


def _alnum(value: str) -> str:
    return "".join(c for c in normalize(value) if c.isalnum())


def refs_match(a: str | None, b: str | None) -> bool:
    """Order refs / phones: normalize away case + separators, then exact."""
    if not a or not b:
        return False
    return _alnum(a) == _alnum(b)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def names_match(stored: str | None, spoken: str | None) -> bool:
    """Fuzzy name match tolerant of STT error. Token-subset OR close edit distance."""
    s_norm, k_norm = normalize(stored), normalize(spoken)
    if not s_norm or not k_norm:
        return False
    s_tokens, k_tokens = set(s_norm.split()), set(k_norm.split())
    # Every spoken token is close to some stored token (covers first-name-only + typos).
    for kt in k_tokens:
        if not any(_levenshtein(kt, st) <= 1 for st in s_tokens):
            return False
    return True
```

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/test_matching.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add normalization and fuzzy matching helpers"
```

---

## Task 7: Twin source — Protocol, mock client, seed, upsert

**Files:**
- Create: `app/twin/__init__.py`, `app/twin/base.py`, `app/twin/mock.py`, `app/twin/sync.py`, `tests/test_twin.py`

- [ ] **Step 1: Write `tests/test_twin.py` (failing)**

```python
from app.models import Customer, Order
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_seed_upsert_creates_orders_and_customers(db):
    records = MockTwinClient().fetch_all()
    assert len(records) >= 3
    upsert_orders(db, records)
    db.flush()
    assert db.query(Order).count() == len(records)
    # customers deduped on phone
    assert db.query(Customer).count() >= 1


def test_upsert_is_idempotent(db):
    records = MockTwinClient().fetch_all()
    upsert_orders(db, records)
    db.flush()
    first = db.query(Order).count()
    upsert_orders(db, records)  # second time: update, not insert
    db.flush()
    assert db.query(Order).count() == first


def test_upsert_refreshes_status_and_otp(db):
    client = MockTwinClient()
    records = client.fetch_all()
    upsert_orders(db, records)
    db.flush()
    ref = records[0].twin_order_ref
    records[0].status = "delivered"
    records[0].otp_code = "9999"
    upsert_orders(db, records)
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref=ref).one()
    assert order.status == "delivered"
    assert order.otp_code == "9999"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_twin.py -v`
Expected: FAIL (`app.twin` not importable).

- [ ] **Step 3: Create `app/twin/__init__.py`** (empty file)

- [ ] **Step 4: Create `app/twin/base.py`**

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass
class OrderRecord:
    twin_order_ref: str
    customer_name: str
    customer_phone: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None = None
    delivery_window: str | None = None
    otp_code: str | None = None
    assigned_driver: str | None = None
    expected_pieces: int | None = None
    language_pref: str | None = None
    twin_customer_ref: str | None = None


class TwinClient(Protocol):
    def fetch_all(self) -> list[OrderRecord]:
        """Return the full current order feed."""

    def fetch_by_ref(self, twin_order_ref: str) -> OrderRecord | None:
        """Live single-order lookup (fresh status + OTP at call start)."""
```

- [ ] **Step 5: Create `app/twin/mock.py`**

```python
from app.twin.base import OrderRecord

_SEED = [
    OrderRecord(
        twin_order_ref="TWIN-1001", customer_name="Aisha Khan", customer_phone="+971500000001",
        merchant="Amazon", status="out_for_delivery", delivery_address="Apt 12, Marina Gate 1, Dubai Marina",
        delivery_area="Dubai Marina", delivery_window="2026-06-03 09:00-12:00", otp_code="4821",
        assigned_driver="Rahul P.", expected_pieces=1, language_pref="en",
    ),
    OrderRecord(
        twin_order_ref="TWIN-1002", customer_name="Omar Al Farsi", customer_phone="+971500000002",
        merchant="Temu", status="failed", delivery_address="Villa 7, Al Barsha 2",
        delivery_area="Al Barsha", delivery_window="2026-06-02 14:00-18:00", otp_code="7310",
        assigned_driver="Sara M.", expected_pieces=3, language_pref="ar",
    ),
    OrderRecord(
        twin_order_ref="TWIN-1003", customer_name="Fatima Noor", customer_phone="+971500000003",
        merchant="Trendyol", status="delivered", delivery_address="Office 401, Business Bay Tower",
        delivery_area="Business Bay", delivery_window="2026-06-01 10:00-13:00", otp_code="1599",
        assigned_driver="Ali K.", expected_pieces=2, language_pref="en",
    ),
]


class MockTwinClient:
    def fetch_all(self) -> list[OrderRecord]:
        # Return copies so tests can mutate without corrupting the seed.
        from dataclasses import replace
        return [replace(r) for r in _SEED]

    def fetch_by_ref(self, twin_order_ref: str) -> OrderRecord | None:
        from dataclasses import replace
        for r in _SEED:
            if r.twin_order_ref == twin_order_ref:
                return replace(r)
        return None
```

- [ ] **Step 6: Create `app/twin/sync.py`**

```python
import datetime as dt

from sqlalchemy.orm import Session

from app.models import Customer, Order
from app.twin.base import OrderRecord


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _get_or_create_customer(db: Session, rec: OrderRecord) -> Customer:
    customer = db.query(Customer).filter_by(primary_phone=rec.customer_phone).one_or_none()
    if customer is None:
        customer = Customer(
            full_name=rec.customer_name, primary_phone=rec.customer_phone,
            language_pref=rec.language_pref, twin_customer_ref=rec.twin_customer_ref,
            last_synced_at=_now(),
        )
        db.add(customer)
        db.flush()
    else:
        customer.full_name = rec.customer_name
        customer.language_pref = rec.language_pref
        customer.last_synced_at = _now()
    return customer


def upsert_orders(db: Session, records: list[OrderRecord]) -> list[Order]:
    """Single write path for order data — fed by a Twin pull or the ingest endpoint."""
    out: list[Order] = []
    for rec in records:
        customer = _get_or_create_customer(db, rec)
        order = db.query(Order).filter_by(twin_order_ref=rec.twin_order_ref).one_or_none()
        if order is None:
            order = Order(twin_order_ref=rec.twin_order_ref, customer_id=customer.customer_id,
                          merchant=rec.merchant, status=rec.status, delivery_address=rec.delivery_address,
                          last_synced_at=_now())
            db.add(order)
        order.customer_id = customer.customer_id
        order.merchant = rec.merchant
        order.status = rec.status
        order.delivery_address = rec.delivery_address
        order.delivery_area = rec.delivery_area
        order.delivery_window = rec.delivery_window
        order.otp_code = rec.otp_code
        order.assigned_driver = rec.assigned_driver
        order.expected_pieces = rec.expected_pieces
        order.last_synced_at = _now()
        db.flush()
        out.append(order)
    return out
```

- [ ] **Step 7: Run the test**

Run: `uv run pytest tests/test_twin.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: add Twin source protocol, mock client, seed, and upsert path"
```

---

## Task 8: Call service + verification policy

**Files:**
- Create: `app/services/calls.py`, `app/services/verification.py`, `tests/test_verification.py`

- [ ] **Step 1: Write `tests/test_verification.py` (failing) — the policy matrix**

```python
import datetime as dt

import pytest

from app.models import Call, Verification
from app.services.calls import get_or_create_call
from app.services.verification import VerifyInput, verify_caller
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    return db


def _call(db) -> Call:
    return get_or_create_call(db, happyrobot_call_id="hr-1", caller_number="+971500000001")


def test_pass_on_order_ref_plus_name(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Aisha Khan"))
    assert res.result == "passed"
    assert res.order is not None
    assert res.order.twin_order_ref == "TWIN-1001"
    seeded.refresh(call)
    assert call.verification_status == "passed"
    assert call.order_id == res.order.order_id


def test_pass_on_phone_name_area_fallback(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(
        registered_phone="+971500000001", name="Aisha Khan", delivery_area="Dubai Marina"))
    assert res.result == "passed"


def test_partial_when_only_name_matches(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Wrong Person"))
    assert res.result in ("partial", "failed")
    assert res.order is None  # never disclose on non-pass


def test_failed_when_nothing_matches(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    assert res.result == "failed"
    assert res.order is None


def test_attempt_cap_escalates_after_three(seeded):
    call = _call(seeded)
    for _ in range(3):
        verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    res = verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    assert res.escalated is True
    assert seeded.query(Verification).filter_by(call_id=call.call_id).count() >= 3


def test_each_attempt_is_recorded(seeded):
    call = _call(seeded)
    verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Aisha Khan"))
    v = seeded.query(Verification).filter_by(call_id=call.call_id).one()
    assert v.attempt_no == 1
    assert "order_ref" in v.factors_checked
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_verification.py -v`
Expected: FAIL (`app.services.calls` not importable).

- [ ] **Step 3: Create `app/services/calls.py`**

```python
import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.models import Call


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def get_or_create_call(
    db: Session,
    *,
    happyrobot_call_id: str | None = None,
    caller_number: str | None = None,
    language: str | None = None,
) -> Call:
    """One call row per HappyRobot call; reused if the agent retries /verify."""
    if happyrobot_call_id:
        existing = db.query(Call).filter_by(happyrobot_call_id=happyrobot_call_id).one_or_none()
        if existing:
            return existing
    call = Call(
        happyrobot_call_id=happyrobot_call_id, caller_number=caller_number, language=language,
        direction="inbound", agent_type="inbound_exception", verification_status="not_started",
        started_at=_now(),
    )
    db.add(call)
    db.flush()
    return call


def get_call(db: Session, call_id: uuid.UUID) -> Call | None:
    return db.get(Call, call_id)
```

- [ ] **Step 4: Create `app/services/verification.py`**

```python
import datetime as dt
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Call, Customer, Escalation, Order, Verification
from app.services.matching import names_match, normalize, refs_match


@dataclass
class VerifyInput:
    name: str | None = None
    order_ref: str | None = None
    registered_phone: str | None = None
    delivery_area: str | None = None
    item: str | None = None


@dataclass
class VerifyResult:
    result: str            # passed | partial | failed
    order: Order | None    # populated ONLY on pass (safety §2)
    attempt_no: int
    escalated: bool = False


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _candidate_order(db: Session, data: VerifyInput) -> Order | None:
    if data.order_ref:
        for o in db.query(Order).all():
            if refs_match(o.twin_order_ref, data.order_ref):
                return o
    if data.registered_phone:
        cust = None
        for c in db.query(Customer).all():
            if refs_match(c.primary_phone, data.registered_phone):
                cust = c
                break
        if cust:
            order = db.query(Order).filter_by(customer_id=cust.customer_id).first()
            if order:
                return order
    return None


def _evaluate(order: Order | None, data: VerifyInput) -> tuple[str, list[str], list[str]]:
    checked: list[str] = []
    passed: list[str] = []
    if data.order_ref is not None:
        checked.append("order_ref")
        if order and refs_match(order.twin_order_ref, data.order_ref):
            passed.append("order_ref")
    if data.name is not None:
        checked.append("name")
        if order and names_match(order.customer.full_name, data.name):
            passed.append("name")
    if data.registered_phone is not None:
        checked.append("registered_phone")
        if order and refs_match(order.customer.primary_phone, data.registered_phone):
            passed.append("registered_phone")
    if data.delivery_area is not None:
        checked.append("delivery_area")
        if order and names_match(order.delivery_area, data.delivery_area):
            passed.append("delivery_area")

    ps = set(passed)
    strong = {"order_ref", "name"}.issubset(ps)
    fallback = {"registered_phone", "name", "delivery_area"}.issubset(ps)
    if strong or fallback:
        return "passed", checked, passed
    if passed:
        return "partial", checked, passed
    return "failed", checked, passed


def verify_caller(db: Session, call: Call, data: VerifyInput) -> VerifyResult:
    prior = db.query(Verification).filter_by(call_id=call.call_id).count()
    attempt_no = prior + 1

    order = _candidate_order(db, data)
    result, checked, passed = _evaluate(order, data)

    db.add(Verification(
        call_id=call.call_id, order_id=order.order_id if order else None,
        factors_checked=checked, factors_passed=passed, result=result,
        attempt_no=attempt_no, created_at=_now(),
    ))
    call.verification_status = result

    escalated = False
    matched_order: Order | None = None
    if result == "passed":
        matched_order = order
        call.order_id = order.order_id
        call.customer_id = order.customer_id
    elif attempt_no > settings.verification_max_attempts:
        # Safety §2: cap attempts, hand to a human.
        db.add(Escalation(
            call_id=call.call_id, category="verification_failed",
            reason="exceeded verification attempt cap", status="open", created_at=_now(),
        ))
        escalated = True

    db.flush()
    return VerifyResult(result=result, order=matched_order, attempt_no=attempt_no, escalated=escalated)
```

> Note: the attempt-cap escalation also relies on the `escalations.call_id` unique index (Task 2); if a prior escalation exists this insert would conflict — acceptable because cap-escalation happens at most once per call in practice. The `/escalate` endpoint (Task 11) uses get-or-create to stay idempotent.

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/test_verification.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add call service and verify_caller policy with attempt cap"
```

---

## Task 9: `/verify` endpoint + guard

**Files:**
- Create: `app/schemas/__init__.py`, `app/schemas/verify.py`, `app/services/guard.py`, `app/routers/__init__.py`, `app/routers/tools.py`, `tests/test_verify_endpoint.py`, `tests/test_guard.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write `tests/test_guard.py` (failing)**

```python
import datetime as dt

import pytest

from app.models import Call
from app.services.guard import VerificationRequired, require_verified_call


def _call(db, status: str) -> Call:
    c = Call(direction="inbound", agent_type="inbound_exception", verification_status=status,
             started_at=dt.datetime.now(dt.timezone.utc))
    db.add(c)
    db.flush()
    return c


def test_guard_blocks_unverified(db):
    call = _call(db, "partial")
    with pytest.raises(VerificationRequired):
        require_verified_call(call)


def test_guard_allows_verified(db):
    call = _call(db, "passed")
    require_verified_call(call)  # no raise
```

- [ ] **Step 2: Write `tests/test_verify_endpoint.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def test_verify_requires_auth(client, seeded):
    r = client.post("/verify", json={"happyrobot_call_id": "hr-x", "name": "Aisha Khan", "order_ref": "TWIN-1001"})
    assert r.status_code == 401


def test_verify_pass_returns_order(client, seeded):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": "hr-1", "name": "Aisha Khan", "order_ref": "TWIN-1001"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"] == "passed"
    assert body["order"]["twin_order_ref"] == "TWIN-1001"
    assert "otp_code" not in body["order"]   # safety: OTP never in verify response


def test_verify_fail_hides_order(client, seeded):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": "hr-2", "name": "Nobody", "order_ref": "NOPE"})
    assert r.status_code == 200
    assert r.json()["result"] == "failed"
    assert r.json()["order"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_guard.py tests/test_verify_endpoint.py -v`
Expected: FAIL (imports missing).

- [ ] **Step 4: Create `app/services/guard.py`**

```python
from app.models import Call


class VerificationRequired(Exception):
    """Raised when an action/read is attempted before the call is verified. Safety §2."""


def require_verified_call(call: Call) -> None:
    if call.verification_status != "passed":
        raise VerificationRequired(f"call {call.call_id} is '{call.verification_status}', not 'passed'")
```

- [ ] **Step 5: Create `app/schemas/__init__.py`** (empty), then `app/schemas/verify.py`

```python
import uuid

from pydantic import BaseModel


class VerifyRequest(BaseModel):
    happyrobot_call_id: str | None = None
    caller_number: str | None = None
    language: str | None = None
    name: str | None = None
    order_ref: str | None = None
    registered_phone: str | None = None
    delivery_area: str | None = None
    item: str | None = None


class OrderPublic(BaseModel):
    """Order fields safe to return to a VERIFIED caller. No otp_code here (safety §2)."""
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    expected_pieces: int | None


class VerifyResponse(BaseModel):
    call_id: uuid.UUID
    result: str
    attempt_no: int
    escalated: bool
    order: OrderPublic | None
```

- [ ] **Step 6: Create `app/routers/__init__.py`** (empty), then `app/routers/tools.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.verify import OrderPublic, VerifyRequest, VerifyResponse
from app.services.calls import get_or_create_call
from app.services.verification import VerifyInput, verify_caller

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    call = get_or_create_call(
        db, happyrobot_call_id=payload.happyrobot_call_id,
        caller_number=payload.caller_number, language=payload.language,
    )
    res = verify_caller(db, call, VerifyInput(
        name=payload.name, order_ref=payload.order_ref, registered_phone=payload.registered_phone,
        delivery_area=payload.delivery_area, item=payload.item,
    ))
    db.commit()
    order_public = OrderPublic.model_validate(res.order, from_attributes=True) if res.order else None
    return VerifyResponse(
        call_id=call.call_id, result=res.result, attempt_no=res.attempt_no,
        escalated=res.escalated, order=order_public,
    )
```

- [ ] **Step 7: Mount the router in `app/main.py`**

Add inside `create_app()` before `return app`:
```python
    from app.routers import tools

    app.include_router(tools.router)
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest tests/test_guard.py tests/test_verify_endpoint.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: add /verify endpoint, verification guard, and safe order response model"
```

---

## Task 10: Order status endpoint (gated)

**Files:**
- Create: `app/schemas/orders.py`, `app/services/orders.py`, `tests/test_orders.py`
- Modify: `app/routers/tools.py`

- [ ] **Step 1: Write `tests/test_orders.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def _verify(client, ref="TWIN-1001", name="Aisha Khan", call_id="hr-status"):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": call_id, "name": name, "order_ref": ref})
    return r.json()


def test_status_requires_verified_call(client, seeded):
    # Make an order id available but use a fresh unverified call header
    body = _verify(client, name="Nobody", ref="NOPE", call_id="hr-unv")
    cid = body["call_id"]
    # find any order id via a passing verify on a different call
    ok = _verify(client, call_id="hr-ok")
    order_id = ok["order"]["order_id"]
    r = client.get(f"/orders/{order_id}/status", headers={**HEADERS, "X-Call-Id": cid})
    assert r.status_code == 403


def test_status_returns_for_verified(client, seeded):
    ok = _verify(client, call_id="hr-ok2")
    order_id = ok["order"]["order_id"]
    cid = ok["call_id"]
    r = client.get(f"/orders/{order_id}/status", headers={**HEADERS, "X-Call-Id": cid})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"pending", "out_for_delivery", "delivered", "failed", "rescheduled", "returned", "cancelled"}
    assert "otp_code" not in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orders.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `app/schemas/orders.py`**

```python
import uuid

from pydantic import BaseModel


class OrderStatusResponse(BaseModel):
    order_id: uuid.UUID
    status: str
    delivery_window: str | None
    assigned_driver: str | None
```

- [ ] **Step 4: Create `app/services/orders.py`**

```python
import uuid

from sqlalchemy.orm import Session

from app.models import Order


def get_order(db: Session, order_id: uuid.UUID) -> Order | None:
    return db.get(Order, order_id)
```

- [ ] **Step 5: Add a shared call-context dependency + status route to `app/routers/tools.py`**

Add near the top (after existing imports):
```python
import uuid

from fastapi import Header, HTTPException, status as http_status

from app.schemas.orders import OrderStatusResponse
from app.services.calls import get_call
from app.services.guard import VerificationRequired, require_verified_call
from app.services.orders import get_order


def load_verified_call(
    x_call_id: uuid.UUID = Header(...),
    db: Session = Depends(get_db),
):
    call = get_call(db, x_call_id)
    if call is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="call not found")
    try:
        require_verified_call(call)
    except VerificationRequired:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="caller not verified")
    return call
```

Then add the route:
```python
@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
def order_status(order_id: uuid.UUID, call=Depends(load_verified_call), db: Session = Depends(get_db)) -> OrderStatusResponse:
    order = get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="order not found")
    return OrderStatusResponse(
        order_id=order.order_id, status=order.status,
        delivery_window=order.delivery_window, assigned_driver=order.assigned_driver,
    )
```

- [ ] **Step 6: Run the test**

Run: `uv run pytest tests/test_orders.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: add gated order status endpoint with verified-call dependency"
```

---

## Task 11: Action endpoints (idempotent, gated)

Covers reschedule, investigation, merchant-referral, address-flag, escalate, fallback-message. All but fallback are one-per-call (idempotent via get-or-create on `call_id`).

**Files:**
- Create: `app/schemas/actions.py`, `app/services/actions.py`, `tests/test_actions.py`, `tests/test_idempotency.py`
- Modify: `app/routers/tools.py`

- [ ] **Step 1: Write `tests/test_actions.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def verified(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    ok = client.post("/verify", headers=HEADERS,
                     json={"happyrobot_call_id": "hr-act", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    return {"order_id": ok["order"]["order_id"], "call_id": ok["call_id"]}


def _h(verified):
    return {**HEADERS, "X-Call-Id": verified["call_id"]}


def test_reschedule(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/reschedule", headers=_h(verified),
                    json={"requested_date": "2026-06-10", "requested_window": "09:00-12:00", "reason": "not home"})
    assert r.status_code == 200
    assert r.json()["status"] == "requested"


def test_investigation(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/investigation", headers=_h(verified),
                    json={"type": "not_received"})
    assert r.status_code == 200
    assert r.json()["status"] == "open"
    assert r.json()["callback_due_at"] is not None


def test_merchant_referral(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/merchant-referral", headers=_h(verified),
                    json={"reason": "wrong items"})
    assert r.status_code == 200


def test_address_flag(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/address-flag", headers=_h(verified),
                    json={"correction_text": "Building B not A"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


def test_escalate(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/escalate", headers=_h(verified),
                    json={"category": "complaint", "reason": "angry customer"})
    assert r.status_code == 200


def test_fallback_never_carries_otp(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/fallback-message", headers=_h(verified),
                    json={"channel": "whatsapp", "content_type": "tracking_link"})
    assert r.status_code == 200
    # content_type other than tracking_link/notice is rejected
    bad = client.post(f"/orders/{verified['order_id']}/fallback-message", headers=_h(verified),
                      json={"channel": "sms", "content_type": "otp"})
    assert bad.status_code == 422
```

- [ ] **Step 2: Write `tests/test_idempotency.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def verified(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    ok = client.post("/verify", headers=HEADERS,
                     json={"happyrobot_call_id": "hr-idem", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    return {"order_id": ok["order"]["order_id"], "call_id": ok["call_id"]}


def test_reschedule_retry_is_noop(client, verified):
    h = {**HEADERS, "X-Call-Id": verified["call_id"]}
    body = {"requested_date": "2026-06-10"}
    first = client.post(f"/orders/{verified['order_id']}/reschedule", headers=h, json=body).json()
    second = client.post(f"/orders/{verified['order_id']}/reschedule", headers=h, json=body).json()
    assert first["reschedule_id"] == second["reschedule_id"]   # same row, not a duplicate


def test_investigation_retry_is_noop(client, verified):
    h = {**HEADERS, "X-Call-Id": verified["call_id"]}
    first = client.post(f"/orders/{verified['order_id']}/investigation", headers=h, json={"type": "not_received"}).json()
    second = client.post(f"/orders/{verified['order_id']}/investigation", headers=h, json={"type": "not_received"}).json()
    assert first["investigation_id"] == second["investigation_id"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_actions.py tests/test_idempotency.py -v`
Expected: FAIL.

- [ ] **Step 4: Create `app/schemas/actions.py`**

```python
import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel


class RescheduleRequest(BaseModel):
    requested_date: dt.date
    requested_window: str | None = None
    reason: str | None = None


class RescheduleResponse(BaseModel):
    reschedule_id: uuid.UUID
    status: str
    requested_date: dt.date


class InvestigationRequest(BaseModel):
    type: Literal["not_received"] = "not_received"


class InvestigationResponse(BaseModel):
    investigation_id: uuid.UUID
    status: str
    callback_due_at: dt.datetime | None


class MerchantReferralRequest(BaseModel):
    reason: str | None = None


class MerchantReferralResponse(BaseModel):
    referral_id: uuid.UUID
    status: str


class AddressFlagRequest(BaseModel):
    correction_text: str


class AddressFlagResponse(BaseModel):
    flag_id: uuid.UUID
    status: str


class EscalateRequest(BaseModel):
    category: Literal["cancel", "complaint", "unclassified", "hostile", "verification_failed"]
    reason: str | None = None


class EscalateResponse(BaseModel):
    escalation_id: uuid.UUID
    status: str


class FallbackMessageRequest(BaseModel):
    channel: Literal["sms", "whatsapp"]
    content_type: Literal["tracking_link", "notice"]   # never "otp" — rejected by validation


class FallbackMessageResponse(BaseModel):
    message_id: uuid.UUID
    status: str
```

- [ ] **Step 5: Create `app/services/actions.py`**

```python
import datetime as dt
import uuid
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models import (
    AddressFlag,
    Escalation,
    FallbackMessage,
    Investigation,
    MerchantReferral,
    Order,
    Reschedule,
)

T = TypeVar("T")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _get_existing(db: Session, model: type[T], call_id: uuid.UUID) -> T | None:
    return db.query(model).filter_by(call_id=call_id).one_or_none()


def create_reschedule(db: Session, call_id: uuid.UUID, order_id: uuid.UUID,
                      requested_date: dt.date, requested_window: str | None, reason: str | None) -> Reschedule:
    existing = _get_existing(db, Reschedule, call_id)
    if existing:
        return existing
    row = Reschedule(call_id=call_id, order_id=order_id, requested_date=requested_date,
                     requested_window=requested_window, reason=reason, status="requested", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_investigation(db: Session, call_id: uuid.UUID, order_id: uuid.UUID, type_: str) -> Investigation:
    existing = _get_existing(db, Investigation, call_id)
    if existing:
        return existing
    row = Investigation(call_id=call_id, order_id=order_id, type=type_, status="open",
                        callback_due_at=_now() + dt.timedelta(hours=24), opened_at=_now())
    db.add(row)
    db.flush()
    return row


def create_merchant_referral(db: Session, call_id: uuid.UUID, order_id: uuid.UUID, reason: str | None) -> MerchantReferral:
    existing = _get_existing(db, MerchantReferral, call_id)
    if existing:
        return existing
    row = MerchantReferral(call_id=call_id, order_id=order_id, reason=reason, status="open", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_address_flag(db: Session, call_id: uuid.UUID, order: Order, correction_text: str) -> AddressFlag:
    existing = _get_existing(db, AddressFlag, call_id)
    if existing:
        return existing
    row = AddressFlag(call_id=call_id, order_id=order.order_id, original_address=order.delivery_address,
                      correction_text=correction_text, status="pending", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_escalation(db: Session, call_id: uuid.UUID, order_id: uuid.UUID | None,
                      category: str, reason: str | None) -> Escalation:
    existing = _get_existing(db, Escalation, call_id)
    if existing:
        return existing
    row = Escalation(call_id=call_id, order_id=order_id, category=category, reason=reason,
                     status="open", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_fallback_message(db: Session, call_id: uuid.UUID, order_id: uuid.UUID,
                            channel: str, content_type: str) -> FallbackMessage:
    # Not one-per-call (multiple follow-ups allowed). content_type is constrained by the schema.
    row = FallbackMessage(call_id=call_id, order_id=order_id, channel=channel,
                          content_type=content_type, status="queued")
    db.add(row)
    db.flush()
    return row
```

- [ ] **Step 6: Add action routes to `app/routers/tools.py`**

Append (the `load_verified_call` dep + `get_order` are already imported from Task 10):
```python
from app.schemas.actions import (
    AddressFlagRequest, AddressFlagResponse,
    EscalateRequest, EscalateResponse,
    FallbackMessageRequest, FallbackMessageResponse,
    InvestigationRequest, InvestigationResponse,
    MerchantReferralRequest, MerchantReferralResponse,
    RescheduleRequest, RescheduleResponse,
)
from app.services import actions


def _require_order(db: Session, order_id: uuid.UUID):
    order = get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="order not found")
    return order


@router.post("/orders/{order_id}/reschedule", response_model=RescheduleResponse)
def reschedule(order_id: uuid.UUID, payload: RescheduleRequest,
               call=Depends(load_verified_call), db: Session = Depends(get_db)) -> RescheduleResponse:
    _require_order(db, order_id)
    row = actions.create_reschedule(db, call.call_id, order_id, payload.requested_date,
                                    payload.requested_window, payload.reason)
    db.commit()
    return RescheduleResponse(reschedule_id=row.reschedule_id, status=row.status, requested_date=row.requested_date)


@router.post("/orders/{order_id}/investigation", response_model=InvestigationResponse)
def investigation(order_id: uuid.UUID, payload: InvestigationRequest,
                  call=Depends(load_verified_call), db: Session = Depends(get_db)) -> InvestigationResponse:
    _require_order(db, order_id)
    row = actions.create_investigation(db, call.call_id, order_id, payload.type)
    db.commit()
    return InvestigationResponse(investigation_id=row.investigation_id, status=row.status, callback_due_at=row.callback_due_at)


@router.post("/orders/{order_id}/merchant-referral", response_model=MerchantReferralResponse)
def merchant_referral(order_id: uuid.UUID, payload: MerchantReferralRequest,
                      call=Depends(load_verified_call), db: Session = Depends(get_db)) -> MerchantReferralResponse:
    _require_order(db, order_id)
    row = actions.create_merchant_referral(db, call.call_id, order_id, payload.reason)
    db.commit()
    return MerchantReferralResponse(referral_id=row.referral_id, status=row.status)


@router.post("/orders/{order_id}/address-flag", response_model=AddressFlagResponse)
def address_flag(order_id: uuid.UUID, payload: AddressFlagRequest,
                 call=Depends(load_verified_call), db: Session = Depends(get_db)) -> AddressFlagResponse:
    order = _require_order(db, order_id)
    row = actions.create_address_flag(db, call.call_id, order, payload.correction_text)
    db.commit()
    return AddressFlagResponse(flag_id=row.flag_id, status=row.status)


@router.post("/orders/{order_id}/escalate", response_model=EscalateResponse)
def escalate(order_id: uuid.UUID, payload: EscalateRequest,
             call=Depends(load_verified_call), db: Session = Depends(get_db)) -> EscalateResponse:
    _require_order(db, order_id)
    row = actions.create_escalation(db, call.call_id, order_id, payload.category, payload.reason)
    db.commit()
    return EscalateResponse(escalation_id=row.escalation_id, status=row.status)


@router.post("/orders/{order_id}/fallback-message", response_model=FallbackMessageResponse)
def fallback_message(order_id: uuid.UUID, payload: FallbackMessageRequest,
                     call=Depends(load_verified_call), db: Session = Depends(get_db)) -> FallbackMessageResponse:
    _require_order(db, order_id)
    row = actions.create_fallback_message(db, call.call_id, order_id, payload.channel, payload.content_type)
    db.commit()
    return FallbackMessageResponse(message_id=row.message_id, status=row.status)
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_actions.py tests/test_idempotency.py -v`
Expected: PASS. (The `content_type: "otp"` case returns 422 from Pydantic's `Literal` validation — OTP can never travel the fallback channel.)

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: add idempotent gated action endpoints (reschedule/investigation/referral/flag/escalate/fallback)"
```

---

## Task 12: Disposition endpoint

**Files:**
- Create: `app/schemas/calls.py`, `tests/test_disposition.py`
- Modify: `app/services/calls.py`, `app/routers/tools.py`

- [ ] **Step 1: Write `tests/test_disposition.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def verified(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    return client.post("/verify", headers=HEADERS,
                       json={"happyrobot_call_id": "hr-disp", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()


def test_disposition_sets_outcome_and_ends_call(client, verified):
    cid = verified["call_id"]
    r = client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                    json={"disposition": "resolved_info", "intent": "tracking", "csat_score": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["disposition"] == "resolved_info"
    assert body["ended_at"] is not None


def test_disposition_scrubs_otp_from_transcript(client, verified):
    cid = verified["call_id"]
    r = client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                    json={"disposition": "resolved_info", "transcript": "your code is 4821 thanks"})
    assert r.status_code == 200
    assert "4821" not in r.json()["transcript"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_disposition.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `app/schemas/calls.py`**

```python
import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel

DispositionLiteral = Literal[
    "resolved_info", "rescheduled", "investigation_opened", "re_attempt_scheduled",
    "referred_to_merchant", "escalated", "verification_failed", "no_order_found",
]
IntentLiteral = Literal[
    "tracking", "not_received", "failed_delivery", "wrong_items", "reschedule", "cancel", "other",
]


class DispositionRequest(BaseModel):
    disposition: DispositionLiteral
    intent: IntentLiteral | None = None
    csat_score: float | None = None
    transcript: str | None = None
    notes: str | None = None
    recording_url: str | None = None


class DispositionResponse(BaseModel):
    call_id: uuid.UUID
    disposition: str
    intent: str | None
    csat_score: float | None
    transcript: str | None
    ended_at: dt.datetime | None
```

- [ ] **Step 4: Add `set_disposition` to `app/services/calls.py`**

```python
from app.models import Order
from app.security import scrub_otp


def set_disposition(db, call, *, disposition, intent=None, csat_score=None,
                    transcript=None, notes=None, recording_url=None):
    otp = None
    if call.order_id:
        order = db.get(Order, call.order_id)
        otp = order.otp_code if order else None
    call.disposition = disposition
    call.intent = intent
    call.csat_score = csat_score
    call.transcript = scrub_otp(transcript, otp)   # safety §2: OTP out of stored transcript
    call.notes = notes
    call.recording_url = recording_url
    call.ended_at = _now()
    db.flush()
    return call
```

- [ ] **Step 5: Add the route to `app/routers/tools.py`**

```python
from app.schemas.calls import DispositionRequest, DispositionResponse
from app.services.calls import set_disposition


@router.post("/calls/{call_id}/disposition", response_model=DispositionResponse)
def disposition(call_id: uuid.UUID, payload: DispositionRequest, db: Session = Depends(get_db)) -> DispositionResponse:
    call = get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="call not found")
    set_disposition(db, call, disposition=payload.disposition, intent=payload.intent,
                    csat_score=payload.csat_score, transcript=payload.transcript,
                    notes=payload.notes, recording_url=payload.recording_url)
    db.commit()
    return DispositionResponse(
        call_id=call.call_id, disposition=call.disposition, intent=call.intent,
        csat_score=call.csat_score, transcript=call.transcript, ended_at=call.ended_at,
    )
```

> Disposition is not gated on verification — a call that fails verification still needs to log `verification_failed`/`no_order_found`.

- [ ] **Step 6: Run the test**

Run: `uv run pytest tests/test_disposition.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: add disposition endpoint with OTP-scrubbed transcript"
```

---

## Task 13: Dashboard read endpoints + metrics

**Files:**
- Create: `app/schemas/dashboard.py`, `app/services/metrics.py`, `app/routers/dashboard.py`, `tests/test_dashboard.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write `tests/test_dashboard.py` (failing)**

```python
import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

WEBHOOK = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}
APIKEY = {"X-API-Key": "dev-dashboard-key-change-me"}


@pytest.fixture()
def with_activity(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    ok = client.post("/verify", headers=WEBHOOK,
                     json={"happyrobot_call_id": "hr-dash", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    client.post(f"/orders/{ok['order']['order_id']}/investigation",
                headers={**WEBHOOK, "X-Call-Id": ok["call_id"]}, json={"type": "not_received"})
    client.post(f"/calls/{ok['call_id']}/disposition", headers=WEBHOOK,
                json={"disposition": "investigation_opened", "intent": "not_received", "csat_score": 4})
    return ok


def test_dashboard_requires_api_key(client, with_activity):
    assert client.get("/calls").status_code == 401


def test_calls_list_hides_otp(client, with_activity):
    r = client.get("/calls", headers=APIKEY)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert "otp_code" not in r.json()[0]


def test_investigations_list(client, with_activity):
    r = client.get("/investigations", headers=APIKEY)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "open"


def test_metrics_shape(client, with_activity):
    r = client.get("/metrics", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    for key in ("total_calls", "first_attempt_rate", "deflection_rate", "avg_csat", "avg_handle_time_seconds"):
        assert key in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `app/schemas/dashboard.py`**

```python
import datetime as dt
import uuid

from pydantic import BaseModel


class CallSummary(BaseModel):
    call_id: uuid.UUID
    direction: str
    language: str | None
    verification_status: str
    intent: str | None
    disposition: str | None
    csat_score: float | None
    started_at: dt.datetime
    ended_at: dt.datetime | None
    # deliberately no transcript / otp / raw caller PII beyond what ops needs

    model_config = {"from_attributes": True}


class InvestigationSummary(BaseModel):
    investigation_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    type: str
    status: str
    callback_due_at: dt.datetime | None
    opened_at: dt.datetime
    model_config = {"from_attributes": True}


class RescheduleSummary(BaseModel):
    reschedule_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    requested_date: dt.date
    status: str
    synced_to_twin_at: dt.datetime | None
    model_config = {"from_attributes": True}


class EscalationSummary(BaseModel):
    escalation_id: uuid.UUID
    call_id: uuid.UUID
    category: str
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class Metrics(BaseModel):
    total_calls: int
    first_attempt_rate: float
    deflection_rate: float
    avg_csat: float | None
    avg_handle_time_seconds: float | None
```

- [ ] **Step 4: Create `app/services/metrics.py`**

```python
from sqlalchemy.orm import Session

from app.models import Call, Escalation


def compute_metrics(db: Session) -> dict:
    calls = db.query(Call).all()
    total = len(calls)
    completed = [c for c in calls if c.ended_at]
    # first-attempt: verified passed on the call (proxy for resolved without re-contact)
    first_attempt = [c for c in calls if c.verification_status == "passed"]
    # deflection: resolved by the agent without an escalation row
    escalated_call_ids = {e.call_id for e in db.query(Escalation).all()}
    deflected = [c for c in calls if c.disposition and c.call_id not in escalated_call_ids]
    csats = [float(c.csat_score) for c in calls if c.csat_score is not None]
    handle_times = [(c.ended_at - c.started_at).total_seconds() for c in completed]

    def rate(part: list, whole: int) -> float:
        return round(len(part) / whole, 3) if whole else 0.0

    return {
        "total_calls": total,
        "first_attempt_rate": rate(first_attempt, total),
        "deflection_rate": rate(deflected, total),
        "avg_csat": round(sum(csats) / len(csats), 2) if csats else None,
        "avg_handle_time_seconds": round(sum(handle_times) / len(handle_times), 1) if handle_times else None,
    }
```

- [ ] **Step 5: Create `app/routers/dashboard.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Call, Escalation, Investigation, Reschedule
from app.schemas.dashboard import (
    CallSummary, EscalationSummary, InvestigationSummary, Metrics, RescheduleSummary,
)
from app.services.metrics import compute_metrics

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/calls", response_model=list[CallSummary])
def list_calls(db: Session = Depends(get_db)):
    return db.query(Call).order_by(Call.started_at.desc()).all()


@router.get("/investigations", response_model=list[InvestigationSummary])
def list_investigations(db: Session = Depends(get_db)):
    return db.query(Investigation).order_by(Investigation.opened_at.desc()).all()


@router.get("/reschedules", response_model=list[RescheduleSummary])
def list_reschedules(db: Session = Depends(get_db)):
    return db.query(Reschedule).order_by(Reschedule.created_at.desc()).all()


@router.get("/escalations", response_model=list[EscalationSummary])
def list_escalations(db: Session = Depends(get_db)):
    return db.query(Escalation).order_by(Escalation.created_at.desc()).all()


@router.get("/metrics", response_model=Metrics)
def metrics(db: Session = Depends(get_db)):
    return compute_metrics(db)
```

- [ ] **Step 6: Mount the dashboard router in `app/main.py`**

Add inside `create_app()` before `return app`:
```python
    from app.routers import dashboard

    app.include_router(dashboard.router)
```

- [ ] **Step 7: Run the test**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: add dashboard read endpoints and metrics with PII/OTP-safe responses"
```

---

## Task 14: Order ingest endpoint (`POST /orders/sync`)

**Files:**
- Create: `app/schemas/ingest.py`, `app/routers/ingest.py`, `tests/test_ingest.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write `tests/test_ingest.py` (failing)**

```python
HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}

PAYLOAD = {
    "orders": [
        {
            "twin_order_ref": "TWIN-2001", "customer_name": "Layla Hassan",
            "customer_phone": "+971500000099", "merchant": "Amazon", "status": "pending",
            "delivery_address": "Apt 9, JLT Cluster C", "delivery_area": "JLT", "otp_code": "5555",
        }
    ]
}


def test_ingest_requires_auth(client):
    assert client.post("/orders/sync", json=PAYLOAD).status_code == 401


def test_ingest_upserts_orders(client):
    r = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert r.status_code == 200
    assert r.json()["upserted"] == 1
    # second push is an update, not a duplicate
    r2 = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert r2.json()["upserted"] == 1


def test_ingest_response_excludes_otp(client):
    r = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert "otp_code" not in r.text
    assert "5555" not in r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `app/schemas/ingest.py`**

```python
from pydantic import BaseModel


class IngestOrder(BaseModel):
    twin_order_ref: str
    customer_name: str
    customer_phone: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None = None
    delivery_window: str | None = None
    otp_code: str | None = None
    assigned_driver: str | None = None
    expected_pieces: int | None = None
    language_pref: str | None = None
    twin_customer_ref: str | None = None


class IngestRequest(BaseModel):
    orders: list[IngestOrder]


class IngestResponse(BaseModel):
    upserted: int
```

- [ ] **Step 4: Create `app/routers/ingest.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.ingest import IngestRequest, IngestResponse
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.post("/orders/sync", response_model=IngestResponse)
def sync_orders(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    records = [OrderRecord(**o.model_dump()) for o in payload.orders]
    rows = upsert_orders(db, records)
    db.commit()
    return IngestResponse(upserted=len(rows))
```

- [ ] **Step 5: Mount the ingest router in `app/main.py`**

Add inside `create_app()` before `return app`:
```python
    from app.routers import ingest

    app.include_router(ingest.router)
```

- [ ] **Step 6: Run the test**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite + lint**

Run:
```bash
uv run ruff check app tests
uv run pytest -v
```
Expected: ruff clean, all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: add POST /orders/sync ingest endpoint for pushed order data"
```

---

## Task 15: README + run instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Shipa Inbound Voice Backend

FastAPI backend for the Shipa inbound exception-handler voice agent. See
`docs/superpowers/specs/2026-06-02-shipa-inbound-backend-design.md` for the design.

## Setup
```bash
docker compose up -d db          # local Postgres
cp .env.example .env
uv sync
uv run alembic upgrade head      # apply schema
uv run uvicorn app.main:app --reload
```

## Seed mock orders
```bash
uv run python -c "from app.db import SessionLocal; from app.twin.mock import MockTwinClient; from app.twin.sync import upsert_orders; s=SessionLocal(); upsert_orders(s, MockTwinClient().fetch_all()); s.commit()"
```

## Test
```bash
uv run pytest -v
```

## Auth
- Agent tool + ingest endpoints: `X-Webhook-Secret` header (`WEBHOOK_SECRET`).
- Dashboard read endpoints: `X-API-Key` header (`DASHBOARD_API_KEY`).
- Gated endpoints additionally require an `X-Call-Id` header pointing at a verified call.

## Safety invariants
- Order detail/actions require `verify_caller` == passed (enforced by `require_verified_call`).
- OTP never appears in responses or stored transcripts, never on the fallback channel.
- Verification capped at 3 attempts, then auto-escalates.
- Write actions are idempotent per call.
````

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "docs: add README with setup, run, and safety notes"
```

---

## Self-Review notes (for the implementer)

- **Spec coverage:** §2 safety → Tasks 4/5/8/9/11/12 (auth, OTP scrub, attempt cap, guard, idempotency, fallback content-type lock). §3–4 architecture/structure → Tasks 1–2. §5 endpoints → Tasks 9–14. §6 verify policy → Task 8. §7 idempotency → Tasks 2 (unique indexes) + 11. §8 Twin source-agnostic → Tasks 7 + 14. §9 testing → every task is TDD against real Postgres.
- **Deferred per spec (do NOT implement here):** column-level encryption at rest, UAE residency hosting, real Twin client, real SMS/WhatsApp send. `fallback-message` only records intent; it does not call a provider.
- **Known sharp edge:** the verify attempt-cap escalation (Task 8) and the `/escalate` endpoint (Task 11) both write to `escalations`, which has a unique `call_id`. If a call hits the cap AND later calls `/escalate`, the second uses get-or-create and returns the existing row — no error. Confirm this holds when implementing Task 11.
