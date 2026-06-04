# SHIPA Command Center — Frontend Design

**Date:** 2026-06-04
**Status:** Approved
**Goal:** Make the ops dashboard demo-ready and production-grade by turning it into a dark, map-centric **command center** modeled on the customer reference image. Every decision optimizes for demonstrable value to SHIPA Delivery.

## Decisions (locked)

| Area | Decision |
|---|---|
| Page architecture | **Command Center** — the live Dubai map is the homepage (`/`). |
| Map | **Real** street map (CARTO `dark_matter` tiles via existing react-leaflet). Not a choropleth. |
| Navigation | **Left vertical icon rail, app-wide**, replacing the top nav. |
| KPIs | Mapped to **real backend signals** — no fabricated revenue. |
| Scope | **Home + nav/shell first.** Inner pages inherit theme tokens; not individually reworked. |
| Map engine rationale | CARTO+Leaflet supports pinch/two-finger zoom + `divIcon` custom markers (warehouse/truck/customer) — equals the reference look, token-free, no new deps, Railway-safe. Mapbox rejected (needs token, zero functional gain). |

## Reference

Customer-supplied screenshot: dark Mapbox-style UAE/Dubai map; left icon rail with SHIPA mark; 4-card KPI strip (Service Level, Active Orders, Pipeline Revenue, Network Risk); rounded-square icon markers + faint green routes; bottom-left mono "Network Health" overlay; right "Live Orders" panel with LIVE pulse and a ROUTE/PAYLOAD list; monospace data type, grotesk display type.

## Architecture

### 1. Shell (app-wide)
- **Left icon rail** (`TopBar` → `SideRail`): dark, fixed-left, ~64px. SHIPA mark top; nav icons for Overview, Orders, Customers, Calls, Reschedules, Investigations, Escalations; theme/info bottom. Active state = SHIPA-blue highlight + filled icon. Hover tooltips with labels. `main` shifts right by rail width.
- **Dark theme tokens** in `globals.css`:
  - `--shipa-ink #0b0d12` (app bg), `--shipa-panel #11141b`, `--shipa-panel-2 #161a22`, hairline border `rgba(255,255,255,.08)`.
  - Accent `--shipa-blue #2b3ff2`; status: `--ok #34d399`, `--warn #f59e0b`, `--bad #ef4444`, `--muted #94a3b8`.
  - Text: primary `#e6e9ef`, secondary `rgba(230,233,239,.6)`.
- **Typography:** wire the dangling `--font-geist-sans` / `--font-geist-mono` to actual Geist fonts via `next/font` in `layout.tsx`. Display = Geist Sans; data/labels/KPIs = Geist Mono (uppercase, letter-spaced for labels).

### 2. Command-center home (`/`)
Replaces current Overview layout.
- **Header:** "Shipa Delivery" (display) + "REAL-TIME MONITORING" (mono, uppercase, letter-spaced).
- **KPI strip — 4 cards, real data:**
  1. **Service Level** ← `metrics.first_attempt_rate` (%), green.
  2. **Active Orders** ← count of `map_points` with status `out_for_delivery` (+ `pending`).
  3. **Deflection** ← `metrics.deflection_rate` (%).
  4. **Network Risk** ← derived: `HIGH` if `needs_attention.open_escalations > 0` OR `failed_orders ≥ 2`; `MED` if either is nonzero; else `LOW`. Card accent red/amber/green accordingly.
  - Each card: label (mono), big value, status icon, optional sub.
- **Hero map (`CommandMap`):** full-bleed, ~68vh.
  - CARTO `dark_matter` tiles. `scrollWheelZoom` + `touchZoom` enabled (pinch + buttons).
  - Hub = warehouse `divIcon` (rounded square, blue). Stops = status-colored rounded-square `divIcon` markers matching reference. Routes = faint hub→stop polylines (green, low opacity).
  - Click stop → navigate `/orders/{id}`. Popups dark-themed.
  - Bottom-left **Network Health** mono overlay: Nominal (on-track count), At Risk (failed+escalated), `ACTIVE_ROUTES: n`.
- **Right "Live Orders" panel:** docked right of map (or below on mobile). `● LIVE` green pulse; "SHIPA DELIVERY" subtitle; scrollable list of active orders (customer name · delivery area · status dot). Row click → `/orders/{id}`.
- **Below the fold:** existing `BarChart` calls-per-day + intent-mix and range filter retained, restyled dark. Recent calls + needs-attention remain accessible (kept on home beneath map).

### 3. Data mapping (no backend change)
- All from existing `getMetrics()` + `getInsights(days)` + `getCalls()`/`getOrders()`.
- KPIs ← `metrics` + `insights.needs_attention` + `insights.map_points`.
- Map + Live Orders ← `insights.map_points` (active subset for the panel).
- Hub coords = existing constant `[25.158, 55.236]` (Al Quoz), matches seed origin.

### 4. Components
- New: `SideRail.tsx`, `CommandMap.tsx` (+ `CommandMapClient.tsx` dynamic/ssr-false wrapper), `LiveOrdersPanel.tsx`, `NetworkHealthOverlay.tsx`, `RiskKpiCard.tsx` (or extend `KpiCard`).
- Modified: `app/layout.tsx` (fonts + rail), `app/page.tsx` (command-center composition), `app/globals.css` (dark tokens), `KpiCard.tsx`, `BarChart.tsx` (dark restyle), `MapClient`/`DeliveryMap` (dark tile + icon parity on order detail).
- Removed/retired: `TopBar.tsx` (replaced by `SideRail`); `DeliveriesMap`/`DeliveriesMapClient` superseded by `CommandMap` (delete after parity confirmed).

### 5. Map cleanliness (explicit, per customer ask)
- Muted dark basemap, no clutter; thin hairline panel borders; consistent 8px marker grid alignment; routes at ≤0.25 opacity so pins dominate; legend/overlay non-interactive (`pointer-events:none`); generous padding via `fitBounds`. Professional, readable, uncluttered.

## Out of scope (this pass)
- Reworking inner pages individually (they inherit tokens + rail only).
- Live/simulated driver GPS (no data source; render real stops/hub/routes only).
- Backend/API changes.
- Mapbox, choropleth, fabricated revenue metric.

## Risks
- **Geist fonts via next/font** in this Next 16 build — verify API in `node_modules/next/dist/docs/` before wiring (per repo AGENTS.md: this Next.js has breaking changes).
- **Leaflet SSR** — `CommandMap` must stay client-only via dynamic import (`ssr:false`), as the current map already does.
- **Dark popups/tiles** — Leaflet default CSS is light; override popup styles for dark theme.

## Testing
- Manual: run `next dev`, verify map renders, pinch+button zoom, pin click → order, KPI values match API, rail nav works on all 7 routes, responsive down to tablet width.
- Visual parity check against reference screenshot.
- No existing automated FE tests; flag if the user wants component tests added.
