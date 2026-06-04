# Signal → Command Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every urgent dashboard signal one click to an enriched order-detail "command surface" that aggregates the operational why.

**Architecture:** All enrichment rides existing endpoints — backend widens response schemas + service aggregation; frontend mirrors types and rewires navigation + the detail page. Backend is TDD (pytest service/route level). Frontend changes are JSX wiring verified by typecheck/build + manual smoke (component-test infra is thin — only `frontend/lib/insights.test.ts` exists).

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic v2 (Postgres), Next.js (server components) + Tailwind, pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-06-04-signal-to-command-surface-design.md`

---

## Task 1: Expose escalation → order link (backend)

**Files:**
- Modify: `app/schemas/dashboard.py` (`EscalationSummary`, ~line 47)
- Modify: `app/routers/dashboard.py` (`list_escalations`, ~line 51)
- Test: `tests/test_dashboard_lookups.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_dashboard_lookups.py` (the file already imports `dt`, `Call`, `Order`, `EscalationSummary`, `MockTwinClient`, `upsert_orders`; add `Escalation` to the `app.models` import and `list_escalations` to the `app.routers.dashboard` import):

```python
def test_escalation_summary_exposes_order_link():
    assert "order_id" in EscalationSummary.model_fields
    assert "twin_order_ref" in EscalationSummary.model_fields


def test_list_escalations_resolves_twin_ref(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add(call)
    db.flush()
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="refund",
                      reason="late", status="open", created_at=dt.datetime.now()))
    db.flush()
    rows = list_escalations(db)
    assert rows[0].order_id == order.order_id
    assert rows[0].twin_order_ref == "TWIN-1001"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard_lookups.py -v`
Expected: `test_escalation_summary_exposes_order_link` FAILS (field missing); `test_list_escalations_resolves_twin_ref` FAILS (TypeError on `.order_id` / construction).

- [ ] **Step 3: Widen the schema**

In `app/schemas/dashboard.py`, replace the `EscalationSummary` class body with:

```python
class EscalationSummary(BaseModel):
    escalation_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID | None = None
    twin_order_ref: str | None = None
    category: str
    reason: str | None = None
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Join twin refs in the router**

In `app/routers/dashboard.py`, replace `list_escalations` with:

```python
@router.get("/escalations", response_model=list[EscalationSummary])
def list_escalations(db: Session = Depends(get_db)):
    rows = db.query(Escalation).order_by(Escalation.created_at.desc()).all()
    order_ids = {r.order_id for r in rows if r.order_id is not None}
    refs = (
        dict(db.query(Order.order_id, Order.twin_order_ref).filter(Order.order_id.in_(order_ids)).all())
        if order_ids else {}
    )
    return [
        EscalationSummary(
            escalation_id=r.escalation_id, call_id=r.call_id, order_id=r.order_id,
            twin_order_ref=refs.get(r.order_id), category=r.category, reason=r.reason,
            status=r.status, created_at=r.created_at,
        )
        for r in rows
    ]
```

(`Escalation` and `Order` are already imported at the top of this router.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_dashboard_lookups.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/routers/dashboard.py tests/test_dashboard_lookups.py
git commit -m "feat(api): expose order link on escalation summaries"
```

---

## Task 2: Enrich OrderDetail with operational context (backend)

**Files:**
- Modify: `app/schemas/dashboard.py` (`OrderDetail`, ~line 120; import line ~line 4)
- Modify: `app/services/orders.py` (`get_order_detail`, ~line 55; imports ~line 5)
- Test: `tests/test_orders_service.py`

- [ ] **Step 1: Write the failing tests**

At the top of `tests/test_orders_service.py` add imports:

```python
import datetime as dt

from app.models import Call, Escalation, Reschedule
```

Append these tests:

```python
def test_get_order_detail_aggregates_related_records(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = next(o for o in orders if o.twin_order_ref == "TWIN-1001")
    # each operation table has a UNIQUE call_id, so make a distinct call per record
    c1 = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
              order_id=order.order_id, customer_id=order.customer_id, disposition="not_on_site",
              started_at=dt.datetime.now())
    c2 = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
              order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add_all([c1, c2])
    db.flush()
    db.add(Escalation(call_id=c1.call_id, order_id=order.order_id, category="refund",
                      reason="late", status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=c2.call_id, order_id=order.order_id,
                      requested_date=dt.date.today(), status="requested", created_at=dt.datetime.now()))
    db.flush()
    detail = get_order_detail(db, order.order_id)
    assert detail.attempt_count == order.attempt_count
    assert len(detail.calls) == 2
    assert len(detail.escalations) == 1
    assert detail.escalations[0].reason == "late"
    assert len(detail.reschedules) == 1


def test_get_order_detail_clean_order_has_empty_related(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    detail = get_order_detail(db, orders[0].order_id)
    assert detail.calls == []
    assert detail.escalations == []
    assert detail.reschedules == []
    assert detail.address_flags == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orders_service.py -v`
Expected: new tests FAIL (`OrderDetail` has no `calls`/`escalations`/`attempt_count`).

- [ ] **Step 3: Widen the schema**

In `app/schemas/dashboard.py`, change the import line to include `Field`:

```python
from pydantic import BaseModel, Field
```

Replace the `OrderDetail` class with:

```python
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
    attempt_count: int
    delivered_at: dt.datetime | None
    sla_due_at: dt.datetime | None
    merchant_lat: float | None
    merchant_lng: float | None
    delivery_lat: float | None
    delivery_lng: float | None
    last_synced_at: dt.datetime
    customer: CustomerBrief
    calls: list[CallSummary] = Field(default_factory=list)
    escalations: list[EscalationSummary] = Field(default_factory=list)
    investigations: list[InvestigationSummary] = Field(default_factory=list)
    reschedules: list[RescheduleSummary] = Field(default_factory=list)
    address_flags: list[AddressFlagSummary] = Field(default_factory=list)
    # deliberately no otp_code
```

(All five summary classes are already defined earlier in this same module.)

- [ ] **Step 4: Aggregate in the service**

In `app/services/orders.py`, replace the import on line 5 with:

```python
from app.models import AddressFlag, Call, Escalation, Investigation, Order, Reschedule
from app.schemas.dashboard import (
    AddressFlagSummary, CallSummary, CustomerBrief, EscalationSummary, InvestigationSummary,
    OrderDetail, OrderListItem, RescheduleSummary,
)
```

(Remove the old `from app.schemas.dashboard import CustomerBrief, OrderDetail, OrderListItem` line — it is replaced by the block above. Keep the existing `from app.schemas.twin import TwinOrderRead`.)

Replace `get_order_detail` with:

```python
def get_order_detail(db: Session, order_id: uuid.UUID) -> OrderDetail | None:
    o = db.get(Order, order_id)
    if o is None:
        return None
    calls = (
        db.query(Call).filter(Call.order_id == order_id).order_by(Call.started_at.desc()).all()
    )
    escalations = (
        db.query(Escalation).filter(Escalation.order_id == order_id)
        .order_by(Escalation.created_at.desc()).all()
    )
    investigations = (
        db.query(Investigation).filter(Investigation.order_id == order_id)
        .order_by(Investigation.opened_at.desc()).all()
    )
    reschedules = (
        db.query(Reschedule).filter(Reschedule.order_id == order_id)
        .order_by(Reschedule.created_at.desc()).all()
    )
    address_flags = (
        db.query(AddressFlag).filter(AddressFlag.order_id == order_id)
        .order_by(AddressFlag.created_at.desc()).all()
    )
    return OrderDetail(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_address=o.delivery_address, delivery_area=o.delivery_area,
        delivery_window=o.delivery_window, assigned_driver=o.assigned_driver,
        expected_pieces=o.expected_pieces, attempt_count=o.attempt_count,
        delivered_at=o.delivered_at, sla_due_at=o.sla_due_at,
        merchant_lat=o.merchant_lat, merchant_lng=o.merchant_lng,
        delivery_lat=o.delivery_lat, delivery_lng=o.delivery_lng,
        last_synced_at=o.last_synced_at,
        customer=CustomerBrief.model_validate(o.customer),
        calls=[CallSummary.model_validate(c) for c in calls],
        escalations=[EscalationSummary.model_validate(e) for e in escalations],
        investigations=[InvestigationSummary.model_validate(i) for i in investigations],
        reschedules=[RescheduleSummary.model_validate(r) for r in reschedules],
        address_flags=[AddressFlagSummary.model_validate(f) for f in address_flags],
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_orders_service.py -v`
Expected: PASS (including the pre-existing `test_get_order_detail_has_coords_and_customer`).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/services/orders.py tests/test_orders_service.py
git commit -m "feat(api): aggregate related ops records onto order detail"
```

---

## Task 3: At-risk reason hint on the order list (backend)

**Files:**
- Modify: `app/schemas/dashboard.py` (`OrderListItem`, ~line 109)
- Modify: `app/services/orders.py` (`_order_list_item` + `list_orders`)
- Test: `tests/test_orders_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_orders_service.py` (imports from Task 2 already cover `Call`, `Escalation`, `dt`):

```python
def test_list_orders_issue_from_open_escalation(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = next(o for o in orders if o.twin_order_ref == "TWIN-1001")
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add(call)
    db.flush()
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="refund",
                      reason="parcel damaged", status="open", created_at=dt.datetime.now()))
    db.flush()
    item = next(i for i in list_orders(db) if i.twin_order_ref == "TWIN-1001")
    assert item.issue == "parcel damaged"
    assert item.attempt_count == order.attempt_count


def test_list_orders_issue_none_when_clean(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    items = list_orders(db)
    assert all(i.issue is None for i in items if i.attempt_count == 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orders_service.py -v`
Expected: new tests FAIL (`OrderListItem` has no `issue`).

- [ ] **Step 3: Widen the schema**

In `app/schemas/dashboard.py`, replace the `OrderListItem` class with:

```python
class OrderListItem(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    customer_name: str
    attempt_count: int = 1
    issue: str | None = None
```

(The new fields have defaults, so other constructors — e.g. `CustomerDetail.orders` in `app/services/customers.py` — keep working unchanged.)

- [ ] **Step 4: Derive the hint in the service**

In `app/services/orders.py`, replace `_order_list_item` and `list_orders` with:

```python
def _derive_issue(o: Order, esc_by_order: dict, flag_by_order: dict) -> str | None:
    if o.order_id in esc_by_order:
        return esc_by_order[o.order_id]
    if o.order_id in flag_by_order:
        return f"Address: {flag_by_order[o.order_id]}"
    if o.attempt_count > 1:
        return f"Attempt {o.attempt_count}"
    return None


def _order_list_item(o: Order, esc_by_order: dict | None = None, flag_by_order: dict | None = None) -> OrderListItem:
    esc_by_order = esc_by_order or {}
    flag_by_order = flag_by_order or {}
    return OrderListItem(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_area=o.delivery_area, delivery_window=o.delivery_window,
        assigned_driver=o.assigned_driver, customer_name=o.customer.full_name,
        attempt_count=o.attempt_count, issue=_derive_issue(o, esc_by_order, flag_by_order),
    )


def list_orders(db: Session) -> list[OrderListItem]:
    orders = db.query(Order).order_by(Order.twin_order_ref).all()
    esc_by_order = {
        oid: (reason or category)
        for oid, reason, category in db.query(
            Escalation.order_id, Escalation.reason, Escalation.category
        ).filter(Escalation.status == "open", Escalation.order_id.isnot(None)).all()
    }
    flag_by_order = dict(
        db.query(AddressFlag.order_id, AddressFlag.correction_text)
        .filter(AddressFlag.status == "pending").all()
    )
    return [_order_list_item(o, esc_by_order, flag_by_order) for o in orders]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_orders_service.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/services/orders.py tests/test_orders_service.py
git commit -m "feat(api): derive at-risk issue hint on order list"
```

---

## Task 4: Mirror backend types (frontend)

**Files:**
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Add `AddressFlagSummary` and widen existing types**

In `frontend/lib/types.ts`:

Add a new type (place near the other summaries):

```typescript
export type AddressFlagSummary = {
  flag_id: string;
  call_id: string;
  order_id: string;
  original_address: string;
  correction_text: string;
  status: string;
  created_at: string;
};
```

Replace `EscalationSummary` with:

```typescript
export type EscalationSummary = {
  escalation_id: string;
  call_id: string;
  order_id: string | null;
  twin_order_ref: string | null;
  category: string;
  reason: string | null;
  status: string;
  created_at: string;
};
```

Replace `OrderListItem` with:

```typescript
export type OrderListItem = {
  order_id: string;
  twin_order_ref: string;
  merchant: string;
  status: string;
  delivery_area: string | null;
  delivery_window: string | null;
  assigned_driver: string | null;
  customer_name: string;
  attempt_count: number;
  issue: string | null;
};
```

Replace `OrderDetail` with:

```typescript
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
  attempt_count: number;
  delivered_at: string | null;
  sla_due_at: string | null;
  merchant_lat: number | null;
  merchant_lng: number | null;
  delivery_lat: number | null;
  delivery_lng: number | null;
  last_synced_at: string;
  customer: CustomerBrief;
  calls: CallSummary[];
  escalations: EscalationSummary[];
  investigations: InvestigationSummary[];
  reschedules: RescheduleSummary[];
  address_flags: AddressFlagSummary[];
};
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no usages broke; new fields are additive). Existing consumers compile.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(fe): mirror enriched order/escalation API types"
```

---

## Task 5: Make the At-Risk KPI clickable (frontend)

**Files:**
- Modify: `frontend/components/KpiStat.tsx`
- Modify: `frontend/app/page.tsx` (At-Risk `KpiStat`, ~line 73)

- [ ] **Step 1: Add an optional `href` to `KpiStat`**

Replace `frontend/components/KpiStat.tsx` with:

```tsx
import Link from "next/link";
import type { ComponentType } from "react";

type Tone = "neutral" | "ok" | "warn" | "bad";

const TONE: Record<Tone, string> = {
  neutral: "text-txt",
  ok: "text-ok",
  warn: "text-warn",
  bad: "text-bad",
};
const ICON_TONE: Record<Tone, string> = {
  neutral: "bg-panel-2 text-txt-dim",
  ok: "bg-ok/10 text-ok",
  warn: "bg-warn/10 text-warn",
  bad: "bg-bad/10 text-bad",
};

export default function KpiStat({
  label, value, sub, tone = "neutral", Icon, href,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  Icon: ComponentType<{ size?: number; className?: string }>;
  href?: string;
}) {
  const inner = (
    <>
      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-txt-faint">{label}</div>
        <div className={`mt-2 text-3xl font-semibold ${TONE[tone]}`}>{value}</div>
        {sub && <div className="mt-1 text-xs text-txt-dim">{sub}</div>}
      </div>
      <span className={`grid h-9 w-9 place-items-center rounded-lg ${ICON_TONE[tone]}`}>
        <Icon size={18} />
      </span>
    </>
  );
  const base = "flex items-start justify-between rounded-2xl border border-hairline bg-panel p-5";
  if (href) {
    return (
      <Link href={href} className={`${base} transition-colors hover:border-shipa-blue hover:bg-panel-2`}>
        {inner}
      </Link>
    );
  }
  return <div className={base}>{inner}</div>;
}
```

- [ ] **Step 2: Point the At-Risk KPI at the at-risk view**

In `frontend/app/page.tsx`, replace the At-Risk `KpiStat` (line ~73) with:

```tsx
        <KpiStat label="At-Risk" value={metrics.at_risk.toString()} sub="failed / returned" tone={metrics.at_risk > 0 ? "bad" : "ok"} Icon={TriangleAlert} href="/orders?risk=1" />
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/KpiStat.tsx frontend/app/page.tsx
git commit -m "feat(fe): make at-risk KPI a one-click drill into failed orders"
```

---

## Task 6: At-risk filter + issue column on the orders table (frontend)

**Files:**
- Modify: `frontend/components/OrdersTable.tsx`

- [ ] **Step 1: Add the `risk` predicate, heading, and Issue column**

Replace `frontend/components/OrdersTable.tsx` with:

```tsx
"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { OrderListItem } from "@/lib/types";

const AT_RISK = new Set(["failed", "returned"]);

export default function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  const { get, set } = useTableFilters();
  const riskOnly = get("risk") === "1";
  const rows = useMemo(
    () =>
      applyFilters(orders, {
        query: get("q"),
        textFields: ["twin_order_ref", "customer_name", "merchant"],
        equals: { status: get("status"), delivery_area: get("area"), merchant: get("merchant"), assigned_driver: get("driver") },
        predicate: riskOnly ? (o) => AT_RISK.has(o.status) : undefined,
      }),
    [orders, get, riskOnly],
  );

  return (
    <div>
      {riskOnly && (
        <div className="mb-4 flex items-center gap-3">
          <h2 className="text-lg font-semibold text-bad">At-risk orders</h2>
          <span className="font-mono text-sm text-txt-dim">{rows.length} failed / returned</span>
          <button onClick={() => set("risk", "")} className="text-xs text-shipa-blue hover:underline">
            clear
          </button>
        </div>
      )}
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
              <th className="px-4 py-3 font-semibold">Issue</th>
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
                <td className="px-4 py-3">
                  {o.issue ? (
                    <span className="text-[#ff8585]">{o.issue}</span>
                  ) : o.attempt_count > 1 ? (
                    <span className="text-warn">Attempt {o.attempt_count}</span>
                  ) : (
                    <span className="text-txt-faint">—</span>
                  )}
                </td>
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

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OrdersTable.tsx
git commit -m "feat(fe): at-risk filter and inline issue column on orders table"
```

---

## Task 7: Make escalation rows link to the order (frontend)

**Files:**
- Modify: `frontend/components/EscalationsTable.tsx`

- [ ] **Step 1: Add an Order column with a link**

Replace `frontend/components/EscalationsTable.tsx` with:

```tsx
"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
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
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Reason</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.escalation_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  {r.order_id ? (
                    <Link href={`/orders/${r.order_id}`} className="font-medium text-shipa-blue hover:underline">
                      {r.twin_order_ref ?? "view order"}
                    </Link>
                  ) : (
                    <span className="text-txt-faint">—</span>
                  )}
                </td>
                <td className="px-4 py-3">{r.category}</td>
                <td className="px-4 py-3">{r.reason ?? "—"}</td>
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

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/EscalationsTable.tsx
git commit -m "feat(fe): link escalation rows to their order"
```

---

## Task 8: Rebuild the order detail as the command surface (frontend)

**Files:**
- Modify: `frontend/app/orders/[id]/page.tsx`

- [ ] **Step 1: Restructure the detail page with activity sections**

Replace `frontend/app/orders/[id]/page.tsx` with:

```tsx
import Link from "next/link";
import type { ReactNode } from "react";
import BackButton from "@/components/BackButton";
import MapClient from "@/components/MapClient";
import StatusBadge from "@/components/StatusBadge";
import { getOrder } from "@/lib/api";

type LatLng = [number, number];

function pair(lat: number | null, lng: number | null): LatLng | null {
  return lat != null && lng != null ? [lat, lng] : null;
}

function fmt(ts: string | null): string {
  return ts ? new Date(ts).toLocaleString() : "—";
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-hairline bg-panel p-5">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-txt-faint">{title}</h2>
      {children}
    </div>
  );
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
    ["Attempts", o.attempt_count.toString()],
    ["SLA due", fmt(o.sla_due_at)],
    ["Delivered", fmt(o.delivered_at)],
  ];
  return (
    <div className="px-8 py-8">
      <BackButton href="/orders" label="Orders" />
      <div className="mb-6 mt-3 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-txt">{o.twin_order_ref}</h1>
        <StatusBadge status={o.status} />
        {o.attempt_count > 1 && (
          <span className="rounded-full bg-warn/15 px-2.5 py-0.5 text-xs font-medium text-warn">
            attempt {o.attempt_count}
          </span>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-hairline bg-panel p-5">
          <dl className="divide-y divide-hairline">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
                <dt className="text-txt-dim">{k}</dt>
                <dd className="text-right font-medium text-txt">{v}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-4 py-2.5 text-sm">
              <dt className="text-txt-dim">Customer</dt>
              <dd className="text-right font-medium">
                <Link href={`/customers/${o.customer.customer_id}`} className="text-shipa-blue hover:underline">
                  {o.customer.full_name}
                </Link>
                <span className="text-txt-dim"> · {o.customer.primary_phone}</span>
              </dd>
            </div>
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

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {o.escalations.length > 0 && (
          <Section title="Escalations">
            <ul className="space-y-2 text-sm">
              {o.escalations.map((e) => (
                <li key={e.escalation_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{e.category}{e.reason ? ` — ${e.reason}` : ""}</span>
                  <StatusBadge status={e.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.reschedules.length > 0 && (
          <Section title="Reschedules">
            <ul className="space-y-2 text-sm">
              {o.reschedules.map((r) => (
                <li key={r.reschedule_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">requested {r.requested_date}</span>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.address_flags.length > 0 && (
          <Section title="Address flags">
            <ul className="space-y-2 text-sm">
              {o.address_flags.map((f) => (
                <li key={f.flag_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{f.correction_text}</span>
                  <StatusBadge status={f.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.investigations.length > 0 && (
          <Section title="Investigations">
            <ul className="space-y-2 text-sm">
              {o.investigations.map((i) => (
                <li key={i.investigation_id} className="flex items-start justify-between gap-3">
                  <span className="text-txt">{i.type}</span>
                  <StatusBadge status={i.status} />
                </li>
              ))}
            </ul>
          </Section>
        )}

        {o.calls.length > 0 && (
          <Section title="Recent calls">
            <ul className="space-y-3 text-sm">
              {o.calls.map((c) => (
                <li key={c.call_id} className="border-b border-hairline pb-2 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-txt">{c.intent ?? c.direction}{c.disposition ? ` · ${c.disposition}` : ""}</span>
                    <span className="font-mono text-xs text-txt-faint">{fmt(c.started_at)}</span>
                  </div>
                  {c.csat_score != null && <div className="mt-1 text-xs text-txt-dim">CSAT {c.csat_score}</div>}
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/orders/[id]/page.tsx
git commit -m "feat(fe): order detail as operator command surface"
```

---

## Task 9: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole backend suite**

Run: `pytest tests/ -q`
Expected: all PASS except the single pre-existing httpx/TestClient failure documented in project memory (`command-center-frontend`). Confirm no *new* failures vs. baseline.

- [ ] **Step 2: Frontend lint + production build**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint clean; build succeeds (catches server/client boundary + Suspense issues that `tsc` misses).

- [ ] **Step 3: Manual smoke (use the `run` skill or `npm run dev` + the backend)**

Verify the three drill paths against seeded data:
1. Dashboard At-Risk KPI → click → `/orders?risk=1` shows only failed/returned with the Issue column populated.
2. Work queue → Open escalations → an escalation row with an order links to `/orders/{id}`.
3. Order detail shows attempts/SLA, a clickable customer, and activity sections only when records exist (clean order shows just facts + map).

Expected: all three paths work; no console errors.

- [ ] **Step 4: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "chore: verification fixups for command-surface drill-downs"
```
```
(Skip if Steps 1–2 passed with no changes.)
```
