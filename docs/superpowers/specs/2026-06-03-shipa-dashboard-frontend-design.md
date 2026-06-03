# SHIPA Delivery Ops Dashboard — Design Spec

> Status: **approved for implementation planning** (2026-06-03).
> Scope: ops-facing read dashboard (Orders + Customers, with a geographic delivery map), plus the
> minimal backend read endpoints + coordinate data it needs. Wired to the live FastAPI API.
> Builds on `2026-06-02-shipa-inbound-backend-design.md` (the backend) and `database_schema.md`.

## 1. Goal

Give Shipa ops one place to see **all orders and customers** and, per order, a **geographic map**
of the delivery: merchant origin → delivery address, with merchant info, address, status, driver,
and window alongside. Demo-grade but **fully functional end to end** against the live API. Simplicity
first; the map is the one place we invest in polish because it carries the demo.

Out of scope: overview/metrics screen, ops queues (investigations/reschedules/escalations) screens,
live driver position, auth/login UI, write actions from the dashboard. All read-only.

## 2. Decisions (locked)

| Decision | Choice |
|---|---|
| Frontend stack | Next.js (App Router) + TypeScript + Tailwind CSS |
| Map | Leaflet + OpenStreetMap tiles (no API key) |
| Screens | Orders list → Order detail (map); Customers list → Customer detail (table of their orders) |
| Data source | Live FastAPI API, fetched server-side (API key never reaches the browser) |
| Coordinates | Stored lat/lng on orders, seeded with real UAE coordinates |
| Route line | Straight polyline merchant→delivery (OSRM road geometry is a later drop-in) |
| Customer detail | Table of their orders (no per-customer map) |
| Driver pin | Skipped (schema has a driver name, no position) |

## 3. Architecture

```
Browser ──▶ Next.js server component ──(fetch + X-API-Key from env)──▶ FastAPI /orders, /customers
                  │                                                         │
            passes data as props                                     dashboard router (api-key auth)
                  ▼                                                         │
        DeliveryMap (client, Leaflet) ── OSM tiles                   SQLAlchemy ──▶ Postgres
```

- The API key lives only in the Next.js server environment; the browser never sees it. The map is the
  only client component (Leaflet needs `window`); it receives already-fetched data as props.
- The dashboard endpoints are **ops-facing**, behind the existing `X-API-Key` auth. `delivery_address`
  and customer contact are intentionally exposed *here* — the strict PII/OTP minimization in the
  backend spec governs the **agent/caller** path, not the authenticated ops dashboard. **`otp_code` is
  never exposed by these endpoints** (it stays caller-flow only); a test pins this.

## 4. Backend changes

### 4.1 Schema / migration
Add four nullable `float` columns to `orders`: `merchant_lat`, `merchant_lng`, `delivery_lat`,
`delivery_lng`. New Alembic revision; nullable so existing rows are unaffected.

Update `app/models/read.py` (`Order`) and `app/twin/base.py` (`OrderRecord`, same four fields,
defaulting `None`) and `app/twin/sync.py` (`upsert_orders` copies the four fields through). This keeps
the single write path intact, so a future real-Twin feed can supply coordinates the same way.

### 4.2 Seed data (real UAE coordinates)
Populate coordinates in `app/twin/mock.py` and `db/seed_twin_mock.sql` (and the bulk/test seeds where
they add orders). Delivery points use the existing Dubai areas; merchants map to plausible
fulfillment-hub coordinates. Indicative values (finalized in implementation):

| Area / merchant | lat, lng |
|---|---|
| Dubai Marina (delivery) | 25.0805, 55.1403 |
| Al Barsha | 25.1107, 55.2014 |
| Business Bay | 25.1857, 55.2645 |
| Deira / Naif Rd | 25.2730, 55.3050 |
| JLT | 25.0693, 55.1440 |
| Amazon hub (Dubai South) | 24.9180, 55.1610 |
| Temu / Noon hub (DIP) | 24.9700, 55.1800 |
| Trendyol hub (Al Quoz) | 25.1200, 55.2000 |

### 4.3 Endpoints (added to the existing dashboard router, `X-API-Key` auth)
- `GET /orders` → `list[OrderListItem]`: `order_id`, `twin_order_ref`, `merchant`, `status`,
  `delivery_area`, `delivery_window`, `assigned_driver`, `customer_name`.
- `GET /orders/{order_id}` → `OrderDetail`: list fields + `delivery_address`, `expected_pieces`,
  `merchant_lat/lng`, `delivery_lat/lng`, `last_synced_at`, and a nested `customer`
  (`customer_id`, `full_name`, `primary_phone`, `language_pref`). `404` if not found. **No `otp_code`.**
- `GET /customers` → `list[CustomerListItem]`: `customer_id`, `full_name`, `primary_phone`,
  `language_pref`, `order_count`.
- `GET /customers/{customer_id}` → `CustomerDetail`: contact fields + `orders` (list of `OrderListItem`).
  `404` if not found.

New Pydantic schemas in `app/schemas/dashboard.py` (or a new `app/schemas/read_views.py`); query/join
logic in `app/services/orders.py` (and a small `customers` service helper). Routers stay thin.

### 4.4 CORS
Add `CORSMiddleware` in `app/main.py` allowing the frontend origin (env-driven, default
`http://localhost:3000`). Primary fetch is server-side, but this keeps any client-side calls working.

### 4.5 Tests (mirror `tests/test_dashboard.py`)
- Each new endpoint requires the API key (401/403 without it).
- `GET /orders` / `/customers` return the expected shape and counts against seeded data.
- `GET /orders/{id}` includes coordinates + nested customer and **omits `otp_code`**.
- `404` on unknown `order_id` / `customer_id`.

## 5. Frontend

### 5.1 Structure
```
frontend/
  app/
    layout.tsx              # SHIPA shell: top bar (logo) + nav (Orders | Customers)
    page.tsx                # redirect → /orders
    orders/page.tsx         # orders table
    orders/[id]/page.tsx    # order detail + DeliveryMap
    customers/page.tsx      # customers table
    customers/[id]/page.tsx # customer detail + their orders table
  components/
    DeliveryMap.tsx         # 'use client' — Leaflet map, two pins + route line
    StatusBadge.tsx         # status → brand color chip
    DataTable.tsx           # simple reusable table
    TopBar.tsx              # logo + nav links (active state)
  lib/
    api.ts                  # server-side typed fetch (base URL + X-API-Key from env)
    types.ts                # TS types mirroring the Pydantic response models
  public/shipa-logo.svg     # provided logo asset
  tailwind.config.ts        # brand theme tokens
  .env.example              # API_BASE_URL, DASHBOARD_API_KEY, NEXT_PUBLIC_* as needed
```

### 5.2 Screens
- **Orders list:** table of `GET /orders` — ref, customer, merchant, status badge, area, window,
  driver. Row click → order detail. Optional client-side text filter (simple).
- **Order detail:** header (ref + status), a details card (merchant, full address, window, driver,
  pieces, customer name/phone), and the **DeliveryMap** beside/below it.
- **Customers list:** table of `GET /customers` — name, phone, language, order count. Row → detail.
- **Customer detail:** contact card + table of their orders (each row links to the order detail map).

### 5.3 DeliveryMap (the insightful part)
`'use client'` Leaflet component fed `{merchant, merchantLatLng, deliveryAddress, deliveryLatLng,
status}`:
- **Merchant pin** (origin, ink/dark) and **delivery pin** (destination, brand-blue) — visually
  distinct markers with popups (merchant name / delivery address + status).
- **Route line:** straight `Polyline` merchant→delivery. (Real road geometry via public OSRM is a
  later swap with straight-line fallback — explicitly deferred, not built now.)
- **Auto-fit** bounds to both points with padding; sensible default zoom if a coordinate is missing
  (render the available pin, skip the line, show a "coordinates unavailable" note).
- Leaflet is dynamically imported (`ssr: false`) so it only runs in the browser.

### 5.4 Brand
Tailwind theme tokens (hexes finalized in implementation, refined when reviewing the running app):
- `shipa-blue` — electric swoosh blue: primary accent, active nav, delivery pin, links/buttons.
- `shipa-ink` — near-black: text, wordmark, merchant pin.
- `shipa-sky` — light-blue hero tint: page/section background washes.
- White cards/surfaces, subtle borders. Logo (`SHIPA` wordmark + blue swoosh) in the top bar.
- Status badge colors: `delivered` green, `out_for_delivery` blue, `failed` red, `pending` amber,
  `rescheduled`/`returned`/`cancelled` neutral.

### 5.5 Data access
`lib/api.ts` exposes typed `getOrders()`, `getOrder(id)`, `getCustomers()`, `getCustomer(id)` that
fetch `${API_BASE_URL}` with the `X-API-Key` header from server env. Called only from server
components. Errors surface a simple inline error state; no global state library.

## 6. Data flow & later DB integration

Already live-API-bound. The "DB integration" phase is purely backend: replace seeded mock data with a
real Twin sync behind the *same* endpoints. **No frontend change required.**

## 7. Testing & verification

- Backend: pytest as in §4.5.
- Frontend: keep light for the demo — a smoke check that pages render against a running seeded backend.
  No component test suite for v1 (flagged: behavior is read-only and visual; revisit if it grows).
- Manual verification before claiming done: backend up + seeded → load `/orders`, open an order, see
  two pins + route line on the map; load `/customers`, open one, see their orders.

## 8. Out of scope / deferred (explicit)
- Real road routing (OSRM) — straight line for now.
- Live driver position — no data.
- Metrics/overview and ops-queue screens.
- Dashboard auth/login UI (single shared API key, server-side).
- Write actions from the dashboard (read-only product).
