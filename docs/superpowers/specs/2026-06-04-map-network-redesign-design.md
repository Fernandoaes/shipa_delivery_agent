# Command Map Network Redesign — Design

**Date:** 2026-06-04
**Status:** Approved (pending spec review)
**Scope:** Command-center map (`CommandMap`) — color semantics, line semantics, merchant origin nodes, inbound flow.

## Problem

The real-time command map has three legibility gaps:

1. **Backwards color semantics.** `pending` is green (the most "active/positive" hue) while `out_for_delivery` — the thing actually in motion — is blue. An ops person scanning the board reads this inverted.
2. **Invisible first-mile.** The physical flow is `Merchant origin → Shipa hub (Al Quoz) → Customer`, but only the last-mile leg (hub → customer driver routes) is drawn. Merchant origins and the inbound leg don't appear, even though the data carries `merchant_lat/lng` per order.
3. **Hub-and-spoke star.** Last-mile routes are straight geodesic segments fanning from the hub, reading as a synthetic star rather than dispatched routes.

## Goals

- Recolor order statuses to match operational reading (queue → go → caution → stop).
- Introduce **merchant origin nodes** (industrial icon) and an **inbound flow line** so the full two-stage network is visible.
- Keep the map readable as **three semantic layers**: order state, fleet/last-mile, inbound supply.
- Soften last-mile lines into arcs.

## Non-Goals

- **Real street-following routing** (OSRM/Mapbox/GraphHopper). Deferred: adds an external dependency, latency, rate limits, and a failure mode, recomputed on every refresh. A command-center overview cares about *who covers whom* and *fan-out from the hub*, not turn-by-turn — that belongs in order/driver detail. Gentle curved polylines deliver the visual win with no dependency.
- A merchant master-data table. Merchant remains a denormalized string + coords on each order; nodes are derived by deduping.

## Design

### Three semantic layers

| Layer | Hue family | Question it answers |
|---|---|---|
| Order state | blue / green / amber / red | "Status of each delivery?" |
| Fleet / last-mile | cyan | "Where are trucks and their paths?" |
| Inbound supply | violet | "What's flowing into the hub?" |

### 1. Order status colors (`CommandMap.tsx` `STATUS_COLOR` + `LEGEND`)

| Status | Current | New | Rationale |
|---|---|---|---|
| `pending` | green `#34d399` | **blue `#3b82f6`** | Queued/waiting — cool, calm |
| `out_for_delivery` | blue `#3b82f6` | **green `#34d399`** | In motion / on track — "go" |
| `rescheduled` | amber `#f59e0b` | amber `#f59e0b` (unchanged) | Caution — needs attention |
| `failed` | red `#ef4444` | red `#ef4444` (unchanged) | Stop — problem |

Net change: swap blue and green between `pending` and `out_for_delivery`. The legend entry for "Driver en route" stays cyan `#22d3ee`.

### 2. Line semantics & styling

| Line | Color | Style | Notes |
|---|---|---|---|
| Last-mile (hub → customers) | cyan `#22d3ee` | solid, weight 2.5, opacity 0.6, **animated flowing dash**, **arced** | Unchanged hue; add motion + curve |
| ↳ at-risk variant | amber `#f59e0b` | solid (animated, arced) | Route contains a failed order. Amber (not red) — the route isn't failed, it contains a failure; markers carry status, lines carry flow + health |
| Inbound (merchant → hub) | violet `#a78bfa` | **dashed**, thin (1.5), opacity 0.35 | Subordinate to last-mile; reads as "coming in." Matches merchant node hue |

**Visual story:** violet dashed flows *into* the hub, cyan solid (flowing) flows *out* to customers — two stages legible without the legend.

**Animated flow:** CSS/SVG `stroke-dashoffset` animation on the cyan route (Leaflet `Polyline` renders an SVG `path`; animate via a CSS class on the renderer or `dashArray` + keyframes). Lightweight, no dependency. If `prefers-reduced-motion`, render static.

**Arced last-mile:** replace straight segments with a quadratic curve — offset each segment's midpoint perpendicular to the chord by a small factor, sampling N points into the polyline. Pure geometry in `insights.ts`, no dependency.

### 3. Merchant origin nodes

- **Derivation (`insights.ts`):** dedupe active `map_points` by `merchant` name; take the modal (or first) `merchant_lat/lng` per merchant. If a merchant's coords diverge across orders beyond a small epsilon, log/flag — it signals the seed encodes per-pickup, not per-HQ, coords.
- **Icon (`CommandMap.tsx`):** industrial/warehouse `divIcon`, violet `#a78bfa`, deliberately **outside** the status palette so origins never read as an order state. Distinct glyph (factory/warehouse SVG) and shape from pin (order) and circle (driver).
- **Popup:** merchant name + count of live orders from that origin.

### 4. Inbound line — Option A (active-only)

Draw a `merchant → hub` violet dashed line **only when that merchant has ≥1 active order** (`pending` or `out_for_delivery`). Reads as "packages coming in *now*," not a static supplier footprint. Avoids clutter and staleness.

### 5. Legend update

Add a **Merchant origin** entry (violet square). Order: Out for delivery (green), Pending (blue), Rescheduled (amber), Failed (red), Driver en route (cyan), Merchant origin (violet).

## Data flow / required changes

Plotting merchant nodes requires merchant coords in the `map_points` payload, which currently carries only `delivery_*`.

**Backend:**
- `app/schemas/dashboard.py` — `MapPoint`: add `merchant: str`, `merchant_lat: float | None`, `merchant_lng: float | None`.
- `app/services/insights.py` — `map_points` dict (~L64): include `merchant`, `merchant_lat`, `merchant_lng`. Keep the `delivery_lat/lng IS NOT NULL` + active-status filter; merchant coords may be null (skip those for node derivation).

**Frontend:**
- `frontend/lib/types.ts` — `MapPoint`: add `merchant`, `merchant_lat: number | null`, `merchant_lng: number | null`.
- `frontend/lib/insights.ts` — `buildMerchantNodes(points)` (dedupe + coord-divergence guard); arc helper for last-mile paths; optionally `buildInboundLines(nodes)` for active merchants.
- `frontend/components/CommandMap.tsx` — swap status colors; `merchantIcon()` divIcon; render merchant markers + inbound polylines; animated/arced last-mile; legend entry.

## Components (frontend units)

- **`buildMerchantNodes`** — in: `MapPoint[]`; out: `{ merchant, position: LatLng, activeCount }[]`; dedupes by name, guards coord divergence. Pure.
- **`arcPath`** — in: `LatLng[]` (hub → stops); out: densified `LatLng[]` with curved segments. Pure.
- **`merchantIcon`** — in: none (fixed violet); out: Leaflet `divIcon`.
- **`CommandMap`** — composes the above; owns rendering and the legend.

Each is independently testable; `insights.ts` helpers are pure functions with unit-test seams.

## Testing

- **`buildMerchantNodes`:** dedupes orders sharing a merchant into one node; counts active orders; flags divergent coords; skips null-coord merchants.
- **`arcPath`:** returns a curve (midpoint offset from chord) and preserves endpoints.
- **Backend `map_points`:** payload includes merchant fields; null merchant coords tolerated.
- **Visual smoke (manual):** statuses render new colors; merchant nodes appear with inbound lines only when active; last-mile arcs animate.

## Risks

- **Coord divergence** — if seed coords are per-pickup, merchant nodes are approximate. Mitigated by the divergence flag; acceptable for an overview.
- **Animation cost** — many SVG dash animations can tax low-end devices. Cap by only animating active last-mile routes; honor `prefers-reduced-motion`.
- **Clutter** — many distinct merchants could crowd the hub. Active-only inbound lines + subordinate styling mitigate; revisit clustering if merchant count grows large.
