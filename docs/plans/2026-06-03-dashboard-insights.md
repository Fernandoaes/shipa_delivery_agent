# Dashboard Insights & Calls — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Overview home (KPIs, charts, live deliveries map, needs-attention, recent calls), a lean Calls view, and customer-oriented call history to the read-only SHIPA ops dashboard.

**Architecture:** One new server aggregation endpoint `GET /insights`; safe extensions to `CallSummary` and `CustomerDetail` (derived joins only — no transcript/PII, `otp_code` stays excluded). Frontend reuses the existing design system and react-leaflet map pattern. No DB migration (all tables already exist). No new frontend dependencies.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 (backend), pytest against a real `shipa_test` Postgres, Next.js 16 (App Router, server components) + Tailwind v4 + react-leaflet (frontend), psycopg seed run via `railway run`.

> ⚠️ **Next.js 16 caveat:** This repo's `frontend/AGENTS.md` warns the installed Next.js has breaking changes vs. training data. Before writing/altering any frontend code, skim the relevant guide under `frontend/node_modules/next/dist/docs/`. Mirror existing files (`app/orders/[id]/page.tsx`, `components/MapClient.tsx`) for current API shapes (async `params: Promise<…>`, server components by default).

---

## File Structure

**Backend**
- Modify `app/schemas/dashboard.py` — extend `CallSummary`, `CustomerDetail`; add `Insights` + sub-models.
- Create `app/services/calls.py` — `list_calls` with join + `_call_summary` helper.
- Create `app/services/insights.py` — `compute_insights`.
- Modify `app/services/customers.py` — call history, avg CSAT, last contact, follow-up flag.
- Modify `app/routers/dashboard.py` — `/calls` uses the service; add `GET /insights`.
- Tests: `tests/test_calls_service.py`, `tests/test_insights_service.py`, extend `tests/test_customers_service.py`.

**Mock data**
- Create `db/seed_demo_calls.py` — calls + escalations/reschedules/investigations for the `*-D*` rows.

**Frontend**
- Modify `frontend/lib/types.ts`, `frontend/lib/api.ts`.
- Modify `frontend/components/TopBar.tsx`.
- Create `frontend/components/KpiCard.tsx`, `BarChart.tsx`, `NeedsAttention.tsx`, `RecentCalls.tsx`, `DeliveriesMap.tsx`, `DeliveriesMapClient.tsx`, `CallsTable.tsx`.
- Modify `frontend/app/page.tsx` (Overview), `frontend/app/customers/[id]/page.tsx`, `frontend/app/orders/page.tsx`.
- Create `frontend/app/calls/page.tsx`.

---

## Task 1: Extend CallSummary + calls service (join customer name + order ref)

**Files:**
- Modify: `app/schemas/dashboard.py` (CallSummary)
- Create: `app/services/calls.py`
- Modify: `app/routers/dashboard.py` (list_calls)
- Test: `tests/test_calls_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_calls_service.py
import datetime as dt

from app.models import Call
from app.services.calls import list_calls
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed_call(db, order, **kw):
    call = Call(
        direction=kw.get("direction", "inbound"),
        agent_type=kw.get("agent_type", "inbound_support"),
        verification_status=kw.get("verification_status", "passed"),
        intent=kw.get("intent", "delivery_status"),
        disposition=kw.get("disposition", "info_provided"),
        csat_score=kw.get("csat_score", 4),
        order_id=order.order_id,
        customer_id=order.customer_id,
        started_at=kw.get("started_at", dt.datetime.now()),
    )
    db.add(call)
    db.flush()
    return call


def test_list_calls_includes_customer_and_order(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    from app.models import Order
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order)
    items = list_calls(db)
    assert len(items) == 1
    assert items[0].twin_order_ref == "TWIN-1001"
    assert items[0].customer_name == order.customer.full_name


def test_list_calls_orders_newest_first(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    from app.models import Order
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 1, 9, 0))
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 2, 9, 0))
    items = list_calls(db)
    assert items[0].started_at > items[1].started_at
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calls_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.calls`.

- [ ] **Step 3: Extend the schema**

In `app/schemas/dashboard.py`, replace the `CallSummary` class body's trailing fields so it reads:

```python
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
    customer_name: str | None = None
    twin_order_ref: str | None = None
    # deliberately no transcript / otp / raw caller PII beyond what ops needs

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create the calls service**

```python
# app/services/calls.py
from sqlalchemy.orm import Session

from app.models import Call, Customer, Order
from app.schemas.dashboard import CallSummary


def _call_summary(call: Call, customer_name: str | None, twin_order_ref: str | None) -> CallSummary:
    return CallSummary(
        call_id=call.call_id,
        direction=call.direction,
        language=call.language,
        verification_status=call.verification_status,
        intent=call.intent,
        disposition=call.disposition,
        csat_score=float(call.csat_score) if call.csat_score is not None else None,
        started_at=call.started_at,
        ended_at=call.ended_at,
        customer_name=customer_name,
        twin_order_ref=twin_order_ref,
    )


def list_calls(db: Session) -> list[CallSummary]:
    rows = (
        db.query(Call, Customer.full_name, Order.twin_order_ref)
        .outerjoin(Customer, Call.customer_id == Customer.customer_id)
        .outerjoin(Order, Call.order_id == Order.order_id)
        .order_by(Call.started_at.desc())
        .all()
    )
    return [_call_summary(call, name, ref) for call, name, ref in rows]
```

- [ ] **Step 5: Wire the router to the service**

In `app/routers/dashboard.py`: add `from app.services.calls import list_calls as list_calls_service` to the service imports, and replace the `/calls` handler body:

```python
@router.get("/calls", response_model=list[CallSummary])
def list_calls(db: Session = Depends(get_db)):
    return list_calls_service(db)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_calls_service.py tests/test_dashboard.py -v`
Expected: PASS (including the existing `test_calls_list_hides_otp`).

- [ ] **Step 7: Commit**

```bash
git add app/schemas/dashboard.py app/services/calls.py app/routers/dashboard.py tests/test_calls_service.py
git commit -m "feat(api): calls list joins customer name + order ref"
```

---

## Task 2: Insights schema, service, and `/insights` endpoint

**Files:**
- Modify: `app/schemas/dashboard.py` (add Insights models)
- Create: `app/services/insights.py`
- Modify: `app/routers/dashboard.py` (add endpoint)
- Test: `tests/test_insights_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_insights_service.py
import datetime as dt

from app.models import Call, Escalation, Order, Reschedule
from app.services.insights import compute_insights
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    now = dt.datetime.now()
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                intent="reschedule", disposition="rescheduled", csat_score=5,
                order_id=order.order_id, customer_id=order.customer_id, started_at=now))
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="failed",
                intent="not_received", disposition=None, csat_score=None,
                order_id=order.order_id, customer_id=order.customer_id,
                started_at=now - dt.timedelta(days=3)))
    db.flush()
    return order


def test_calls_per_day_is_zero_filled_14_days(db):
    _seed(db)
    out = compute_insights(db)
    assert len(out["calls_per_day"]) == 14
    assert sum(d["count"] for d in out["calls_per_day"]) == 2
    dates = [d["date"] for d in out["calls_per_day"]]
    assert dates == sorted(dates)


def test_intent_and_disposition_mix(db):
    _seed(db)
    out = compute_insights(db)
    intents = {d["intent"]: d["count"] for d in out["intent_mix"]}
    assert intents["reschedule"] == 1 and intents["not_received"] == 1
    dispositions = {d["disposition"]: d["count"] for d in out["disposition_mix"]}
    assert dispositions["unknown"] == 1  # the None disposition is labeled "unknown"


def test_needs_attention_counts(db):
    order = _seed(db)
    call = db.query(Call).first()
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=call.call_id, order_id=order.order_id,
                      requested_date=dt.date.today(), status="requested",
                      synced_to_twin_at=None, created_at=dt.datetime.now()))
    order.status = "failed"
    db.flush()
    out = compute_insights(db)
    assert out["needs_attention"]["open_escalations"] == 1
    assert out["needs_attention"]["pending_reschedules"] == 1
    assert out["needs_attention"]["failed_orders"] == 1


def test_map_points_only_active_with_coords(db):
    order = _seed(db)
    order.status = "delivered"  # terminal -> excluded
    order.delivery_lat, order.delivery_lng = 25.1, 55.2
    db.flush()
    out = compute_insights(db)
    assert all(p["status"] in ("out_for_delivery", "pending", "failed", "rescheduled")
               for p in out["map_points"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_insights_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.insights`.

- [ ] **Step 3: Add the schemas**

Append to `app/schemas/dashboard.py`:

```python
class DayCount(BaseModel):
    date: dt.date
    count: int


class IntentCount(BaseModel):
    intent: str
    count: int


class DispositionCount(BaseModel):
    disposition: str
    count: int


class NeedsAttention(BaseModel):
    open_escalations: int
    pending_reschedules: int
    failed_orders: int


class MapPoint(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    status: str
    delivery_area: str | None
    delivery_lat: float
    delivery_lng: float


class Insights(BaseModel):
    calls_per_day: list[DayCount]
    intent_mix: list[IntentCount]
    disposition_mix: list[DispositionCount]
    needs_attention: NeedsAttention
    map_points: list[MapPoint]
```

- [ ] **Step 4: Create the service**

```python
# app/services/insights.py
import datetime as dt
from collections import Counter

from sqlalchemy.orm import Session

from app.models import Call, Escalation, Order, Reschedule

_ACTIVE_STATUSES = ("out_for_delivery", "pending", "failed", "rescheduled")


def compute_insights(db: Session) -> dict:
    calls = db.query(Call).all()

    today = dt.date.today()
    start = today - dt.timedelta(days=13)
    per_day: dict[dt.date, int] = {start + dt.timedelta(days=i): 0 for i in range(14)}
    for c in calls:
        d = c.started_at.date()
        if d in per_day:
            per_day[d] += 1
    calls_per_day = [{"date": d, "count": n} for d, n in sorted(per_day.items())]

    intent_counter = Counter((c.intent or "unknown") for c in calls)
    disposition_counter = Counter((c.disposition or "unknown") for c in calls)
    intent_mix = [{"intent": k, "count": v} for k, v in intent_counter.most_common()]
    disposition_mix = [{"disposition": k, "count": v} for k, v in disposition_counter.most_common()]

    needs_attention = {
        "open_escalations": db.query(Escalation).filter(Escalation.status == "open").count(),
        "pending_reschedules": db.query(Reschedule).filter(Reschedule.synced_to_twin_at.is_(None)).count(),
        "failed_orders": db.query(Order).filter(Order.status.in_(["failed", "returned"])).count(),
    }

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
        "calls_per_day": calls_per_day,
        "intent_mix": intent_mix,
        "disposition_mix": disposition_mix,
        "needs_attention": needs_attention,
        "map_points": map_points,
    }
```

- [ ] **Step 5: Add the endpoint**

In `app/routers/dashboard.py`: add `Insights` to the `app.schemas.dashboard` import, add `from app.services.insights import compute_insights`, and add a handler (next to `metrics`):

```python
@router.get("/insights", response_model=Insights)
def insights(db: Session = Depends(get_db)):
    return compute_insights(db)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_insights_service.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add app/schemas/dashboard.py app/services/insights.py app/routers/dashboard.py tests/test_insights_service.py
git commit -m "feat(api): add /insights aggregation endpoint"
```

---

## Task 3: Customer detail — call history, avg CSAT, last contact, follow-up flag

**Files:**
- Modify: `app/schemas/dashboard.py` (CustomerDetail)
- Modify: `app/services/customers.py`
- Test: `tests/test_customers_service.py` (extend)

- [ ] **Step 1: Write the failing test (append to `tests/test_customers_service.py`)**

```python
import datetime as dt

from app.models import Call, Order


def test_customer_detail_includes_call_insights(db):
    from app.twin.mock import MockTwinClient
    from app.twin.sync import upsert_orders
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                intent="delivery_status", disposition="info_provided", csat_score=2,
                order_id=order.order_id, customer_id=order.customer_id,
                started_at=dt.datetime(2026, 1, 5, 10, 0)))
    db.flush()
    detail = get_customer_detail(db, order.customer_id)
    assert len(detail.calls) == 1
    assert detail.calls[0].twin_order_ref == "TWIN-1001"
    assert detail.avg_csat == 2.0
    assert detail.last_contact_at == dt.datetime(2026, 1, 5, 10, 0)
    assert detail.needs_follow_up is True  # avg csat < 3.0
```

(The file already imports `get_customer_detail`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_customers_service.py::test_customer_detail_includes_call_insights -v`
Expected: FAIL — `CustomerDetail` has no field `calls`.

- [ ] **Step 3: Extend the schema**

In `app/schemas/dashboard.py`, replace the `CustomerDetail` class:

```python
class CustomerDetail(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    orders: list[OrderListItem]
    calls: list[CallSummary]
    avg_csat: float | None
    last_contact_at: dt.datetime | None
    needs_follow_up: bool
```

- [ ] **Step 4: Update the service**

Replace `get_customer_detail` in `app/services/customers.py` (and add imports `from app.models import Call, Customer` and `from app.services.calls import _call_summary`):

```python
def get_customer_detail(db: Session, customer_id: uuid.UUID) -> CustomerDetail | None:
    c = db.get(Customer, customer_id)
    if c is None:
        return None
    ref_by_order = {o.order_id: o.twin_order_ref for o in c.orders}
    calls = (
        db.query(Call)
        .filter(Call.customer_id == customer_id)
        .order_by(Call.started_at.desc())
        .all()
    )
    call_summaries = [_call_summary(x, c.full_name, ref_by_order.get(x.order_id)) for x in calls]
    csats = [float(x.csat_score) for x in calls if x.csat_score is not None]
    avg_csat = round(sum(csats) / len(csats), 2) if csats else None
    last_contact_at = max((x.started_at for x in calls), default=None)
    has_failed_order = any(o.status in ("failed", "returned") for o in c.orders)
    needs_follow_up = (avg_csat is not None and avg_csat < 3.0) or has_failed_order
    return CustomerDetail(
        customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
        language_pref=c.language_pref,
        orders=[_order_list_item(o) for o in sorted(c.orders, key=lambda o: o.twin_order_ref)],
        calls=call_summaries, avg_csat=avg_csat, last_contact_at=last_contact_at,
        needs_follow_up=needs_follow_up,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_customers_service.py -v`
Expected: PASS (all, including the new test).

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/schemas/dashboard.py app/services/customers.py tests/test_customers_service.py
git commit -m "feat(api): customer detail adds call history + csat + follow-up flag"
```

---

## Task 4: Mock data — calls + escalations/reschedules/investigations

**Files:**
- Create: `db/seed_demo_calls.py`

No unit test (seed script). Verified by running against the local/test DB then production.

- [ ] **Step 1: Write the seed**

```python
# db/seed_demo_calls.py
"""Demo seed: one call per *-D* order, plus a few escalations / reschedules /
investigations so the dashboard's insights + needs-attention are populated.

Idempotent: calls keyed by happyrobot_call_id 'HR-<order ref>' + ON CONFLICT;
operation rows keyed by the unique call_id + ON CONFLICT. Run:

    railway run --service Postgres -- uv run python db/seed_demo_calls.py

Mock data only — never run against a real Twin database.
"""

import os
import sys

import psycopg

URL = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
if not URL:
    sys.exit("No DATABASE_PUBLIC_URL / DATABASE_URL in environment")
URL = URL.replace("postgresql+psycopg://", "postgresql://")

# Deterministic int in [0, n) from a stable hash of the order ref.
def _h(expr_col: str, lo: int, span: int, slc: str) -> str:
    return f"({lo} + (('x'||substr(md5({expr_col}),{slc}))::bit(16)::int % {span}))"

CALLS_SQL = f"""
INSERT INTO calls (call_id, happyrobot_call_id, order_id, customer_id, direction, agent_type,
                   language, verification_status, intent, disposition, csat_score, started_at)
SELECT gen_random_uuid(), 'HR-' || o.twin_order_ref, o.order_id, o.customer_id,
       'inbound', 'inbound_support', cu.language_pref,
       CASE WHEN o.status IN ('delivered','out_for_delivery') THEN 'passed'
            WHEN o.status IN ('failed','rescheduled') THEN 'partial'
            ELSE 'not_started' END,
       CASE o.status WHEN 'failed' THEN 'not_received'
                     WHEN 'rescheduled' THEN 'reschedule'
                     WHEN 'returned' THEN 'return_query'
                     ELSE 'delivery_status' END,
       CASE o.status WHEN 'failed' THEN 'investigation_opened'
                     WHEN 'rescheduled' THEN 'rescheduled'
                     WHEN 'returned' THEN 'escalated'
                     WHEN 'pending' THEN NULL
                     ELSE 'info_provided' END,
       {_h("o.twin_order_ref", 2, 4, "1,4")}::numeric,
       now()
         - ({_h("o.twin_order_ref", 0, 14, "5,4")} || ' days')::interval
         - ({_h("o.twin_order_ref", 0, 24, "9,4")} || ' hours')::interval
FROM orders o JOIN customers cu ON cu.customer_id = o.customer_id
WHERE o.twin_order_ref LIKE 'TWIN-D%'
ON CONFLICT (happyrobot_call_id) DO NOTHING;
"""

ENDED_SQL = f"""
UPDATE calls
SET ended_at = started_at + ({_h("happyrobot_call_id", 40, 320, "1,4")} || ' seconds')::interval
WHERE happyrobot_call_id LIKE 'HR-TWIN-D%' AND ended_at IS NULL;
"""

ESCALATIONS_SQL = """
INSERT INTO escalations (escalation_id, call_id, order_id, category, reason, status, created_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, 'delivery_dispute', 'Customer dispute (mock)',
       'open', c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'returned'
ON CONFLICT (call_id) DO NOTHING;
"""

RESCHEDULES_SQL = """
INSERT INTO reschedules (reschedule_id, call_id, order_id, requested_date, requested_window,
                         reason, status, synced_to_twin_at, created_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, (now()::date + 2), '13:00-17:00',
       'Not home (mock)', 'requested', NULL, c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'rescheduled'
ON CONFLICT (call_id) DO NOTHING;
"""

INVESTIGATIONS_SQL = """
INSERT INTO investigations (investigation_id, call_id, order_id, type, status, callback_due_at, opened_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, 'not_received', 'open',
       now() + interval '1 day', c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'failed'
ON CONFLICT (call_id) DO NOTHING;
"""


def main() -> None:
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CALLS_SQL)
            cur.execute(ENDED_SQL)
            cur.execute(ESCALATIONS_SQL)
            cur.execute(RESCHEDULES_SQL)
            cur.execute(INVESTIGATIONS_SQL)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%%'")
            calls = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM escalations WHERE status='open'")
            esc = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM reschedules WHERE synced_to_twin_at IS NULL")
            resc = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM investigations WHERE status='open'")
            inv = cur.fetchone()[0]
    print(f"calls(D)={calls}  open_escalations={esc}  pending_reschedules={resc}  open_investigations={inv}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run against the test DB to confirm SQL validity**

Run: `DATABASE_PUBLIC_URL="$(uv run python -c "from app.config import settings; from sqlalchemy.engine import make_url; u=make_url(settings.database_url).set(database='shipa_test'); print(u.render_as_string(hide_password=False).replace('postgresql+psycopg','postgresql'))")" uv run python db/seed_demo_calls.py`
Expected: prints a counts line without error (counts may be 0 if `shipa_test` has no `*-D*` orders — that's fine; we're validating SQL parses/executes).

- [ ] **Step 3: Commit**

```bash
git add db/seed_demo_calls.py
git commit -m "chore(seed): demo calls + escalations/reschedules/investigations"
```

*(Run against production in the final deploy task.)*

---

## Task 5: Frontend types + API client

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add types (append to `frontend/lib/types.ts`)**

```typescript
export type Metrics = {
  total_calls: number;
  first_attempt_rate: number;
  deflection_rate: number;
  avg_csat: number | null;
  avg_handle_time_seconds: number | null;
};

export type Call = {
  call_id: string;
  direction: string;
  language: string | null;
  verification_status: string;
  intent: string | null;
  disposition: string | null;
  csat_score: number | null;
  started_at: string;
  ended_at: string | null;
  customer_name: string | null;
  twin_order_ref: string | null;
};

export type MapPoint = {
  order_id: string;
  twin_order_ref: string;
  status: string;
  delivery_area: string | null;
  delivery_lat: number;
  delivery_lng: number;
};

export type Insights = {
  calls_per_day: { date: string; count: number }[];
  intent_mix: { intent: string; count: number }[];
  disposition_mix: { disposition: string; count: number }[];
  needs_attention: { open_escalations: number; pending_reschedules: number; failed_orders: number };
  map_points: MapPoint[];
};
```

Then extend `CustomerDetail` in the same file:

```typescript
export type CustomerDetail = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
  orders: OrderListItem[];
  calls: Call[];
  avg_csat: number | null;
  last_contact_at: string | null;
  needs_follow_up: boolean;
};
```

- [ ] **Step 2: Add API functions (append to `frontend/lib/api.ts`, and extend the import)**

Update the type import at the top to add `Call`, `Insights`, `Metrics`, then append:

```typescript
export const getMetrics = () => get<Metrics>("/metrics");
export const getInsights = () => get<Insights>("/insights");
export const getCalls = () => get<Call[]>("/calls");
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat(fe): types + api client for metrics, insights, calls"
```

---

## Task 6: TopBar (Overview link) + KpiCard + BarChart

**Files:**
- Modify: `frontend/components/TopBar.tsx`
- Create: `frontend/components/KpiCard.tsx`, `frontend/components/BarChart.tsx`

- [ ] **Step 1: Update TopBar**

In `frontend/components/TopBar.tsx`, change `links` and the `active` computation:

```typescript
const links = [
  { href: "/", label: "Overview" },
  { href: "/orders", label: "Orders" },
  { href: "/customers", label: "Customers" },
  { href: "/calls", label: "Calls" },
];
```

And inside the map, replace the `active` line:

```typescript
const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
```

Also change the logo `Link href="/orders"` to `href="/"`.

- [ ] **Step 2: Create KpiCard**

```tsx
// frontend/components/KpiCard.tsx
export default function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-shipa-ink/50">{label}</div>
      <div className="mt-1 text-2xl font-bold text-shipa-ink">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-shipa-ink/50">{sub}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Create BarChart (dependency-free, server component)**

```tsx
// frontend/components/BarChart.tsx
export type Bar = { label: string; value: number };

export default function BarChart({
  title, data, orientation = "vertical",
}: { title: string; data: Bar[]; orientation?: "vertical" | "horizontal" }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-shipa-ink">{title}</h2>
      {orientation === "vertical" ? (
        <div className="flex h-40 items-end gap-1">
          {data.map((d, i) => (
            <div key={i} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${d.label}: ${d.value}`}>
              <div className="w-full rounded-t bg-shipa-blue/80" style={{ height: `${(d.value / max) * 100}%` }} />
              <div className="text-[10px] text-shipa-ink/40">{d.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data.map((d, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <div className="w-28 truncate text-shipa-ink/70" title={d.label}>{d.label}</div>
              <div className="h-4 flex-1 rounded bg-shipa-sky">
                <div className="h-4 rounded bg-shipa-blue/80" style={{ width: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="w-8 text-right text-shipa-ink/60">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/TopBar.tsx frontend/components/KpiCard.tsx frontend/components/BarChart.tsx
git commit -m "feat(fe): Overview nav link + KpiCard + BarChart"
```

---

## Task 7: NeedsAttention + RecentCalls + Overview page (no map yet)

**Files:**
- Create: `frontend/components/NeedsAttention.tsx`, `frontend/components/RecentCalls.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create NeedsAttention**

```tsx
// frontend/components/NeedsAttention.tsx
import Link from "next/link";

type Item = { label: string; count: number; href: string; tone: string };

export default function NeedsAttention({
  openEscalations, pendingReschedules, failedOrders,
}: { openEscalations: number; pendingReschedules: number; failedOrders: number }) {
  const items: Item[] = [
    { label: "Open escalations", count: openEscalations, href: "/calls", tone: "text-red-700" },
    { label: "Pending reschedules", count: pendingReschedules, href: "/calls", tone: "text-amber-700" },
    { label: "Failed / returned orders", count: failedOrders, href: "/orders?status=failed", tone: "text-red-700" },
  ];
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-shipa-ink">Needs attention</h2>
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.label}>
            <Link href={it.href} className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-shipa-sky/60">
              <span className="text-sm text-shipa-ink/70">{it.label}</span>
              <span className={`text-lg font-bold ${it.count > 0 ? it.tone : "text-shipa-ink/30"}`}>{it.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create RecentCalls**

```tsx
// frontend/components/RecentCalls.tsx
import Link from "next/link";
import type { Call } from "@/lib/types";

export default function RecentCalls({ calls }: { calls: Call[] }) {
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white">
      <h2 className="border-b border-shipa-sky-accent px-5 py-3 text-sm font-semibold text-shipa-ink">Recent calls</h2>
      <table className="w-full text-left text-sm">
        <thead className="bg-shipa-sky text-shipa-ink/70">
          <tr>
            <th className="px-4 py-2 font-semibold">When</th>
            <th className="px-4 py-2 font-semibold">Customer</th>
            <th className="px-4 py-2 font-semibold">Intent</th>
            <th className="px-4 py-2 font-semibold">Disposition</th>
            <th className="px-4 py-2 font-semibold">CSAT</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c) => (
            <tr key={c.call_id} className="border-t border-shipa-sky-accent">
              <td className="px-4 py-2 text-shipa-ink/70">{new Date(c.started_at).toLocaleString()}</td>
              <td className="px-4 py-2">{c.customer_name ?? "—"}</td>
              <td className="px-4 py-2">{c.intent ?? "—"}</td>
              <td className="px-4 py-2">{c.disposition ?? "—"}</td>
              <td className="px-4 py-2">{c.csat_score ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Replace `frontend/app/page.tsx` (Overview — map added in Task 8)**

```tsx
// frontend/app/page.tsx
import BarChart from "@/components/BarChart";
import KpiCard from "@/components/KpiCard";
import NeedsAttention from "@/components/NeedsAttention";
import RecentCalls from "@/components/RecentCalls";
import { getCalls, getInsights, getMetrics } from "@/lib/api";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export default async function OverviewPage() {
  const [metrics, insights, calls] = await Promise.all([getMetrics(), getInsights(), getCalls()]);
  const callsPerDay = insights.calls_per_day.map((d) => ({
    label: new Date(d.date).getDate().toString(),
    value: d.count,
  }));
  const intentMix = insights.intent_mix.map((d) => ({ label: d.intent, value: d.count }));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-shipa-ink">Overview</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <KpiCard label="Total calls" value={metrics.total_calls.toString()} />
        <KpiCard label="First-attempt" value={pct(metrics.first_attempt_rate)} />
        <KpiCard label="Deflection" value={pct(metrics.deflection_rate)} />
        <KpiCard label="Avg CSAT" value={metrics.avg_csat?.toFixed(1) ?? "—"} sub="of 5" />
        <KpiCard
          label="Avg handle"
          value={metrics.avg_handle_time_seconds ? `${Math.round(metrics.avg_handle_time_seconds)}s` : "—"}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title="Calls per day (14d)" data={callsPerDay} />
        <BarChart title="Intent mix" data={intentMix} orientation="horizontal" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1"><NeedsAttention {...{
          openEscalations: insights.needs_attention.open_escalations,
          pendingReschedules: insights.needs_attention.pending_reschedules,
          failedOrders: insights.needs_attention.failed_orders,
        }} /></div>
        <div className="md:col-span-2"><RecentCalls calls={calls.slice(0, 10)} /></div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/NeedsAttention.tsx frontend/components/RecentCalls.tsx frontend/app/page.tsx
git commit -m "feat(fe): Overview page with KPIs, charts, needs-attention, recent calls"
```

---

## Task 8: Live deliveries map on the Overview

**Files:**
- Create: `frontend/components/DeliveriesMap.tsx`, `frontend/components/DeliveriesMapClient.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create DeliveriesMap (mirror `components/DeliveryMap.tsx` patterns)**

```tsx
// frontend/components/DeliveriesMap.tsx
"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { MapPoint } from "@/lib/types";

type LatLng = [number, number];

const STATUS_COLOR: Record<string, string> = {
  out_for_delivery: "#3b82f6",
  pending: "#f59e0b",
  failed: "#ef4444",
  rescheduled: "#94a3b8",
};

// Fixed SHIPA fulfilment hub (Al Quoz) — matches the seed origin.
const HUB: LatLng = [25.158, 55.236];

const LEGEND: [string, string][] = [
  ["Out for delivery", STATUS_COLOR.out_for_delivery],
  ["Pending", STATUS_COLOR.pending],
  ["Failed", STATUS_COLOR.failed],
  ["Rescheduled", STATUS_COLOR.rescheduled],
];

function pin(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:16px;height:16px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid #0b0d12;box-shadow:0 0 8px ${color}aa"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 16],
    popupAnchor: [0, -16],
  });
}

function hubIcon() {
  return L.divIcon({
    className: "",
    html: `<div style="background:#6366f1;width:22px;height:22px;border-radius:6px;border:2px solid white;box-shadow:0 0 10px #6366f1;display:flex;align-items:center;justify-content:center;color:white;font-size:13px;line-height:1">▦</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -12],
  });
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) map.fitBounds(points, { padding: [50, 50] });
  }, [map, points]);
  return null;
}

export type DeliveriesMapProps = { points: MapPoint[] };

export default function DeliveriesMap({ points }: DeliveriesMapProps) {
  const latlngs = points.map((p) => [p.delivery_lat, p.delivery_lng] as LatLng);
  const bounds: LatLng[] = [HUB, ...latlngs];
  return (
    <div className="relative">
      <MapContainer center={HUB} zoom={11} scrollWheelZoom={false}
        style={{ height: "460px", width: "100%", borderRadius: "0.75rem" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />
        {points.map((p) => (
          <Polyline key={`r-${p.order_id}`} positions={[HUB, [p.delivery_lat, p.delivery_lng]]}
            pathOptions={{ color: "#34d399", weight: 1, opacity: 0.22 }} />
        ))}
        {points.map((p) => (
          <Marker key={p.order_id} position={[p.delivery_lat, p.delivery_lng]}
            icon={pin(STATUS_COLOR[p.status] ?? "#94a3b8")}>
            <Popup>
              <strong>{p.twin_order_ref}</strong><br />
              {p.delivery_area ?? "—"}<br />
              Status: {p.status.replace(/_/g, " ")}<br />
              <a href={`/orders/${p.order_id}`}>Open order →</a>
            </Popup>
          </Marker>
        ))}
        <Marker position={HUB} icon={hubIcon()}>
          <Popup><strong>SHIPA hub</strong><br />Al Quoz fulfilment</Popup>
        </Marker>
        <FitBounds points={bounds} />
      </MapContainer>
      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-lg border border-white/10 bg-shipa-ink/80 px-3 py-2 text-[11px] text-white/80 shadow-lg">
        <div className="mb-1 font-mono uppercase tracking-wide text-white/50">Network health</div>
        {LEGEND.map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
```

> **Dark map style (per user):** the dashboard stays light, but the map uses CARTO `dark_matter` tiles (free, no API token), glowing status pins, a distinct hub marker, subtle hub→delivery route lines, and an on-map "Network Health" legend — echoing the reference screenshot. Fully functional; popups link to the order.

- [ ] **Step 2: Create the dynamic client wrapper (mirror `components/MapClient.tsx`)**

```tsx
// frontend/components/DeliveriesMapClient.tsx
"use client";

import dynamic from "next/dynamic";
import type { DeliveriesMapProps } from "@/components/DeliveriesMap";

const DeliveriesMap = dynamic(() => import("@/components/DeliveriesMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[420px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
      Loading map…
    </div>
  ),
});

export default function DeliveriesMapClient(props: DeliveriesMapProps) {
  return <DeliveriesMap {...props} />;
}
```

- [ ] **Step 3: Wire into the Overview**

In `frontend/app/page.tsx`: add `import DeliveriesMapClient from "@/components/DeliveriesMapClient";`, and insert a full-width section between the charts grid and the needs-attention/recent-calls grid:

```tsx
      <div className="rounded-xl border border-shipa-sky-accent bg-white p-3">
        <h2 className="mb-2 px-2 pt-1 text-sm font-semibold text-shipa-ink">
          Live deliveries ({insights.map_points.length})
        </h2>
        <DeliveriesMapClient points={insights.map_points} />
      </div>
```

- [ ] **Step 4: Match the order-detail map to the dark style**

In `frontend/components/DeliveryMap.tsx`, replace the existing `<TileLayer>` (the OpenStreetMap one) with the dark CARTO tiles for visual consistency:

```tsx
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
      />
```

- [ ] **Step 5: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: no errors; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/DeliveriesMap.tsx frontend/components/DeliveriesMapClient.tsx frontend/components/DeliveryMap.tsx frontend/app/page.tsx
git commit -m "feat(fe): dark-style live deliveries map + order-detail map"
```

---

## Task 9: Calls page — table + filter + side drawer

**Files:**
- Create: `frontend/components/CallsTable.tsx`, `frontend/app/calls/page.tsx`

- [ ] **Step 1: Create CallsTable (client component: filter + drawer)**

```tsx
// frontend/components/CallsTable.tsx
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import type { Call } from "@/lib/types";

export default function CallsTable({ calls }: { calls: Call[] }) {
  const [q, setQ] = useState("");
  const [intent, setIntent] = useState("");
  const [selected, setSelected] = useState<Call | null>(null);

  const intents = useMemo(
    () => Array.from(new Set(calls.map((c) => c.intent).filter(Boolean))) as string[],
    [calls],
  );

  const rows = calls.filter((c) => {
    const hay = `${c.customer_name ?? ""} ${c.twin_order_ref ?? ""} ${c.disposition ?? ""}`.toLowerCase();
    return (!q || hay.includes(q.toLowerCase())) && (!intent || c.intent === intent);
  });

  return (
    <div className="relative">
      <div className="mb-4 flex gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search customer / order / disposition"
          className="w-72 rounded-lg border border-shipa-sky-accent px-3 py-2 text-sm" />
        <select value={intent} onChange={(e) => setIntent(e.target.value)}
          className="rounded-lg border border-shipa-sky-accent px-3 py-2 text-sm">
          <option value="">All intents</option>
          {intents.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">When</th>
              <th className="px-4 py-3 font-semibold">Customer</th>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Intent</th>
              <th className="px-4 py-3 font-semibold">Disposition</th>
              <th className="px-4 py-3 font-semibold">Verified</th>
              <th className="px-4 py-3 font-semibold">CSAT</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.call_id} onClick={() => setSelected(c)}
                className="cursor-pointer border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3 text-shipa-ink/70">{new Date(c.started_at).toLocaleString()}</td>
                <td className="px-4 py-3">{c.customer_name ?? "—"}</td>
                <td className="px-4 py-3">{c.twin_order_ref ?? "—"}</td>
                <td className="px-4 py-3">{c.intent ?? "—"}</td>
                <td className="px-4 py-3">{c.disposition ?? "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={c.verification_status} /></td>
                <td className="px-4 py-3">{c.csat_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 z-20 flex justify-end bg-black/20" onClick={() => setSelected(null)}>
          <aside className="h-full w-96 overflow-y-auto bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-shipa-ink">Call detail</h2>
              <button onClick={() => setSelected(null)} className="text-shipa-ink/50 hover:text-shipa-ink">✕</button>
            </div>
            <dl className="divide-y divide-shipa-sky-accent text-sm">
              {([
                ["When", new Date(selected.started_at).toLocaleString()],
                ["Ended", selected.ended_at ? new Date(selected.ended_at).toLocaleString() : "—"],
                ["Direction", selected.direction],
                ["Language", selected.language ?? "—"],
                ["Verification", selected.verification_status],
                ["Intent", selected.intent ?? "—"],
                ["Disposition", selected.disposition ?? "—"],
                ["CSAT", selected.csat_score?.toString() ?? "—"],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2.5">
                  <dt className="text-shipa-ink/60">{k}</dt>
                  <dd className="text-right font-medium text-shipa-ink">{v}</dd>
                </div>
              ))}
            </dl>
            {selected.twin_order_ref && (
              <Link href={`/orders`} className="mt-4 inline-block text-sm text-shipa-blue hover:underline">
                Order {selected.twin_order_ref} →
              </Link>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create the page**

```tsx
// frontend/app/calls/page.tsx
import CallsTable from "@/components/CallsTable";
import { getCalls } from "@/lib/api";

export default async function CallsPage() {
  const calls = await getCalls();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Calls</h1>
      <CallsTable calls={calls} />
    </div>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/CallsTable.tsx frontend/app/calls/page.tsx
git commit -m "feat(fe): lean Calls page with filter + drawer"
```

---

## Task 10: Customer detail — call history + insights

**Files:**
- Modify: `frontend/app/customers/[id]/page.tsx`

- [ ] **Step 1: Replace `frontend/app/customers/[id]/page.tsx`**

(Adds an insight stat row + call-history table; keeps the existing orders table. Customer is bound to `c`.)

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

      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-shipa-sky-accent bg-white p-4">
          <div className="text-xs uppercase tracking-wide text-shipa-ink/50">Avg CSAT</div>
          <div className="mt-1 text-2xl font-bold text-shipa-ink">{c.avg_csat?.toFixed(1) ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-shipa-sky-accent bg-white p-4">
          <div className="text-xs uppercase tracking-wide text-shipa-ink/50">Last contact</div>
          <div className="mt-1 text-sm font-medium text-shipa-ink">
            {c.last_contact_at ? new Date(c.last_contact_at).toLocaleDateString() : "—"}
          </div>
        </div>
        <div className="rounded-xl border border-shipa-sky-accent bg-white p-4">
          <div className="text-xs uppercase tracking-wide text-shipa-ink/50">Status</div>
          <div className={`mt-1 text-sm font-semibold ${c.needs_follow_up ? "text-red-700" : "text-green-700"}`}>
            {c.needs_follow_up ? "Needs follow-up" : "Healthy"}
          </div>
        </div>
      </div>

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

      <h2 className="mb-3 mt-8 text-lg font-semibold text-shipa-ink">Call history</h2>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-2 font-semibold">When</th>
              <th className="px-4 py-2 font-semibold">Intent</th>
              <th className="px-4 py-2 font-semibold">Disposition</th>
              <th className="px-4 py-2 font-semibold">CSAT</th>
            </tr>
          </thead>
          <tbody>
            {c.calls.length === 0 && (
              <tr><td className="px-4 py-3 text-shipa-ink/50" colSpan={4}>No calls yet.</td></tr>
            )}
            {c.calls.map((call) => (
              <tr key={call.call_id} className="border-t border-shipa-sky-accent">
                <td className="px-4 py-2 text-shipa-ink/70">{new Date(call.started_at).toLocaleString()}</td>
                <td className="px-4 py-2">{call.intent ?? "—"}</td>
                <td className="px-4 py-2">{call.disposition ?? "—"}</td>
                <td className="px-4 py-2">{call.csat_score ?? "—"}</td>
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

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/customers/[id]/page.tsx
git commit -m "feat(fe): customer detail shows call history + csat + follow-up"
```

---

## Task 11: Orders — status filter + count summary

**Files:**
- Create: `frontend/components/OrdersTable.tsx`
- Modify: `frontend/app/orders/page.tsx`

- [ ] **Step 1: Create OrdersTable (client filter; reuses existing row markup)**

```tsx
// frontend/components/OrdersTable.tsx
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import type { OrderListItem } from "@/lib/types";

export default function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  const [status, setStatus] = useState("");
  const statuses = useMemo(() => Array.from(new Set(orders.map((o) => o.status))).sort(), [orders]);
  const rows = status ? orders.filter((o) => o.status === status) : orders;
  const failed = orders.filter((o) => o.status === "failed" || o.status === "returned").length;

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-shipa-sky-accent px-3 py-2 text-sm">
          <option value="">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
        <span className="text-sm text-shipa-ink/60">{orders.length} orders · {failed} failed/returned</span>
      </div>
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
            {rows.map((o) => (
              <tr key={o.order_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
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
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Slim down the page to use it**

Replace `frontend/app/orders/page.tsx`:

```tsx
import OrdersTable from "@/components/OrdersTable";
import { getOrders } from "@/lib/api";

export default async function OrdersPage() {
  const orders = await getOrders();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Orders</h1>
      <OrdersTable orders={orders} />
    </div>
  );
}
```

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/OrdersTable.tsx frontend/app/orders/page.tsx
git commit -m "feat(fe): orders status filter + count summary"
```

---

## Task 12: Full verification + deploy + seed production

**Files:** none (operational)

- [ ] **Step 1: Backend suite green**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 2: Frontend build green**

Run: `cd frontend && npm run build`
Expected: success, all routes compiled (`/`, `/orders`, `/calls`, `/customers`, `/customers/[id]`, `/orders/[id]`).

- [ ] **Step 3: Merge the feature branch to main (triggers Railway deploy of backend + frontend)**

```bash
git checkout main
git merge --no-ff feat/dashboard-insights -m "Merge feat/dashboard-insights: Overview, insights, lean Calls, customer call history"
git push origin main
```

- [ ] **Step 4: Wait for both services to redeploy, then seed production calls**

Run: `railway run --service Postgres -- uv run python db/seed_demo_calls.py`
Expected: prints `calls(D)=… open_escalations=… pending_reschedules=… open_investigations=…` with non-zero counts.

- [ ] **Step 5: Verify the live API (key injected, not printed)**

```bash
BE=https://shipadeliveryagent-production.up.railway.app
KEY=$(railway variables --service backend --kv 2>/dev/null | grep '^DASHBOARD_API_KEY=' | cut -d= -f2-)
curl -s -H "X-API-Key: $KEY" $BE/insights | python3 -c "import json,sys; d=json.load(sys.stdin); print('days',len(d['calls_per_day']),'intents',len(d['intent_mix']),'attention',d['needs_attention'],'map',len(d['map_points']))"
curl -s -H "X-API-Key: $KEY" $BE/calls | python3 -c "import json,sys; d=json.load(sys.stdin); print('calls',len(d),'sample_keys',sorted(d[0].keys()) if d else [])"
```
Expected: 14 days, several intents, non-zero attention counts, map points > 0; calls include `customer_name` + `twin_order_ref` and no `transcript`/`otp_code`.

- [ ] **Step 6: Verify the live dashboard**

Open `https://hopeful-learning-production-f4d4.up.railway.app/` — Overview shows KPIs, both charts, the deliveries map with colored pins, needs-attention counts, recent calls. Check `/calls` (filter + drawer) and a customer detail (call history + CSAT + follow-up flag).

---

## Notes
- **Read-only:** no dashboard mutations. Calls/operation rows come from the agent or the seed.
- **Safety:** transcript, recording_url, caller_number, and otp_code are never sent to the frontend. `CallSummary` exposes only ops-relevant fields.
- **No migration:** every table already exists; only response shapes and computed views change.
