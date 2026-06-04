# Command Map Network Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recolor order statuses, add merchant origin nodes with an active-only inbound flow line, and turn last-mile routes into animated arcs on the command-center map.

**Architecture:** Backend extends the `map_points` payload with merchant coords (the map currently only receives delivery coords). Frontend derives merchant nodes and curved paths via pure helpers in `lib/insights.ts` (newly unit-tested with Vitest), and `CommandMap.tsx` renders the three semantic layers: order state (blue/green/amber/red markers), fleet/last-mile (cyan animated arcs), inbound supply (violet dashed lines + merchant icons).

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic (backend, `uv run pytest`); Next.js 16 / React 19 + react-leaflet (frontend); Vitest (new, for `lib/` pure helpers).

**Spec:** `docs/superpowers/specs/2026-06-04-map-network-redesign-design.md`

---

## File Structure

**Backend (modify):**
- `app/schemas/dashboard.py` — `MapPoint` schema: add merchant fields.
- `app/services/insights.py` — `map_points` dict: emit merchant fields.
- `tests/test_insights_service.py` — add coverage for merchant fields.

**Frontend (create):**
- `frontend/vitest.config.ts` — Vitest config with `@/` alias.
- `frontend/lib/insights.test.ts` — unit tests for the pure helpers.

**Frontend (modify):**
- `frontend/lib/types.ts` — `MapPoint`: add merchant fields.
- `frontend/lib/insights.ts` — add `buildMerchantNodes` + `arcPath` (+ `MerchantNode` type).
- `frontend/components/CommandMap.tsx` — color swap, merchant icon/markers, inbound lines, animated arced last-mile, legend.
- `frontend/app/globals.css` — `cc-flow` keyframe.
- `frontend/package.json` — add `vitest` dev dep + `test` script.

---

## Task 1: Backend — merchant coords in `map_points`

**Files:**
- Modify: `app/schemas/dashboard.py:186-192`
- Modify: `app/services/insights.py:64-74`
- Test: `tests/test_insights_service.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_insights_service.py`:

```python
def test_map_points_include_merchant_origin(db):
    _seed(db)
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    order.status = "out_for_delivery"
    order.delivery_lat, order.delivery_lng = 25.1, 55.2
    order.merchant = "Noon"
    order.merchant_lat, order.merchant_lng = 24.92, 55.16
    db.flush()

    out = compute_insights(db)
    pt = next(p for p in out["map_points"] if p["twin_order_ref"] == "TWIN-1001")
    assert pt["merchant"] == "Noon"
    assert pt["merchant_lat"] == 24.92
    assert pt["merchant_lng"] == 55.16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_insights_service.py::test_map_points_include_merchant_origin -v`
Expected: FAIL with `KeyError: 'merchant'`.

- [ ] **Step 3: Emit merchant fields in the service**

In `app/services/insights.py`, replace the `map_points` list comprehension (currently lines 64-74) with:

```python
    map_points = [
        {
            "order_id": o.order_id,
            "twin_order_ref": o.twin_order_ref,
            "status": o.status,
            "delivery_area": o.delivery_area,
            "delivery_lat": o.delivery_lat,
            "delivery_lng": o.delivery_lng,
            "merchant": o.merchant,
            "merchant_lat": o.merchant_lat,
            "merchant_lng": o.merchant_lng,
        }
        for o in map_orders
    ]
```

- [ ] **Step 4: Add merchant fields to the schema**

In `app/schemas/dashboard.py`, replace the `MapPoint` class (currently lines 186-192) with:

```python
class MapPoint(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    status: str
    delivery_area: str | None
    delivery_lat: float
    delivery_lng: float
    merchant: str
    merchant_lat: float | None
    merchant_lng: float | None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_insights_service.py -v`
Expected: PASS (new test + all existing insights tests, including `test_map_points_only_active_with_coords`).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/services/insights.py tests/test_insights_service.py
git commit -m "feat(insights): carry merchant origin coords in map_points"
```

---

## Task 2: Frontend — add Vitest

**Files:**
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Install Vitest**

Run: `cd frontend && npm install -D vitest`
Expected: `vitest` added to `devDependencies`.

- [ ] **Step 2: Create the Vitest config**

Create `frontend/vitest.config.ts`:

```typescript
import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
});
```

- [ ] **Step 3: Add the test script**

In `frontend/package.json`, add `"test": "vitest run"` to the `"scripts"` object so it reads:

```json
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "test": "vitest run"
  },
```

- [ ] **Step 4: Verify the runner works (no tests yet)**

Run: `cd frontend && npm test`
Expected: Vitest runs and reports "No test files found" (exit 0 with `--passWithNoTests` is not set, so it may exit 1 with "No test files found, exiting with code 1" — that's fine; the next task adds files).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "chore(frontend): add vitest for lib helpers"
```

---

## Task 3: Frontend — merchant fields on `MapPoint` type

**Files:**
- Modify: `frontend/lib/types.ts:57-64`

- [ ] **Step 1: Add merchant fields**

In `frontend/lib/types.ts`, replace the `MapPoint` type (currently lines 57-64) with:

```typescript
export type MapPoint = {
  order_id: string;
  twin_order_ref: string;
  status: string;
  delivery_area: string | null;
  delivery_lat: number;
  delivery_lng: number;
  merchant: string;
  merchant_lat: number | null;
  merchant_lng: number | null;
};
```

- [ ] **Step 2: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no new errors; existing `map_points` consumers still compile since fields are additive).

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(types): merchant origin fields on MapPoint"
```

---

## Task 4: Frontend — `buildMerchantNodes` helper

**Files:**
- Modify: `frontend/lib/insights.ts`
- Test: `frontend/lib/insights.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/lib/insights.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { buildMerchantNodes } from "@/lib/insights";
import type { MapPoint } from "@/lib/types";

function pt(overrides: Partial<MapPoint>): MapPoint {
  return {
    order_id: crypto.randomUUID(),
    twin_order_ref: "TWIN-X",
    status: "out_for_delivery",
    delivery_area: "Karama",
    delivery_lat: 25.1,
    delivery_lng: 55.2,
    merchant: "Noon",
    merchant_lat: 24.92,
    merchant_lng: 55.16,
    ...overrides,
  };
}

describe("buildMerchantNodes", () => {
  it("dedupes orders sharing a merchant into one node and counts active orders", () => {
    const nodes = buildMerchantNodes([
      pt({ merchant: "Noon", status: "out_for_delivery" }),
      pt({ merchant: "Noon", status: "pending" }),
      pt({ merchant: "Noon", status: "failed" }),
    ]);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].merchant).toBe("Noon");
    expect(nodes[0].position).toEqual([24.92, 55.16]);
    expect(nodes[0].activeCount).toBe(2); // failed is not active
    expect(nodes[0].coordsDiverge).toBe(false);
  });

  it("flags divergent coords for the same merchant", () => {
    const nodes = buildMerchantNodes([
      pt({ merchant: "Amazon", merchant_lat: 24.92, merchant_lng: 55.16 }),
      pt({ merchant: "Amazon", merchant_lat: 25.30, merchant_lng: 55.40 }),
    ]);
    expect(nodes[0].coordsDiverge).toBe(true);
  });

  it("skips merchants with null origin coords", () => {
    const nodes = buildMerchantNodes([
      pt({ merchant: "NoCoords", merchant_lat: null, merchant_lng: null }),
    ]);
    expect(nodes).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — `buildMerchantNodes` is not exported.

- [ ] **Step 3: Implement the helper**

In `frontend/lib/insights.ts`, add after the `ACTIVE` set (line 8) the type and function. Add the import of `MapPoint` is already present (line 1 imports `MapPoint`). Insert:

```typescript
const COORD_EPSILON = 0.001; // ~100m; larger divergence means per-pickup coords, not a single HQ

export type MerchantNode = {
  merchant: string;
  position: LatLng;
  activeCount: number;
  coordsDiverge: boolean;
};

// Derive one origin node per merchant by deduping active map points on the merchant name.
export function buildMerchantNodes(points: MapPoint[]): MerchantNode[] {
  const groups = new Map<string, MapPoint[]>();
  for (const p of points) {
    if (p.merchant_lat == null || p.merchant_lng == null) continue;
    const g = groups.get(p.merchant);
    if (g) g.push(p);
    else groups.set(p.merchant, [p]);
  }

  const nodes: MerchantNode[] = [];
  for (const [merchant, pts] of groups) {
    const position: LatLng = [pts[0].merchant_lat as number, pts[0].merchant_lng as number];
    const coordsDiverge = pts.some(
      (p) =>
        Math.abs((p.merchant_lat as number) - position[0]) > COORD_EPSILON ||
        Math.abs((p.merchant_lng as number) - position[1]) > COORD_EPSILON,
    );
    const activeCount = pts.filter((p) => ACTIVE.has(p.status)).length;
    nodes.push({ merchant, position, activeCount, coordsDiverge });
  }
  return nodes;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: PASS (3 tests in `buildMerchantNodes`).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/insights.ts frontend/lib/insights.test.ts
git commit -m "feat(insights): buildMerchantNodes with coord-divergence guard"
```

---

## Task 5: Frontend — `arcPath` helper

**Files:**
- Modify: `frontend/lib/insights.ts`
- Test: `frontend/lib/insights.test.ts`

- [ ] **Step 1: Write the failing tests**

Append to `frontend/lib/insights.test.ts`:

```typescript
import { arcPath } from "@/lib/insights";
import type { LatLng } from "@/lib/insights";

describe("arcPath", () => {
  it("returns the input unchanged for paths shorter than 2 points", () => {
    expect(arcPath([])).toEqual([]);
    const one: LatLng[] = [[25.0, 55.0]];
    expect(arcPath(one)).toEqual(one);
  });

  it("preserves the original endpoints", () => {
    const out = arcPath([
      [25.0, 55.0],
      [25.2, 55.4],
    ]);
    expect(out[0]).toEqual([25.0, 55.0]);
    expect(out[out.length - 1]).toEqual([25.2, 55.4]);
  });

  it("bows the segment off the straight chord", () => {
    const a: LatLng = [25.0, 55.0];
    const b: LatLng = [25.0, 55.4]; // horizontal chord (constant lat)
    const out = arcPath([a, b]);
    const mid = out[Math.floor(out.length / 2)];
    // a curved segment must leave the constant-lat line somewhere
    expect(out.some((p) => Math.abs(p[0] - 25.0) > 1e-6)).toBe(true);
    expect(mid[0]).not.toBe(25.0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — `arcPath` is not exported.

- [ ] **Step 3: Implement the helper**

In `frontend/lib/insights.ts`, add:

```typescript
const ARC_CURVATURE = 0.18; // perpendicular bow as a fraction of chord length
const ARC_SEGMENTS = 16;

// Densify a hub→stops path into quadratic-bezier arcs so routes read as dispatched
// curves rather than a hub-and-spoke star. Pure geometry, no routing engine.
export function arcPath(path: LatLng[]): LatLng[] {
  if (path.length < 2) return path;
  const out: LatLng[] = [path[0]];
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const mx = (a[0] + b[0]) / 2;
    const my = (a[1] + b[1]) / 2;
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const cx = mx - dy * ARC_CURVATURE; // control point offset perpendicular to chord
    const cy = my + dx * ARC_CURVATURE;
    for (let s = 1; s <= ARC_SEGMENTS; s++) {
      const t = s / ARC_SEGMENTS;
      const u = 1 - t;
      const lat = u * u * a[0] + 2 * u * t * cx + t * t * b[0];
      const lng = u * u * a[1] + 2 * u * t * cy + t * t * b[1];
      out.push([lat, lng]);
    }
  }
  return out;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: PASS (all `buildMerchantNodes` + `arcPath` tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/insights.ts frontend/lib/insights.test.ts
git commit -m "feat(insights): arcPath bezier helper for last-mile routes"
```

---

## Task 6: Frontend — CommandMap layers + flow animation

**Files:**
- Modify: `frontend/components/CommandMap.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Add the flow keyframe**

In `frontend/app/globals.css`, after the `.live-dot` rule (line ~75), add:

```css
@keyframes cc-flow {
  to { stroke-dashoffset: -22; }
}
.cc-flow { animation: cc-flow 1.1s linear infinite; }
@media (prefers-reduced-motion: reduce) {
  .cc-flow { animation: none; }
}
```

- [ ] **Step 2: Swap status colors and extend the legend**

In `frontend/components/CommandMap.tsx`, replace the `STATUS_COLOR` and `LEGEND` blocks (lines 11-24) with:

```typescript
const MERCHANT_COLOR = "#a78bfa";

const STATUS_COLOR: Record<string, string> = {
  out_for_delivery: "#34d399", // green = in motion / on track
  pending: "#3b82f6", // blue = queued / waiting
  failed: "#ef4444",
  rescheduled: "#f59e0b", // amber = needs attention
};

const LEGEND: [string, string][] = [
  ["Out for delivery", STATUS_COLOR.out_for_delivery],
  ["Pending", STATUS_COLOR.pending],
  ["Rescheduled", STATUS_COLOR.rescheduled],
  ["Failed", STATUS_COLOR.failed],
  ["Driver en route", "#22d3ee"],
  ["Merchant origin", MERCHANT_COLOR],
];
```

- [ ] **Step 3: Import the new helpers**

In `frontend/components/CommandMap.tsx`, replace the insights import (line 9) with:

```typescript
import { HUB, healthCounts, buildMerchantNodes, arcPath, type DriverRoute, type LatLng } from "@/lib/insights";
```

- [ ] **Step 4: Add the merchant icon and factory glyph**

In `frontend/components/CommandMap.tsx`, after the `TRUCK_GLYPH` constant (line 31), add:

```typescript
const FACTORY_GLYPH =
  '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="white" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20h20"/><path d="M4 20V9l6 4V9l6 4V6l4 2v12"/><path d="M9 20v-4h2v4"/></svg>';

function merchantIcon() {
  return L.divIcon({
    className: "",
    html: `<div style="background:${MERCHANT_COLOR};width:24px;height:24px;border-radius:6px;border:1.5px solid rgba(255,255,255,.85);box-shadow:0 2px 8px rgba(0,0,0,.5),0 0 0 1px ${MERCHANT_COLOR}55;display:flex;align-items:center;justify-content:center">${FACTORY_GLYPH}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });
}
```

- [ ] **Step 5: Derive merchant nodes and include them in bounds**

In `frontend/components/CommandMap.tsx`, inside the component body, replace the `bounds` line (line 77) with:

```typescript
  const merchants = buildMerchantNodes(points);
  const bounds: LatLng[] = [HUB, ...latlngs, ...merchants.map((m) => m.position)];
```

- [ ] **Step 6: Animate + arc the last-mile routes**

In `frontend/components/CommandMap.tsx`, replace the driver-route `Polyline` block (lines 96-106) with:

```typescript
        {drivers.map((d) => (
          <Polyline
            key={`route-${d.driver}`}
            positions={arcPath(d.path)}
            pathOptions={{
              color: d.atRisk ? "#f59e0b" : "#22d3ee",
              weight: 2.5,
              opacity: 0.7,
              dashArray: "1 10",
              className: "cc-flow",
            }}
          />
        ))}
```

- [ ] **Step 7: Render inbound lines and merchant markers**

In `frontend/components/CommandMap.tsx`, immediately after the driver-route block from Step 6, insert:

```typescript
        {merchants
          .filter((m) => m.activeCount > 0)
          .map((m) => (
            <Polyline
              key={`inbound-${m.merchant}`}
              positions={[m.position, HUB]}
              pathOptions={{ color: MERCHANT_COLOR, weight: 1.5, opacity: 0.35, dashArray: "6 8" }}
            />
          ))}

        {merchants.map((m) => (
          <Marker key={`merch-${m.merchant}`} position={m.position} icon={merchantIcon()}>
            <Popup>
              <strong>{m.merchant}</strong>
              <br />
              {m.activeCount} active order{m.activeCount === 1 ? "" : "s"}
            </Popup>
          </Marker>
        ))}
```

- [ ] **Step 8: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: PASS — no type errors, build succeeds.

- [ ] **Step 9: Visual verification**

Run the app (`cd frontend && npm run dev`, backend seeded) and confirm on the dashboard map:
- Pending markers are **blue**, out-for-delivery markers are **green**.
- Last-mile routes are **cyan arcs with flowing dots** (amber if a driver is at-risk).
- **Violet warehouse icons** appear at merchant origins; a **violet dashed line** runs from each merchant with active orders to the hub.
- Legend shows the **Merchant origin** entry.

- [ ] **Step 10: Commit**

```bash
git add frontend/components/CommandMap.tsx frontend/app/globals.css
git commit -m "feat(map): three-layer redesign — status colors, merchant origins, animated arcs"
```

---

## Self-Review Notes

- **Spec coverage:** colors (Task 6 S2), three layers (Tasks 6), last-mile arc+animation (Tasks 5, 6 S1/S6), inbound Option A active-only (Task 6 S7), merchant nodes + divergence guard (Task 4), backend payload (Task 1), legend (Task 6 S2). Street routing intentionally absent (non-goal).
- **Type consistency:** `MerchantNode` fields (`merchant`, `position`, `activeCount`, `coordsDiverge`) used identically in Task 4 impl and Task 6 consumer; `LatLng` reused from `insights.ts`; `MapPoint` merchant fields match across Task 1 (py), Task 3 (ts), Task 4 (tests).
- **Reused, not duplicated:** `ACTIVE` set (insights.ts:8) drives `activeCount`; `HUB` reused for bounds + inbound lines.
