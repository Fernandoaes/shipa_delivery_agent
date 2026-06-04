# Signal → Command Surface

**Date:** 2026-06-04
**Status:** Approved for planning

## Problem

The ops dashboard is read-only. Urgent signals (KPIs, work queue, charts) bottom out
in thin tables or dead numbers, and the one screen that should be the operator's
workbench — the order-detail page — shows only static fields (merchant, address,
driver). The "why" behind a problem (e.g. "customer not on site") lives scattered
across calls, escalations, investigations, and address flags and is never surfaced.

Three concrete gaps:

| # | Gap | Effect |
|---|-----|--------|
| A | At-Risk KPI isn't clickable | The most urgent number on the page goes nowhere |
| B | Escalation rows aren't links | Work queue → escalations → *stops*; can't reach the order/customer |
| C | Order detail is context-thin | Even when reached, no attempt count, no call disposition/notes, no linked escalation/reschedule |

## Goal

Make every urgent signal **one click** to an **enriched order-detail page** (the
"command surface") that shows the full story plus the customer, so a business
operator can understand and act without hunting. Drill target is the **order**, not a
customer-360 page.

There is no literal `failure_reason` column. "Customer not on site" is inferable from
`call.disposition` / `call.notes` / `escalation.reason` / `attempt_count`. "Full info"
therefore means **aggregating related operational records onto the order**, not
inventing a new field.

## Non-Goals

- Customer-360 page (deferred; order detail links to the existing `/customers/[id]`).
- Map-point drill enrichment (rides the same enriched detail page for free, but no new
  map work this iteration).
- Any write/action capability (escalation resolution, reschedule sync) — read/triage
  only this pass.

## Architecture

All enrichment rides **existing endpoints** — no new routes. Backend widens response
schemas and the service-layer aggregation; frontend mirrors types and rewires
navigation + the detail page.

### Backend (3 files)

**1. Expose escalation → order link**
- `schemas/dashboard.py` — `EscalationSummary` gains `order_id: uuid.UUID | None` and
  `twin_order_ref: str | None = None`.
- `routers/dashboard.py` — `list_escalations` joins `Order.twin_order_ref` for the
  rows' `order_id`s, mirroring the existing `list_investigations` pattern (build an
  `order_id → twin_order_ref` dict, then construct summaries explicitly).

**2. Enrich `OrderDetail` (the command surface)**
- `schemas/dashboard.py` — `OrderDetail` gains:
  - `attempt_count: int`
  - `delivered_at: dt.datetime | None`
  - `sla_due_at: dt.datetime | None`
  - `calls: list[CallSummary]`
  - `escalations: list[EscalationSummary]`
  - `investigations: list[InvestigationSummary]`
  - `reschedules: list[RescheduleSummary]`
  - `address_flags: list[AddressFlagSummary]`
- `services/orders.py` — `get_order_detail` gathers the related records filtered by
  `order_id`. Each related list is newest-first (`created_at`/`started_at`/`opened_at`
  desc). `CallSummary` is built from the order's calls (its `customer_name` /
  `twin_order_ref` fields are already optional). `address_flags` populates each
  summary's existing fields.

**3. At-Risk reason hint on the list**
- `schemas/dashboard.py` — `OrderListItem` gains `attempt_count: int` and
  `issue: str | None = None`.
- `services/orders.py` — `list_orders` computes `issue` with **two batched dict
  queries** (no N+1):
  - open `Escalation` rows → `{order_id: reason or category}`
  - `AddressFlag` rows → `{order_id: correction_text}`

  Derivation priority per order: open-escalation reason/category → address-flag
  correction → `"Attempt N"` when `attempt_count > 1` → `None`. (Latest-call
  disposition is intentionally dropped from the hint to keep `list_orders` to two
  extra queries; the full call history still shows on the detail page.)

### Frontend (6 files)

| File | Change |
|------|--------|
| `components/KpiStat.tsx` | Add optional `href` prop; when present, the card renders inside a `next/link` `Link` with a hover affordance |
| `app/page.tsx` | At-Risk `KpiStat` gets `href="/orders?risk=1"` |
| `components/OrdersTable.tsx` | Read `risk` param via existing `useTableFilters`; when `risk=1`, pre-filter rows to `status ∈ {failed, returned}` and show an "At-risk orders" heading with count. Add an **Issue** column (always rendered, `—` when empty) and an attempt badge when `attempt_count > 1` |
| `components/EscalationsTable.tsx` | Add an **Order** column; when `order_id` is present the row links to `/orders/{order_id}` (rows without an order stay unlinked). Reuse the `OrdersTable` link style (`text-shipa-blue hover:underline`) |
| `app/orders/[id]/page.tsx` | Restructure into the command surface: header (ref + status badge + attempt count + SLA), the existing facts `dl` with the customer name now linking to `/customers/{customer_id}`, the map, and **conditional activity sections** rendered only when non-empty: Escalations, Reschedules, Address flags, Investigations, Recent calls (disposition / intent / notes / csat / time) |
| `lib/types.ts` | Mirror backend additions: `EscalationSummary` (+`order_id`, `twin_order_ref`), `OrderListItem` (+`attempt_count`, `issue`), `OrderDetail` (+attempt/sla/delivered + related arrays), and a new `AddressFlagSummary` type |

`lib/api.ts` is unchanged — all enrichment rides `getOrder`, `getOrders`,
`getEscalations`.

## Data Flow

Next.js server components fetch through `lib/api.ts`. No new fetch functions: the
widened JSON flows through the existing `getOrder` / `getOrders` / `getEscalations`
calls into the updated TypeScript types and the rewired components.

## Drill Paths Unlocked

- **Work queue → Open escalations → click row → order detail** (escalation reason +
  call notes present on arrival)
- **At-Risk KPI → failed/returned orders, each with its `issue` inline → click → full
  story**
- Order list / map points → same enriched surface

## Error Handling

- `EscalationSummary.order_id` is nullable; FE renders unlinked rows and a `—` Order
  cell when absent.
- Activity sections on the detail page render only when their list is non-empty, so a
  clean order shows just facts + map (no empty shells).
- `issue` is nullable; the Issue column shows `—`.
- Existing `get_order_detail` 404 behaviour (router raises `HTTPException(404)`) is
  unchanged.

## Testing

- **Backend (pytest, service/route level):**
  - `get_order_detail` aggregates the related records for an order that has an
    escalation + reschedule + call; a clean order returns empty lists.
  - `list_orders` `issue` derivation follows the documented priority.
  - `/escalations` response exposes `order_id` + `twin_order_ref`.
  - The known httpx/TestClient harness failure is pre-existing and out of scope; assert
    against services directly where the TestClient is implicated.
- **Frontend (vitest):** add/adjust component tests where they already exist for these
  components; flag explicitly if coverage is thin rather than claiming it.

## Files Touched

Backend: `app/schemas/dashboard.py`, `app/services/orders.py`, `app/routers/dashboard.py`
Frontend: `frontend/lib/types.ts`, `frontend/components/KpiStat.tsx`,
`frontend/app/page.tsx`, `frontend/components/OrdersTable.tsx`,
`frontend/components/EscalationsTable.tsx`, `frontend/app/orders/[id]/page.tsx`
