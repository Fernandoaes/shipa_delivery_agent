# SHIPA Ops Dashboard — Insights & Calls (Design)

Date: 2026-06-03
Status: Approved (pending spec review)

## Goal

Turn the read-only ops dashboard from "Orders + Customers tables" into an
insightful, customer-oriented operations view that surfaces the call data the
inbound AI agent produces. Simplicity first, fully functional, no
over-engineering. The dashboard remains **read-only**; calls and operation rows
are written elsewhere (the agent / manual updates), not from the UI.

## Constraints & principles

- **Lean calls:** no transcript, no recording, no caller number in the UI. Only
  the existing safe `CallSummary` fields plus safe relational context
  (customer name, order ref). `otp_code` stays excluded everywhere (already is).
- **No new frontend dependencies.** Charts are dependency-free inline CSS/SVG.
- **Reuse the existing design system** (`shipa-*` tokens, `TopBar`,
  `StatusBadge`) and the existing backend pattern (thin router → service →
  Pydantic schema, `from_attributes`).
- **Read-only**, no auth, no real-time, no pagination, no exports.

## Architecture

Chosen approach: **one server-side aggregation endpoint** (`GET /insights`) plus
small safe extensions to existing schemas. Keeps the frontend dumb and the
aggregation logic unit-testable. Server components fetch in parallel
(`Promise.all`).

## Navigation

`TopBar`: **Overview · Orders · Customers · Calls** (Overview is the new home).

## Pages

### Overview (`app/page.tsx` — replaces `redirect("/orders")`)
Single server component, parallel fetch of `/metrics`, `/insights`, `/calls`.
- **KPI row** from `/metrics`: Total calls · First-attempt % · Deflection % ·
  Avg CSAT · Avg handle time.
- **Two charts** (inline CSS/SVG components): *Calls per day* (last 14 days,
  bars) and *Intent mix* (horizontal bars).
- **Live deliveries map** (Dubai-wide, full-width): pins for active deliveries
  from `/insights.map_points`, colored by status (out_for_delivery, pending,
  failed, rescheduled). Reuses react-leaflet; pins link to the order detail.
- **Needs attention** panel from `/insights.needs_attention`: open escalations ·
  pending reschedules · failed/at-risk orders. Each is a count linking to the
  relevant filtered list.
- **Recent calls**: latest 10 from `/calls` — time · customer · intent ·
  disposition · CSAT, linking to the customer.

### Calls (`app/calls/page.tsx` — new, lean)
- Table from `/calls`: started_at · direction · language · verification_status ·
  intent · disposition · CSAT · customer_name · twin_order_ref.
- Client-side filter: free-text search + intent and disposition dropdowns. No
  pagination.
- Row click opens a **side drawer** showing the `CallSummary` metadata and links
  to the linked order and customer. No transcript/recording/caller number.

### Customers (enhancement — customer-oriented)
- Customer **detail** (`app/customers/[id]/page.tsx`) gains, alongside existing
  orders: **call history** (lean `CallSummary` rows), **avg CSAT**, **last
  contact** date, and a small "needs follow-up" flag when avg CSAT is low
  (< 3.0) or the customer has a failed order.
- Customer **list** unchanged except it already shows order_count.

### Orders (light touch)
- Add a client-side **status filter** and a count summary header
  (e.g. `120 orders · 18 failed · 22 out for delivery`). Detail page + map
  unchanged.

## Backend changes (`app/`)

### `schemas/dashboard.py`
- `Metrics` stays as the 5 KPIs (unchanged). Attention counts live only in
  `Insights.needs_attention` to avoid duplication.
- Extend `CallSummary`: `customer_name: str | None`, `twin_order_ref: str | None`
  (derived via join; both safe, non-PII).
- New `Insights`:
  ```
  calls_per_day: list[{ date: date, count: int }]      # last 14 days, zero-filled
  intent_mix: list[{ intent: str, count: int }]
  disposition_mix: list[{ disposition: str, count: int }]
  needs_attention: { open_escalations: int, pending_reschedules: int, failed_orders: int }
  map_points: list[{ order_id, twin_order_ref, status, delivery_area,
                     delivery_lat: float, delivery_lng: float }]   # active orders w/ coords
  ```
- Extend `CustomerDetail`: `calls: list[CallSummary]`, `avg_csat: float | None`,
  `last_contact_at: datetime | None`.

### `services/`
- `calls.py` (new or fold into dashboard service): `list_calls` joins
  `orders`/`customers` to populate `customer_name` + `twin_order_ref`.
- `insights.py` (new): `compute_insights(db)` → the `Insights` payload.
  - `calls_per_day`: group calls by `started_at::date`, last 14 days,
    zero-filled so the chart has continuous days.
  - `intent_mix` / `disposition_mix`: counts grouped by field, NULLs labeled
    "unknown", sorted desc.
  - `needs_attention`: `open_escalations` = escalations where status='open';
    `pending_reschedules` = reschedules where `synced_to_twin_at IS NULL`;
    `failed_orders` = orders where status in ('failed','returned').
  - `map_points`: orders with non-null delivery_lat/lng and status in
    ('out_for_delivery','pending','failed','rescheduled').
- `customers.py`: `get_customer_detail` also loads the customer's calls
  (newest first), computes `avg_csat` (over non-null csat) and
  `last_contact_at` (max started_at).

### `routers/dashboard.py`
- Add `GET /insights` → `compute_insights(db)`.

## Frontend (`frontend/`)
- `lib/types.ts`: add `Call`, `Insights`, `NeedsAttention`; extend
  `CustomerDetail`; add `Metrics` type.
- `lib/api.ts`: add `getMetrics()`, `getInsights()`, `getCalls()`.
- Components (new): `KpiCard`, `BarChart` (CSS/SVG), `DeliveriesMap`
  (react-leaflet, client component, dynamic import `ssr:false` like the existing
  order-detail map), `NeedsAttention`, `RecentCalls`, `CallsTable`,
  `CallDrawer`. Reuse `StatusBadge`.
- `TopBar`: add Overview + Calls links.

## Mock data
- New seed adds **calls** linked to the existing `*-D*` customers/orders:
  realistic spread over the last 14 days; intents (e.g. delivery_status,
  reschedule, address_change, complaint, otp_help); dispositions (resolved,
  rescheduled, escalated, info_provided); csat 1–5; verification mix; mostly
  inbound; handle times 30s–6m. Plus a handful of **escalations**,
  **reschedules**, and **investigations** so "needs attention" is non-empty.
- Idempotent (dedicated `happyrobot_call_id` ref namespace + ON CONFLICT).
  Run via `railway run --service Postgres -- uv run python db/<seed>.py`.

## Testing
- pytest (TDD): `compute_insights` aggregations (calls_per_day zero-fill, mixes,
  needs_attention thresholds), extended `list_calls` join, extended
  `get_customer_detail` (avg_csat, last_contact). Use the existing test setup.
- Frontend: `next build` type-check; verify on the live deployment.

## Out of scope (YAGNI)
Transcript/recording UI, auth/login, real-time updates, CSV export, date-range
pickers, charting library, server pagination, any write/mutation from the
dashboard.
