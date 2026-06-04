# Shipa Ops Dashboard — Business-Driven Metrics Redesign

**Date:** 2026-06-04
**Status:** Approved design, pending implementation plan
**Supersedes:** the KPI/metric choices in `2026-06-04-shipa-command-center-design.md` (layout shell, map, side rail unchanged)

## 1. Goal

Make the command-center landing page (`frontend/app/page.tsx`) Shipa's **daily business-operations dashboard**. It must answer the four questions a last-mile ops manager asks every morning, lead with real delivery outcomes, and keep the voice-agent's value visible — all grounded in stored data, no fabricated figures.

Two current KPIs are removed:
- **"Service Level / first-attempt"** — mislabeled; it was really verification-pass rate, not a delivery KPI.
- **"Network Risk"** (LOW/MED/HIGH composite) — replaced by a concrete **At-Risk** count.

## 2. Data model change (unlocks true delivery KPIs)

Add three columns to `Order` (`app/models/read.py`). Today only current `status` is stored — no attempt history and no actual-delivery time — so first-attempt and on-time cannot be computed honestly. These columns fix that.

| column | type | purpose |
|---|---|---|
| `delivered_at` | `datetime \| null` | actual delivery completion time |
| `attempt_count` | `int`, default `1`, not null | number of delivery attempts made |
| `sla_due_at` | `datetime \| null` | promised delivery deadline (on-time reference) |

`delivery_window` stays as the human-readable label; `sla_due_at` is the machine deadline.

**Propagation (single write path):**
- `OrderRecord` (`app/twin/base.py`) — add the three optional fields.
- `IngestOrder` schema (`app/schemas/ingest.py`) — add the three optional fields (inherits `_BlankToNone`).
- `upsert_orders` (`app/twin/sync.py`) — persist them. `delivered_at`/`sla_due_at` follow the coords pattern: only overwrite when the incoming value is non-null, so a partial sync never wipes a known timestamp. `attempt_count` defaults to 1 on insert; update when provided.
- Alembic migration in `migrations/versions/` — add columns with the defaults above; backfill existing rows (`attempt_count=1`, timestamps null).
- Demo seed `db/seed_demo.py` (`ORDERS_SQL`) — populate realistic values so the dashboard shows live numbers:
  - `attempt_count`: mostly 1; a deterministic minority of `delivered` rows get 2–3, and `failed`/`returned`/`rescheduled` get ≥2.
  - `delivered_at`: set for `delivered` rows (a date derived from the existing window logic).
  - `sla_due_at`: set for terminal/active rows from the same window date; arrange a realistic share of `delivered_at ≤ sla_due_at` (target on-time ≈ 85–92%).

## 3. Metric definitions (locked)

Delivery KPIs are computed over the **current order snapshot** (matches the existing convention where `map_points`/`needs_attention` are current-state); call/interaction charts stay **window-scoped** by the selected range.

Let terminal = orders with status in `{delivered, failed, returned}`.

| metric | definition | source |
|---|---|---|
| **First-Attempt Success** | `delivered AND attempt_count == 1` ÷ `terminal` | `Order` |
| **On-Time Rate** | `delivered AND delivered_at ≤ sla_due_at` ÷ `delivered AND sla_due_at not null` | `Order` |
| **Active Deliveries** | count status in `{out_for_delivery, pending}` | `Order` |
| **At-Risk** | count status in `{failed, returned}` | `Order` |
| **Agent Containment** | calls with a disposition AND no escalation ÷ total calls (window) | `Call`,`Escalation` (existing `deflection_rate`, renamed) |
| **Failed-Delivery Recovery** | failed/returned orders with a reschedule OR address-flag ÷ all failed/returned | `Order`,`Reschedule`,`AddressFlag` |
| **Avg CSAT / Avg Handle Time** | existing `compute_metrics` values (window) | `Call` |

Edge cases: any rate with a zero denominator returns `0.0` (or `null` for CSAT/AHT, as today). On-Time excludes orders missing `sla_due_at` from both numerator and denominator.

## 4. Backend changes

**`app/services/metrics.py` — extend `compute_metrics(db, days)`** to also return:
- `first_attempt_success` (rename/replace `first_attempt_rate`)
- `on_time_rate`
- `active_deliveries`, `at_risk`
- `containment_rate` (rename of `deflection_rate`)
- `recovery_rate`
- keep `avg_csat`, `avg_handle_time_seconds`, `total_calls`

`Metrics` schema (`app/schemas/dashboard.py`) updated to match. Delivery counts query `Order` directly.

**`app/services/insights.py` — extend `compute_insights(db, days)`** to add:
- `interactions_per_day`: stacked-by-channel volume = voice `Call` rows + `FallbackMessage` rows, bucketed by day over the window. Voice channel from calls; other channels from `FallbackMessage.channel` (using `sent_at`, falling back to call/day association where `sent_at` is null). Replaces `calls_per_day`.
- `failures_by_area`: count of `{failed, returned}` orders grouped by `delivery_area` (top N), current-state.
- keep `intent_mix` (voice-only; WISMO highlighted in FE), `disposition_mix`, `needs_attention` (expanded — see below), `map_points`.

New shape for `interactions_per_day`: `[{ date, channels: { voice: int, sms: int, whatsapp: int, ... } }]` (channel keys dynamic from data).

**Expanded `needs_attention`** (the Work Queue) — add `overdue_callbacks` and `pending_address_flags`:
- `open_escalations` (existing)
- `overdue_callbacks`: open `Investigation` where `callback_due_at < now`
- `pending_reschedules`: `Reschedule` not yet synced (existing)
- `pending_address_flags`: `AddressFlag` with status `pending`

`Insights`/`NeedsAttention` schemas updated accordingly.

## 5. Frontend changes (`frontend/`)

**Types/api** (`lib/types.ts`, `lib/api.ts`): update `Metrics`, `Insights`, `NeedsAttention` to the new shapes.

**`app/page.tsx` layout:**
- **Top strip (4 KPIs):** First-Attempt Success · On-Time Rate · Active Deliveries · At-Risk (`KpiStat` reused; tones: outcome rates `ok`, At-Risk `bad` when >0).
- **Main row:** Live map (unchanged `CommandMapClient`) + **Work Queue** panel.
- **Diagnostics row:**
  - *Agent performance* mini-stat cluster: Containment · Recovery · CSAT · Avg Handle Time.
  - **Interactions per day** — stacked bar by channel.
  - **Intent mix** — labeled "Voice intents", WISMO segment highlighted.
  - **Failures by area** — horizontal bar.

**Components:**
- `WorkQueue` (new) — replaces/extends `NeedsAttention`; four actionable rows (escalations, overdue callbacks, unsynced reschedules, pending address flags), each linking to its page (`/escalations`, `/investigations`, `/reschedules`, and an address-flags view or `/orders`). Each row shows count + tone.
- `StackedBarChart` (new) — channel-stacked daily volume; or extend `BarChart` with a stacked mode. Legend by channel.
- `BarChart` (existing) — reused for Failures by area.
- Agent mini-stats — small `KpiStat` variant or inline stat row.
- `RecentCalls` — retained below as-is.

WISMO highlight: intent values matching where-is-my-order (e.g. `track`/`status`/`wismo` — confirm against seeded intent vocabulary) rendered in an accent color.

## 6. List filters / lookups (Customers, Escalations, Investigations, Orders)

Each list page gets full filter + free-text lookup. **Client-side, URL-synced** — pages already fetch full lists, so filtering needs no backend query params; syncing state to the URL (`?status=failed&area=Deira`) makes filtered views bookmarkable and lets the dashboard **Work Queue rows deep-link into a pre-filtered list** (e.g. overdue callbacks → `/investigations?overdue=1`). Server-side query params are the scale-up path, out of scope for the pilot.

**Shared primitives** (new, `frontend/components/`):
- `SearchInput` — debounced free-text.
- `FilterSelect` — dropdown; options derived from the fetched rows.
- `useTableFilters` hook — text match across configured fields + equality filters + URL read/write (`useSearchParams`/`useRouter`). Each table shows a live result count + "no match" empty state.

Each page renders a thin `"use client"` table wrapper using these. `OrdersTable` refactors onto the shared primitives; add `CustomersTable`, `EscalationsTable`, `InvestigationsTable`.

| page | text search | dropdown filters | special |
|---|---|---|---|
| **Orders** | ref · customer · merchant | status · area · merchant · driver | extends current dropdown |
| **Customers** | name · phone | language | sort by order count |
| **Escalations** | category · reason | status · category | — |
| **Investigations** | order ref | status · type | **Overdue only** toggle (`callback_due_at < now`) |

**Schema additions for searchable fields** (`app/schemas/dashboard.py`):
- `EscalationSummary` — add `reason: str \| null` (already on the model).
- `InvestigationSummary` — add `twin_order_ref: str \| null` (resolve via the linked `Order`) so investigations are searchable/displayable by order ref instead of a truncated UUID.

## 7. Out of scope (YAGNI)

- **$ / hours-saved** ROI metrics (need a cost-per-call config) — deferred to a future QBR/review view, not the daily ops dashboard.
- Driver-level performance, merchant scorecards, multi-channel **inbound** (pilot inbound is voice; only `FallbackMessage` adds non-voice events).
- True SLA on investigations beyond the overdue-callback count.

## 8. Testing

- Backend: unit tests for each new metric in `app/services/metrics.py` and `app/services/insights.py` against a seeded session — first-attempt, on-time (incl. null `sla_due_at` exclusion), recovery, at-risk, stacked interactions, overdue callbacks, failures-by-area. Zero-denominator cases.
- Migration: upgrade/downgrade runs clean; existing rows backfill to `attempt_count=1`.
- Frontend gate (per project convention): `tsc` + `eslint` + `next build`. (No FE test harness; backend httpx/TestClient suite has a known pre-existing failure unrelated to this work.)
- Filters: the `EscalationSummary.reason` / `InvestigationSummary.twin_order_ref` schema additions are covered by the existing serialization tests; manually verify URL-synced filters round-trip (set filter → URL updates → reload restores state) and that a Work Queue deep-link lands pre-filtered.

## 9. Risks / notes

- `delivered_at`/`sla_due_at` are demo-seeded for the pilot; in production they must flow from the Twin/ops system via ingest. The schema is ready; populating them is an integration task.
- Stacked interactions conflate inbound voice with outbound fallback messages — label the chart "Interactions (voice + messages)" so it isn't read as inbound-only volume.
