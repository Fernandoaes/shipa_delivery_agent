# Shipa Ops Dashboard Metrics + List Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's mislabeled KPIs with business-driven delivery + agent metrics (backed by 3 new `Order` columns), and add full URL-synced filter/lookup to the Orders, Customers, Escalations, and Investigations list pages.

**Architecture:** Backend adds `delivered_at`/`attempt_count`/`sla_due_at` to `Order` (single write path via `upsert_orders`), extends `compute_metrics`/`compute_insights`, and exposes two new searchable fields. Frontend rewrites the landing KPI strip + diagnostics, adds a Work Queue, and introduces shared client-side filter primitives used by per-entity table components. Delivery KPIs are current-snapshot; call/interaction charts stay window-scoped.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / Postgres (`uv`); Next 16 / React 19 / Tailwind v4 (frontend).

**Spec:** `docs/superpowers/specs/2026-06-04-shipa-ops-dashboard-metrics-design.md`

**Conventions:**
- Backend tests run with `uv run pytest`. The `db` fixture (SQLAlchemy session) and seed helper `upsert_orders(db, MockTwinClient().fetch_all())` are the standard pattern (see `tests/test_insights_service.py`).
- Frontend has no test harness; the gate is `cd frontend && npx tsc --noEmit && npm run lint && npm run build`. Run it where a task says "run the frontend gate".
- A pre-existing `httpx`/TestClient failure (~20 tests, `KeyError: 'order'`) is unrelated — ignore it; only judge the tests this plan adds/edits.

---

## File Structure

**Backend — modify:**
- `app/models/read.py` — 3 new `Order` columns
- `migrations/versions/<new>.py` — Alembic migration (down_revision `c3a7f1e2b9d4`)
- `app/twin/base.py` — `OrderRecord` fields
- `app/schemas/ingest.py` — `IngestOrder` fields
- `app/twin/sync.py` — persist new fields in `upsert_orders`
- `app/services/metrics.py` — delivery + agent KPIs
- `app/services/insights.py` — stacked interactions, failures-by-area, expanded work queue
- `app/schemas/dashboard.py` — `Metrics`, `Insights`, `NeedsAttention`, `ChannelDay`, `AreaCount`, `EscalationSummary.reason`, `InvestigationSummary.twin_order_ref`
- `app/routers/dashboard.py` — investigations list resolves `twin_order_ref`
- `db/seed_demo.py` — seed new columns
- `tests/test_insights_service.py`, `tests/test_dashboard.py` — updated assertions

**Frontend — create:**
- `frontend/components/WorkQueue.tsx`, `StackedBarChart.tsx`, `AgentStats.tsx`
- `frontend/components/filters/SearchInput.tsx`, `FilterSelect.tsx`, `useTableFilters.ts`
- `frontend/components/CustomersTable.tsx`, `EscalationsTable.tsx`, `InvestigationsTable.tsx`

**Frontend — modify:**
- `frontend/lib/types.ts`, `frontend/lib/api.ts`, `frontend/lib/insights.ts`
- `frontend/app/page.tsx`
- `frontend/components/OrdersTable.tsx`
- `frontend/app/customers/page.tsx`, `escalations/page.tsx`, `investigations/page.tsx`

---

## Task 1: Add delivery-tracking columns to `Order`

**Files:**
- Modify: `app/models/read.py:43` (after `expected_pieces`)
- Create: `migrations/versions/b2c4e6a8d013_add_order_delivery_tracking.py`

- [ ] **Step 1: Add columns to the model**

In `app/models/read.py`, inside `class Order`, add after the `expected_pieces` line (`app/models/read.py:43`):

```python
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    delivered_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    sla_due_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 2: Create the migration**

Create `migrations/versions/b2c4e6a8d013_add_order_delivery_tracking.py`:

```python
"""add order delivery tracking

Revision ID: b2c4e6a8d013
Revises: c3a7f1e2b9d4
Create Date: 2026-06-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c4e6a8d013'
down_revision: Union[str, Sequence[str], None] = 'c3a7f1e2b9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("sla_due_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "sla_due_at")
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "attempt_count")
```

- [ ] **Step 3: Verify migration applies and is at head**

Run: `uv run alembic upgrade head && uv run alembic heads`
Expected: no error; head printed is `b2c4e6a8d013 (head)`.

- [ ] **Step 4: Commit**

```bash
git add app/models/read.py migrations/versions/b2c4e6a8d013_add_order_delivery_tracking.py
git commit -m "feat(db): add attempt_count/delivered_at/sla_due_at to orders"
```

---

## Task 2: Propagate new fields through the order write path

**Files:**
- Modify: `app/twin/base.py:17` (`OrderRecord`)
- Modify: `app/schemas/ingest.py:33` (`IngestOrder`)
- Modify: `app/twin/sync.py:49` (`upsert_orders`)
- Test: `tests/test_twin_sync.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create/append `tests/test_twin_sync.py`:

```python
import datetime as dt

from app.models import Order
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders


def test_upsert_persists_delivery_tracking(db):
    due = dt.datetime(2026, 6, 4, 12, 0, 0)
    delivered = dt.datetime(2026, 6, 4, 11, 0, 0)
    rec = OrderRecord(
        twin_order_ref="TWIN-9001", customer_name="Test User", customer_phone="+971500009001",
        merchant="Amazon", status="delivered", delivery_address="Unit 1, Test Bldg",
        attempt_count=2, delivered_at=delivered, sla_due_at=due,
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-9001").one()
    assert o.attempt_count == 2
    assert o.delivered_at == delivered
    assert o.sla_due_at == due


def test_upsert_defaults_attempt_count_and_preserves_timestamps(db):
    rec = OrderRecord(
        twin_order_ref="TWIN-9002", customer_name="Test Two", customer_phone="+971500009002",
        merchant="Noon", status="pending", delivery_address="Unit 2, Test Bldg",
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-9002").one()
    assert o.attempt_count == 1
    assert o.delivered_at is None
    # a later partial sync without timestamps must not wipe a known delivered_at
    o.delivered_at = dt.datetime(2026, 6, 4, 10, 0, 0)
    db.flush()
    upsert_orders(db, [rec])  # rec still has delivered_at=None
    db.flush()
    assert o.delivered_at == dt.datetime(2026, 6, 4, 10, 0, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_twin_sync.py -v`
Expected: FAIL — `OrderRecord` has no `attempt_count` argument.

- [ ] **Step 3: Add fields to `OrderRecord`**

In `app/twin/base.py`, add to the `OrderRecord` dataclass after `delivery_lng` (`app/twin/base.py:23`):

```python
    attempt_count: int = 1
    delivered_at: "dt.datetime | None" = None
    sla_due_at: "dt.datetime | None" = None
```

Add at the top of the file: `import datetime as dt`.

- [ ] **Step 4: Add fields to `IngestOrder`**

In `app/schemas/ingest.py`, add to `IngestOrder` after `delivery_lng` (`app/schemas/ingest.py:39`):

```python
    attempt_count: int = 1
    delivered_at: dt.datetime | None = None
    sla_due_at: dt.datetime | None = None
```

`dt` is already imported in that module.

- [ ] **Step 5: Persist in `upsert_orders`**

In `app/twin/sync.py`, after `order.expected_pieces = rec.expected_pieces` (`app/twin/sync.py:49`) add:

```python
        order.attempt_count = rec.attempt_count
        # Timestamps arrive when known; a partial sync must not wipe an existing value.
        if rec.delivered_at is not None:
            order.delivered_at = rec.delivered_at
        if rec.sla_due_at is not None:
            order.sla_due_at = rec.sla_due_at
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_twin_sync.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add app/twin/base.py app/schemas/ingest.py app/twin/sync.py tests/test_twin_sync.py
git commit -m "feat(ingest): carry delivery tracking through order upsert"
```

---

## Task 3: Business KPIs in `compute_metrics`

**Files:**
- Modify: `app/services/metrics.py`
- Modify: `app/schemas/dashboard.py:87` (`Metrics`)
- Test: `tests/test_metrics_service.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_metrics_service.py`:

```python
import datetime as dt

from app.models import AddressFlag, Call, Escalation, Order, Reschedule
from app.services.metrics import compute_metrics
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())  # 1001 OFD, 1002 failed, 1003 delivered
    db.flush()
    o1003 = db.query(Order).filter_by(twin_order_ref="TWIN-1003").one()
    o1003.attempt_count = 1
    o1003.delivered_at = dt.datetime(2026, 6, 1, 11, 0, 0)
    o1003.sla_due_at = dt.datetime(2026, 6, 1, 13, 0, 0)  # on time
    db.flush()
    return db.query(Order).filter_by(twin_order_ref="TWIN-1002").one()


def test_delivery_kpis(db):
    _seed_orders(db)
    m = compute_metrics(db)
    assert m["active_deliveries"] == 1   # 1001 out_for_delivery
    assert m["at_risk"] == 1             # 1002 failed
    # terminal = {delivered, failed, returned} = {1003, 1002}; first-attempt delivered = 1003
    assert m["first_attempt_success"] == 0.5
    assert m["on_time_rate"] == 1.0      # 1003 delivered_at <= sla_due_at


def test_recovery_rate_counts_rescheduled_or_address_fixed(db):
    failed = _seed_orders(db)
    now = dt.datetime.now()
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=failed.order_id, customer_id=failed.customer_id, started_at=now)
    db.add(call)
    db.flush()
    db.add(Reschedule(call_id=call.call_id, order_id=failed.order_id,
                      requested_date=dt.date.today(), status="requested", created_at=now))
    db.flush()
    m = compute_metrics(db)
    assert m["recovery_rate"] == 1.0  # the one at-risk order has a reschedule


def test_containment_excludes_escalated_calls(db):
    order = _seed_orders(db)
    now = dt.datetime.now()
    handled = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                   disposition="rescheduled", order_id=order.order_id, customer_id=order.customer_id,
                   started_at=now)
    escalated = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                     disposition="escalated", order_id=order.order_id, customer_id=order.customer_id,
                     started_at=now)
    db.add_all([handled, escalated])
    db.flush()
    db.add(Escalation(call_id=escalated.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=now))
    db.flush()
    m = compute_metrics(db)
    assert m["total_calls"] == 2
    assert m["containment_rate"] == 0.5  # 1 of 2 calls resolved without escalation


def test_empty_db_rates_are_zero(db):
    m = compute_metrics(db)
    assert m["first_attempt_success"] == 0.0
    assert m["on_time_rate"] == 0.0
    assert m["recovery_rate"] == 0.0
    assert m["active_deliveries"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_metrics_service.py -v`
Expected: FAIL — `KeyError: 'active_deliveries'`.

- [ ] **Step 3: Rewrite `compute_metrics`**

Replace the body of `app/services/metrics.py` with:

```python
import datetime as dt

from sqlalchemy.orm import Session

from app.models import AddressFlag, Call, Escalation, Order, Reschedule

_TERMINAL = ("delivered", "failed", "returned")
_AT_RISK = ("failed", "returned")
_ACTIVE = ("out_for_delivery", "pending")


def compute_metrics(db: Session, days: int = 7) -> dict:
    # Call KPIs window by started_at (matches compute_insights); delivery KPIs are current-snapshot.
    start = dt.date.today() - dt.timedelta(days=days - 1)
    calls = [c for c in db.query(Call).all() if c.started_at.date() >= start]
    total = len(calls)
    completed = [c for c in calls if c.ended_at]
    escalated_call_ids = {e.call_id for e in db.query(Escalation).all()}
    contained = [c for c in calls if c.disposition and c.call_id not in escalated_call_ids]
    csats = [float(c.csat_score) for c in calls if c.csat_score is not None]
    handle_times = [(c.ended_at - c.started_at).total_seconds() for c in completed]

    orders = db.query(Order).all()
    terminal = [o for o in orders if o.status in _TERMINAL]
    delivered = [o for o in orders if o.status == "delivered"]
    first_attempt = [o for o in delivered if o.attempt_count == 1]
    on_time_denom = [o for o in delivered if o.sla_due_at is not None and o.delivered_at is not None]
    on_time_num = [o for o in on_time_denom if o.delivered_at <= o.sla_due_at]
    at_risk = [o for o in orders if o.status in _AT_RISK]
    active = [o for o in orders if o.status in _ACTIVE]

    at_risk_ids = {o.order_id for o in at_risk}
    rescheduled_ids = {r.order_id for r in db.query(Reschedule.order_id).all()}
    flagged_ids = {f.order_id for f in db.query(AddressFlag.order_id).all()}
    recovered = at_risk_ids & (rescheduled_ids | flagged_ids)

    def rate(part, whole: int) -> float:
        whole = whole if isinstance(whole, int) else len(whole)
        n = part if isinstance(part, int) else len(part)
        return round(n / whole, 3) if whole else 0.0

    return {
        "total_calls": total,
        "first_attempt_success": rate(first_attempt, len(terminal)),
        "on_time_rate": rate(on_time_num, len(on_time_denom)),
        "active_deliveries": len(active),
        "at_risk": len(at_risk),
        "containment_rate": rate(contained, total),
        "recovery_rate": rate(len(recovered), len(at_risk)),
        "avg_csat": round(sum(csats) / len(csats), 2) if csats else None,
        "avg_handle_time_seconds": round(sum(handle_times) / len(handle_times), 1) if handle_times else None,
    }
```

- [ ] **Step 4: Update the `Metrics` schema**

Replace `class Metrics` in `app/schemas/dashboard.py:87`:

```python
class Metrics(BaseModel):
    total_calls: int
    first_attempt_success: float
    on_time_rate: float
    active_deliveries: int
    at_risk: int
    containment_rate: float
    recovery_rate: float
    avg_csat: float | None
    avg_handle_time_seconds: float | None
```

- [ ] **Step 5: Update the metrics endpoint test**

In `tests/test_dashboard.py`, replace the key tuple in `test_metrics_shape` (`tests/test_dashboard.py:45`):

```python
    for key in ("total_calls", "first_attempt_success", "on_time_rate", "active_deliveries",
                "at_risk", "containment_rate", "recovery_rate", "avg_csat", "avg_handle_time_seconds"):
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_metrics_service.py -v`
Expected: PASS (4 tests). (`test_dashboard.py::test_metrics_shape` shares the pre-existing TestClient fixture failure — ignore that one.)

- [ ] **Step 7: Commit**

```bash
git add app/services/metrics.py app/schemas/dashboard.py tests/test_metrics_service.py tests/test_dashboard.py
git commit -m "feat(metrics): delivery + agent business KPIs"
```

---

## Task 4: Stacked interactions, failures-by-area, expanded work queue in `compute_insights`

**Files:**
- Modify: `app/services/insights.py`
- Modify: `app/schemas/dashboard.py` (`Insights`, `NeedsAttention`, add `ChannelDay`, `AreaCount`)
- Modify: `tests/test_insights_service.py`

- [ ] **Step 1: Update the insights tests**

In `tests/test_insights_service.py`, replace the two `calls_per_day` tests and `test_needs_attention_counts` with:

```python
def test_interactions_per_day_zero_filled_with_voice_channel(db):
    _seed(db)
    out = compute_insights(db)  # default 7-day window
    assert len(out["interactions_per_day"]) == 7
    voice = sum(d["channels"].get("voice", 0) for d in out["interactions_per_day"])
    assert voice == 2
    dates = [d["date"] for d in out["interactions_per_day"]]
    assert dates == sorted(dates)


def test_interactions_include_fallback_messages(db):
    order = _seed(db)
    from app.models import FallbackMessage
    db.add(FallbackMessage(order_id=order.order_id, channel="whatsapp", content_type="text",
                           status="sent", sent_at=dt.datetime.now()))
    db.flush()
    out = compute_insights(db)
    wa = sum(d["channels"].get("whatsapp", 0) for d in out["interactions_per_day"])
    assert wa == 1


def test_needs_attention_work_queue(db):
    order = _seed(db)
    call = db.query(Call).order_by(Call.started_at.desc()).first()
    from app.models import AddressFlag, Investigation
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=call.call_id, order_id=order.order_id, requested_date=dt.date.today(),
                      status="requested", synced_to_twin_at=None, created_at=dt.datetime.now()))
    db.add(Investigation(call_id=call.call_id, order_id=order.order_id, type="missing_item",
                         status="open", callback_due_at=dt.datetime.now() - dt.timedelta(hours=1),
                         opened_at=dt.datetime.now()))
    db.add(AddressFlag(call_id=call.call_id, order_id=order.order_id, original_address="x",
                       correction_text="y", status="pending", created_at=dt.datetime.now()))
    db.flush()
    na = compute_insights(db)["needs_attention"]
    assert na["open_escalations"] == 1
    assert na["overdue_callbacks"] == 1
    assert na["pending_reschedules"] == 1
    assert na["pending_address_flags"] == 1


def test_failures_by_area(db):
    _seed(db)
    db.query(Order).filter_by(twin_order_ref="TWIN-1002").one().status = "failed"
    db.flush()
    areas = {a["area"]: a["count"] for a in compute_insights(db)["failures_by_area"]}
    assert areas.get("Al Barsha") == 1
```

Note: `_seed` reuses `Investigation` import — the helper already imports from `app.models`; the local `from app.models import ...` lines above keep each test self-contained.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_insights_service.py -v`
Expected: FAIL — `KeyError: 'interactions_per_day'` / `'failures_by_area'`.

- [ ] **Step 3: Rewrite `compute_insights`**

Replace `app/services/insights.py` with:

```python
import datetime as dt
from collections import Counter

from sqlalchemy.orm import Session

from app.models import (
    AddressFlag, Call, Escalation, FallbackMessage, Investigation, Order, Reschedule,
)

_ACTIVE_STATUSES = ("out_for_delivery", "pending", "failed", "rescheduled")
_AT_RISK = ("failed", "returned")


def compute_insights(db: Session, days: int = 7) -> dict:
    today = dt.date.today()
    start = today - dt.timedelta(days=days - 1)
    window_days = [start + dt.timedelta(days=i) for i in range(days)]

    # Stacked interactions: voice calls + fallback messages, by channel, per day.
    per_day: dict[dt.date, Counter] = {d: Counter() for d in window_days}
    calls = db.query(Call).all()
    windowed_calls = [c for c in calls if c.started_at.date() >= start]
    for c in windowed_calls:
        d = c.started_at.date()
        if d in per_day:
            per_day[d]["voice"] += 1
    for m in db.query(FallbackMessage).filter(FallbackMessage.sent_at.isnot(None)).all():
        d = m.sent_at.date()
        if d in per_day:
            per_day[d][m.channel] += 1
    interactions_per_day = [
        {"date": d, "channels": dict(per_day[d])} for d in window_days
    ]

    intent_counter = Counter((c.intent or "unknown") for c in windowed_calls)
    disposition_counter = Counter((c.disposition or "unknown") for c in windowed_calls)
    intent_mix = [{"intent": k, "count": v} for k, v in intent_counter.most_common()]
    disposition_mix = [{"disposition": k, "count": v} for k, v in disposition_counter.most_common()]

    now = dt.datetime.now()
    needs_attention = {
        "open_escalations": db.query(Escalation).filter(Escalation.status == "open").count(),
        "overdue_callbacks": db.query(Investigation).filter(
            Investigation.status == "open", Investigation.callback_due_at < now
        ).count(),
        "pending_reschedules": db.query(Reschedule).filter(Reschedule.synced_to_twin_at.is_(None)).count(),
        "pending_address_flags": db.query(AddressFlag).filter(AddressFlag.status == "pending").count(),
    }

    failure_counter: Counter = Counter()
    for o in db.query(Order).filter(Order.status.in_(_AT_RISK)).all():
        failure_counter[o.delivery_area or "Unknown"] += 1
    failures_by_area = [{"area": k, "count": v} for k, v in failure_counter.most_common()]

    map_orders = (
        db.query(Order)
        .filter(
            Order.delivery_lat.isnot(None),
            Order.delivery_lng.isnot(None),
            Order.status.in_(_ACTIVE_STATUSES),
        )
        .all()
    )
    map_points = [
        {
            "order_id": o.order_id,
            "twin_order_ref": o.twin_order_ref,
            "status": o.status,
            "delivery_area": o.delivery_area,
            "delivery_lat": o.delivery_lat,
            "delivery_lng": o.delivery_lng,
        }
        for o in map_orders
    ]

    return {
        "interactions_per_day": interactions_per_day,
        "intent_mix": intent_mix,
        "disposition_mix": disposition_mix,
        "failures_by_area": failures_by_area,
        "needs_attention": needs_attention,
        "map_points": map_points,
    }
```

- [ ] **Step 4: Update schemas**

In `app/schemas/dashboard.py`, replace `class NeedsAttention` (`:168`) and add `ChannelDay`/`AreaCount`, then update `class Insights` (`:183`):

```python
class ChannelDay(BaseModel):
    date: dt.date
    channels: dict[str, int]


class AreaCount(BaseModel):
    area: str
    count: int


class NeedsAttention(BaseModel):
    open_escalations: int
    overdue_callbacks: int
    pending_reschedules: int
    pending_address_flags: int


class Insights(BaseModel):
    interactions_per_day: list[ChannelDay]
    intent_mix: list[IntentCount]
    disposition_mix: list[DispositionCount]
    failures_by_area: list[AreaCount]
    needs_attention: NeedsAttention
    map_points: list[MapPoint]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_insights_service.py -v`
Expected: PASS (all tests in file).

- [ ] **Step 6: Commit**

```bash
git add app/services/insights.py app/schemas/dashboard.py tests/test_insights_service.py
git commit -m "feat(insights): stacked interactions, failures-by-area, work-queue counts"
```

---

## Task 5: Make escalations + investigations searchable by order/reason

**Files:**
- Modify: `app/schemas/dashboard.py` (`EscalationSummary`, `InvestigationSummary`)
- Modify: `app/routers/dashboard.py` (investigations list resolves `twin_order_ref`)
- Test: `tests/test_dashboard_lookups.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_dashboard_lookups.py`:

```python
import datetime as dt

from app.models import Call, Investigation, Order
from app.routers.dashboard import list_investigations
from app.schemas.dashboard import EscalationSummary, InvestigationSummary
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_escalation_summary_exposes_reason():
    assert "reason" in EscalationSummary.model_fields


def test_investigation_summary_exposes_twin_order_ref():
    assert "twin_order_ref" in InvestigationSummary.model_fields


def test_list_investigations_resolves_twin_ref(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    # call_id is NOT NULL on Investigation, so create a real Call first.
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add(call)
    db.flush()
    db.add(Investigation(call_id=call.call_id, order_id=order.order_id, type="missing_item",
                         status="open", opened_at=dt.datetime.now()))
    db.flush()
    rows = list_investigations(db)
    assert rows[0].twin_order_ref == "TWIN-1001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_lookups.py -v`
Expected: FAIL — `reason`/`twin_order_ref` not in fields; `list_investigations` not callable with a session only.

- [ ] **Step 3: Add fields to the summaries**

In `app/schemas/dashboard.py`, add `reason` to `EscalationSummary` (after `category`, `:48`):

```python
    reason: str | None = None
```

Add `twin_order_ref` to `InvestigationSummary` (after `order_id`, `:28`):

```python
    twin_order_ref: str | None = None
```

- [ ] **Step 4: Resolve `twin_order_ref` in the investigations endpoint**

In `app/routers/dashboard.py`, replace the `list_investigations` function (`:29-31`):

```python
@router.get("/investigations", response_model=list[InvestigationSummary])
def list_investigations(db: Session = Depends(get_db)):
    rows = db.query(Investigation).order_by(Investigation.opened_at.desc()).all()
    refs = dict(db.query(Order.order_id, Order.twin_order_ref).all())
    return [
        InvestigationSummary(
            investigation_id=r.investigation_id, call_id=r.call_id, order_id=r.order_id,
            type=r.type, status=r.status, callback_due_at=r.callback_due_at,
            opened_at=r.opened_at, twin_order_ref=refs.get(r.order_id),
        )
        for r in rows
    ]
```

Add `Order` to the model import at the top of `app/routers/dashboard.py:7` (the `from app.models import (...)` block — append `Order`). Escalations already serialize via `from_attributes`, so `reason` needs no router change.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard_lookups.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/routers/dashboard.py tests/test_dashboard_lookups.py
git commit -m "feat(dashboard): expose escalation reason + investigation order ref for lookups"
```

---

## Task 6: Seed realistic delivery-tracking values

**Files:**
- Modify: `db/seed_demo.py` (`ORDERS_SQL`, columns `:84-86` and SELECT `:87-109`)

- [ ] **Step 1: Add the three columns to the INSERT**

In `db/seed_demo.py`, extend the column list in `ORDERS_SQL` (`:84-86`) — append `attempt_count, delivered_at, sla_due_at` before the closing paren:

```sql
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces,
                    merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at,
                    attempt_count, delivered_at, sla_due_at)
```

- [ ] **Step 2: Add the three SELECT expressions**

In the same SELECT, immediately after the `now()` that ends the existing column list (`db/seed_demo.py:109`, the `last_synced_at` value) and before `FROM`, add three comma-separated expressions:

```sql
       ,
       -- attempt_count: failed/returned/rescheduled took >=2 attempts; a minority of delivered took 2-3
       CASE
         WHEN st.status IN ('failed','returned') THEN 2 + (gen.n %% 2)
         WHEN st.status = 'rescheduled' THEN 2
         WHEN st.status = 'delivered' AND gen.n %% 6 = 0 THEN 2
         ELSE 1
       END,
       -- delivered_at: set for delivered rows, derived from the window date
       CASE WHEN st.status = 'delivered'
            THEN (now()::date - (1 + gen.n %% 3)) + time '10:30' ELSE NULL END,
       -- sla_due_at: promised deadline; ~88% of delivered land on/before it
       CASE
         WHEN st.status = 'delivered'
           THEN (now()::date - (1 + gen.n %% 3)) + CASE WHEN gen.n %% 8 = 0 THEN time '09:00' ELSE time '17:00' END
         WHEN st.status IN ('out_for_delivery','rescheduled','failed','returned')
           THEN (now()::date + (gen.n %% 3)) + time '17:00'
         ELSE NULL
       END
```

(The `%%` escaping matches the existing file's psycopg parameter style.)

- [ ] **Step 3: Verify the seed runs**

Run (against a scratch/local DB, per the project's seed mechanics): `uv run python db/seed_demo.py --help` or the project's documented invocation, then confirm rows populate:
Expected: no SQL error; `attempt_count` non-null, a mix of `delivered_at` set/null.

- [ ] **Step 4: Commit**

```bash
git add db/seed_demo.py
git commit -m "feat(seed): populate attempt_count/delivered_at/sla_due_at for demo orders"
```

---

## Task 7: Frontend types + API client

**Files:**
- Modify: `frontend/lib/types.ts` (`Metrics`, `Insights`, `NeedsAttention`; add `ChannelDay`, `AreaCount`; `EscalationSummary`, `InvestigationSummary`)
- Modify: `frontend/lib/api.ts` (no signature change — `getMetrics`/`getInsights` already typed)

- [ ] **Step 1: Update `types.ts`**

Replace `Metrics` (`frontend/lib/types.ts:43`):

```typescript
export type Metrics = {
  total_calls: number;
  first_attempt_success: number;
  on_time_rate: number;
  active_deliveries: number;
  at_risk: number;
  containment_rate: number;
  recovery_rate: number;
  avg_csat: number | null;
  avg_handle_time_seconds: number | null;
};
```

Replace `Insights` (`:60`) and add the row types:

```typescript
export type ChannelDay = { date: string; channels: Record<string, number> };
export type AreaCount = { area: string; count: number };

export type Insights = {
  interactions_per_day: ChannelDay[];
  intent_mix: { intent: string; count: number }[];
  disposition_mix: { disposition: string; count: number }[];
  failures_by_area: AreaCount[];
  needs_attention: {
    open_escalations: number;
    overdue_callbacks: number;
    pending_reschedules: number;
    pending_address_flags: number;
  };
  map_points: MapPoint[];
};
```

Add `reason` to `EscalationSummary` (`:35`): `reason: string | null;`
Add `twin_order_ref` to `InvestigationSummary` (`:25`): `twin_order_ref: string | null;`

- [ ] **Step 2: Run the frontend gate**

Run: `cd frontend && npx tsc --noEmit`
Expected: errors ONLY in `app/page.tsx` and `lib/insights.ts` (they reference removed fields — fixed in Task 8). No errors in `lib/`.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(fe): update metric/insight types for business KPIs"
```

---

## Task 8: Redesign the dashboard landing page

**Files:**
- Create: `frontend/components/WorkQueue.tsx`, `frontend/components/StackedBarChart.tsx`, `frontend/components/AgentStats.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/lib/insights.ts` (remove `networkRisk`)

- [ ] **Step 1: Create `WorkQueue.tsx`**

```tsx
import Link from "next/link";

type Row = { label: string; value: number; href: string };

export default function WorkQueue({
  openEscalations, overdueCallbacks, pendingReschedules, pendingAddressFlags,
}: {
  openEscalations: number; overdueCallbacks: number;
  pendingReschedules: number; pendingAddressFlags: number;
}) {
  const rows: Row[] = [
    { label: "Open escalations", value: openEscalations, href: "/escalations?status=open" },
    { label: "Overdue callbacks", value: overdueCallbacks, href: "/investigations?overdue=1" },
    { label: "Unsynced reschedules", value: pendingReschedules, href: "/reschedules" },
    { label: "Pending address flags", value: pendingAddressFlags, href: "/orders?status=failed" },
  ];
  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">Work queue</h2>
      <ul className="space-y-1">
        {rows.map((r) => (
          <li key={r.label}>
            <Link href={r.href}
              className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-panel-2">
              <span className="text-sm text-txt-dim">{r.label}</span>
              <span className={`font-mono text-lg font-semibold ${r.value > 0 ? "text-amber-400" : "text-txt-faint"}`}>
                {r.value}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `StackedBarChart.tsx`**

```tsx
"use client";

import { useMemo } from "react";
import type { ChannelDay } from "@/lib/types";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6"];

export default function StackedBarChart({ title, data }: { title: string; data: ChannelDay[] }) {
  const channels = useMemo(() => {
    const set = new Set<string>();
    data.forEach((d) => Object.keys(d.channels).forEach((c) => set.add(c)));
    return Array.from(set).sort();
  }, [data]);
  const color = (c: string) => COLORS[channels.indexOf(c) % COLORS.length];
  const max = Math.max(1, ...data.map((d) => Object.values(d.channels).reduce((a, b) => a + b, 0)));

  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">{title}</h2>
      <div className="flex h-40 items-end gap-1">
        {data.map((d) => (
          <div key={d.date} className="flex flex-1 flex-col-reverse" title={d.date}>
            {channels.map((c) => {
              const v = d.channels[c] ?? 0;
              return v ? (
                <div key={c} style={{ height: `${(v / max) * 100}%`, background: color(c) }} />
              ) : null;
            })}
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        {channels.map((c) => (
          <span key={c} className="flex items-center gap-1.5 text-xs text-txt-dim">
            <span className="inline-block h-2 w-2 rounded-sm" style={{ background: color(c) }} />
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `AgentStats.tsx`**

```tsx
function fmtPct(n: number) { return `${Math.round(n * 100)}%`; }

export default function AgentStats({
  containment, recovery, csat, handleTimeSeconds,
}: {
  containment: number; recovery: number; csat: number | null; handleTimeSeconds: number | null;
}) {
  const items = [
    { label: "Containment", value: fmtPct(containment) },
    { label: "Recovery", value: fmtPct(recovery) },
    { label: "CSAT", value: csat != null ? csat.toFixed(1) : "—" },
    { label: "Avg handle", value: handleTimeSeconds != null ? `${Math.round(handleTimeSeconds)}s` : "—" },
  ];
  return (
    <div className="rounded-xl border border-hairline bg-panel p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">Agent performance</h2>
      <div className="grid grid-cols-2 gap-3">
        {items.map((i) => (
          <div key={i.label}>
            <div className="font-mono text-2xl font-semibold text-txt">{i.value}</div>
            <div className="text-xs text-txt-dim">{i.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Remove `networkRisk` from `lib/insights.ts`**

Delete the `RiskLevel` type and `networkRisk` function (`frontend/lib/insights.ts:8-15`). Keep `HUB`, `activeOrders`, `healthCounts`, `buildDriverRoutes`.

- [ ] **Step 5: Rewrite `app/page.tsx`**

Replace `frontend/app/page.tsx` with:

```tsx
import Link from "next/link";
import AgentStats from "@/components/AgentStats";
import BarChart from "@/components/BarChart";
import CommandMapClient from "@/components/CommandMapClient";
import KpiStat from "@/components/KpiStat";
import RecentCalls from "@/components/RecentCalls";
import StackedBarChart from "@/components/StackedBarChart";
import WorkQueue from "@/components/WorkQueue";
import { Activity, Clock, Package, TriangleAlert } from "@/components/icons";
import { getCalls, getInsights, getMetrics, getOrders } from "@/lib/api";
import { activeOrders, buildDriverRoutes } from "@/lib/insights";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

const RANGES: { label: string; days: number }[] = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
];

const WISMO = new Set(["track", "status", "wismo", "where_is_my_order", "tracking"]);

export default async function CommandCenter({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const { range } = await searchParams;
  const selected = RANGES.find((r) => r.label === range) ?? RANGES[1];
  const [metrics, insights, calls, orders] = await Promise.all([
    getMetrics(selected.days),
    getInsights(selected.days),
    getCalls(),
    getOrders(),
  ]);

  const active = activeOrders(insights.map_points);
  const drivers = buildDriverRoutes(orders, insights.map_points);
  const intentMix = insights.intent_mix.map((d) => ({
    label: d.intent,
    value: d.count,
    accent: WISMO.has(d.intent.toLowerCase()),
  }));
  const areaFailures = insights.failures_by_area.map((a) => ({ label: a.area, value: a.count }));

  return (
    <div className="space-y-6 px-6 pb-6">
      <div className="sticky top-0 z-30 -mx-6 flex items-end justify-between border-b border-hairline bg-ink/95 px-6 py-4 backdrop-blur">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-txt">Shipa Delivery</h1>
          <div className="font-mono text-xs uppercase tracking-[0.3em] text-txt-faint">Operations</div>
        </div>
        <div className="flex gap-1 rounded-lg border border-hairline bg-panel p-1">
          {RANGES.map((r) => (
            <Link
              key={r.label}
              href={`/?range=${r.label}`}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                r.label === selected.label ? "bg-shipa-blue text-white" : "text-txt-dim hover:bg-panel-2"
              }`}
            >
              {r.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiStat label="First-Attempt Success" value={pct(metrics.first_attempt_success)} sub="delivered on attempt 1" tone="ok" Icon={Activity} />
        <KpiStat label="On-Time Rate" value={pct(metrics.on_time_rate)} sub="within promised window" tone="ok" Icon={Clock} />
        <KpiStat label="Active Deliveries" value={metrics.active_deliveries.toString()} sub="out for delivery" Icon={Package} />
        <KpiStat label="At-Risk" value={metrics.at_risk.toString()} sub="failed / returned" tone={metrics.at_risk > 0 ? "bad" : "ok"} Icon={TriangleAlert} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <CommandMapClient points={insights.map_points} drivers={drivers} />
        <WorkQueue
          openEscalations={insights.needs_attention.open_escalations}
          overdueCallbacks={insights.needs_attention.overdue_callbacks}
          pendingReschedules={insights.needs_attention.pending_reschedules}
          pendingAddressFlags={insights.needs_attention.pending_address_flags}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <AgentStats
          containment={metrics.containment_rate}
          recovery={metrics.recovery_rate}
          csat={metrics.avg_csat}
          handleTimeSeconds={metrics.avg_handle_time_seconds}
        />
        <StackedBarChart title={`Interactions per day (${selected.label})`} data={insights.interactions_per_day} />
        <BarChart title={`Voice intents (${selected.label})`} data={intentMix} orientation="horizontal" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title="Failures by area" data={areaFailures} orientation="horizontal" />
        <RecentCalls calls={calls.slice(0, 10)} />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Verify `BarChart` accepts the data shape + `Clock` icon exists**

Run: `cd frontend && cat components/BarChart.tsx | head -30 && grep -n "Clock\|Activity" components/icons.tsx`
If `BarChart`'s data prop doesn't include an optional `accent` field, either drop `accent` from `intentMix` (use `{ label, value }`) or extend `BarChart`'s row type with `accent?: boolean` and tint accented bars. If `Clock` is not exported from `components/icons`, replace the import + usage with an existing icon (e.g. `TrendingUp`).

- [ ] **Step 7: Run the frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm run build`
Expected: clean build.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/page.tsx frontend/lib/insights.ts frontend/components/WorkQueue.tsx frontend/components/StackedBarChart.tsx frontend/components/AgentStats.tsx
git commit -m "feat(fe): business-driven KPI strip, work queue, stacked interactions"
```

---

## Task 9: Shared filter primitives

**Files:**
- Create: `frontend/components/filters/SearchInput.tsx`, `frontend/components/filters/FilterSelect.tsx`, `frontend/components/filters/useTableFilters.ts`

- [ ] **Step 1: Create `useTableFilters.ts`**

URL-synced filter state: a free-text query plus named equality filters, read from and written to the URL.

```tsx
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

export function useTableFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const get = useCallback((key: string) => params.get(key) ?? "", [params]);

  const set = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(params.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, pathname, router],
  );

  return { get, set };
}

// Generic client-side filter: case-insensitive text match across `textFields`,
// plus exact-match for each provided equality filter.
export function applyFilters<T>(
  rows: T[],
  opts: {
    query: string;
    textFields: (keyof T)[];
    equals?: Partial<Record<keyof T, string>>;
    predicate?: (row: T) => boolean;
  },
): T[] {
  const q = opts.query.trim().toLowerCase();
  return rows.filter((row) => {
    if (opts.predicate && !opts.predicate(row)) return false;
    for (const [k, v] of Object.entries(opts.equals ?? {})) {
      if (v && String((row as Record<string, unknown>)[k] ?? "") !== v) return false;
    }
    if (!q) return true;
    return opts.textFields.some((f) =>
      String(row[f] ?? "").toLowerCase().includes(q),
    );
  });
}

export function optionsFor<T>(rows: T[], field: keyof T): string[] {
  return Array.from(new Set(rows.map((r) => String(r[field] ?? "")).filter(Boolean))).sort();
}
```

- [ ] **Step 2: Create `SearchInput.tsx`**

```tsx
"use client";

export default function SearchInput({
  value, onChange, placeholder,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder ?? "Search…"}
      className="w-64 rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt placeholder:text-txt-faint"
    />
  );
}
```

- [ ] **Step 3: Create `FilterSelect.tsx`**

```tsx
"use client";

export default function FilterSelect({
  value, onChange, options, allLabel,
}: {
  value: string; onChange: (v: string) => void; options: string[]; allLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 4: Run the frontend gate**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean (these are leaf modules; unused-export warnings are acceptable until Task 10 consumes them).

- [ ] **Step 5: Commit**

```bash
git add frontend/components/filters
git commit -m "feat(fe): shared URL-synced table filter primitives"
```

---

## Task 10: Filterable table components + wire the four pages

**Files:**
- Modify: `frontend/components/OrdersTable.tsx`
- Create: `frontend/components/CustomersTable.tsx`, `EscalationsTable.tsx`, `InvestigationsTable.tsx`
- Modify: `frontend/app/customers/page.tsx`, `escalations/page.tsx`, `investigations/page.tsx`

- [ ] **Step 1: Rewrite `OrdersTable.tsx` onto the shared primitives**

```tsx
"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { OrderListItem } from "@/lib/types";

export default function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  const { get, set } = useTableFilters();
  const rows = useMemo(
    () =>
      applyFilters(orders, {
        query: get("q"),
        textFields: ["twin_order_ref", "customer_name", "merchant"],
        equals: { status: get("status"), delivery_area: get("area"), merchant: get("merchant"), assigned_driver: get("driver") },
      }),
    [orders, get],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Order, customer, merchant…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(orders, "status")} allLabel="All statuses" />
        <FilterSelect value={get("area")} onChange={(v) => set("area", v)} options={optionsFor(orders, "delivery_area")} allLabel="All areas" />
        <FilterSelect value={get("merchant")} onChange={(v) => set("merchant", v)} options={optionsFor(orders, "merchant")} allLabel="All merchants" />
        <FilterSelect value={get("driver")} onChange={(v) => set("driver", v)} options={optionsFor(orders, "assigned_driver")} allLabel="All drivers" />
        <span className="text-sm text-txt-dim">{rows.length} of {orders.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
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
            {rows.map((o) => (
              <tr key={o.order_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">{o.twin_order_ref}</Link>
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
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No orders match.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `CustomersTable.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useMemo } from "react";
import SearchInput from "@/components/filters/SearchInput";
import FilterSelect from "@/components/filters/FilterSelect";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import type { CustomerListItem } from "@/lib/types";

export default function CustomersTable({ customers }: { customers: CustomerListItem[] }) {
  const { get, set } = useTableFilters();
  const rows = useMemo(() => {
    const filtered = applyFilters(customers, {
      query: get("q"),
      textFields: ["full_name", "primary_phone"],
      equals: { language_pref: get("lang") },
    });
    return get("sort") === "orders"
      ? [...filtered].sort((a, b) => b.order_count - a.order_count)
      : filtered;
  }, [customers, get]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Name or phone…" />
        <FilterSelect value={get("lang")} onChange={(v) => set("lang", v)} options={optionsFor(customers, "language_pref")} allLabel="All languages" />
        <FilterSelect value={get("sort")} onChange={(v) => set("sort", v)} options={["orders"]} allLabel="Default order" />
        <span className="text-sm text-txt-dim">{rows.length} of {customers.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Phone</th>
              <th className="px-4 py-3 font-semibold">Language</th>
              <th className="px-4 py-3 font-semibold">Orders</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.customer_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/customers/${c.customer_id}`} className="font-medium text-shipa-blue hover:underline">{c.full_name}</Link>
                </td>
                <td className="px-4 py-3">{c.primary_phone}</td>
                <td className="px-4 py-3">{c.language_pref ?? "—"}</td>
                <td className="px-4 py-3">{c.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No customers match.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `EscalationsTable.tsx`**

```tsx
"use client";

import { useMemo } from "react";
import SearchInput from "@/components/filters/SearchInput";
import FilterSelect from "@/components/filters/FilterSelect";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { EscalationSummary } from "@/lib/types";

export default function EscalationsTable({ rows: data }: { rows: EscalationSummary[] }) {
  const { get, set } = useTableFilters();
  const rows = useMemo(
    () =>
      applyFilters(data, {
        query: get("q"),
        textFields: ["category", "reason"],
        equals: { status: get("status"), category: get("category") },
      }),
    [data, get],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Category or reason…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(data, "status")} allLabel="All statuses" />
        <FilterSelect value={get("category")} onChange={(v) => set("category", v)} options={optionsFor(data, "category")} allLabel="All categories" />
        <span className="text-sm text-txt-dim">{rows.length} of {data.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.escalation_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">{r.category}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No escalations match.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `InvestigationsTable.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useMemo } from "react";
import SearchInput from "@/components/filters/SearchInput";
import FilterSelect from "@/components/filters/FilterSelect";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { InvestigationSummary } from "@/lib/types";

export default function InvestigationsTable({ rows: data }: { rows: InvestigationSummary[] }) {
  const { get, set } = useTableFilters();
  const overdue = get("overdue") === "1";
  const now = Date.now();
  const rows = useMemo(
    () =>
      applyFilters(data, {
        query: get("q"),
        textFields: ["twin_order_ref"],
        equals: { status: get("status"), type: get("type") },
        predicate: overdue
          ? (r) => r.status === "open" && !!r.callback_due_at && new Date(r.callback_due_at).getTime() < now
          : undefined,
      }),
    [data, get, overdue, now],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Order ref…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(data, "status")} allLabel="All statuses" />
        <FilterSelect value={get("type")} onChange={(v) => set("type", v)} options={optionsFor(data, "type")} allLabel="All types" />
        <label className="flex items-center gap-2 text-sm text-txt-dim">
          <input type="checkbox" checked={overdue} onChange={(e) => set("overdue", e.target.checked ? "1" : "")} />
          Overdue only
        </label>
        <span className="text-sm text-txt-dim">{rows.length} of {data.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Type</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Callback due</th>
              <th className="px-4 py-3 font-semibold">Opened</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.investigation_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/orders/${r.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {r.twin_order_ref ?? r.order_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3">{r.type}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">{r.callback_due_at ? new Date(r.callback_due_at).toLocaleString() : "—"}</td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.opened_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No investigations match.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Wire the three pages**

`frontend/app/customers/page.tsx`:

```tsx
import CustomersTable from "@/components/CustomersTable";
import { getCustomers } from "@/lib/api";

export default async function CustomersPage() {
  const customers = await getCustomers();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Customers</h1>
      <CustomersTable customers={customers} />
    </div>
  );
}
```

`frontend/app/escalations/page.tsx`:

```tsx
import EscalationsTable from "@/components/EscalationsTable";
import { getEscalations } from "@/lib/api";

export default async function EscalationsPage() {
  const rows = await getEscalations();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Escalations</h1>
      <EscalationsTable rows={rows} />
    </div>
  );
}
```

`frontend/app/investigations/page.tsx`:

```tsx
import InvestigationsTable from "@/components/InvestigationsTable";
import { getInvestigations } from "@/lib/api";

export default async function InvestigationsPage() {
  const rows = await getInvestigations();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Investigations</h1>
      <InvestigationsTable rows={rows} />
    </div>
  );
}
```

- [ ] **Step 6: Run the frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm run build`
Expected: clean build.

- [ ] **Step 7: Manually verify URL sync + deep-link**

Run: `cd frontend && npm run dev`, then:
- `/orders` → pick a status; confirm URL gains `?status=…` and reloading preserves the filter.
- From the dashboard Work Queue, click "Overdue callbacks"; confirm it lands on `/investigations?overdue=1` with the checkbox checked and the list filtered.

- [ ] **Step 8: Commit**

```bash
git add frontend/components/OrdersTable.tsx frontend/components/CustomersTable.tsx frontend/components/EscalationsTable.tsx frontend/components/InvestigationsTable.tsx frontend/app/customers/page.tsx frontend/app/escalations/page.tsx frontend/app/investigations/page.tsx
git commit -m "feat(fe): full URL-synced filters on orders, customers, escalations, investigations"
```

---

## Final verification

- [ ] **Backend:** `uv run pytest tests/test_metrics_service.py tests/test_insights_service.py tests/test_twin_sync.py tests/test_dashboard_lookups.py -v` — all PASS.
- [ ] **Migration round-trip:** `uv run alembic downgrade -1 && uv run alembic upgrade head` — clean.
- [ ] **Frontend:** `cd frontend && npx tsc --noEmit && npm run lint && npm run build` — clean.
- [ ] **Spec coverage:** every section of the spec maps to a task (model+migration §2→T1, propagation §2→T2, metrics §3/§4→T3/T4, lookups §6→T5/T9/T10, seed §2→T6, FE §5→T7/T8, filters §6→T9/T10).
