# SHIPA Command Center Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the SHIPA ops dashboard into a dark, map-centric **command center** modeled on the customer reference image — left icon rail, real CARTO-dark Leaflet map as the hero, KPI strip from real data, and a live-orders side panel.

**Architecture:** Next.js 16 App Router. Shell (dark theme tokens + Geist fonts + left `SideRail`) is app-wide. The home route (`/`) is recomposed into a command center: KPI strip → full-bleed `CommandMap` + `LiveOrdersPanel` → charts below. Map stays client-only via `dynamic({ssr:false})`. No backend/API changes — all data comes from existing `getMetrics`/`getInsights`/`getOrders`.

**Tech Stack:** Next 16, React 19, Tailwind v4 (`@theme` in `globals.css`), react-leaflet 5 + CARTO `dark_matter` raster tiles, `next/font/google` (**Jost** = Shipa's brand sans, verified from shipa.com CSS; **Geist Mono** for data/telemetry labels), `lucide-react` (icons, new dep).

**Testing note (flagged):** There is **no frontend unit-test harness** in this repo, and this is visual work. Per-task verification = `npx tsc --noEmit` (type gate) + `next build` where relevant + manual visual check in `next dev`. Adding Playwright/RTL is out of scope for this pass; offer it afterward if the user wants regression coverage.

**Reference image:** dark UAE/Dubai map, left icon rail with SHIPA mark, 4 KPI cards, rounded-square icon markers + faint routes, bottom-left mono "Network Health" overlay, right "Live Orders" panel with LIVE pulse.

**Conventions to respect:** repo `frontend/AGENTS.md` warns this Next.js 16 differs from training data — the font/dynamic APIs in this plan were verified against `node_modules/next/dist/docs/`. Hub constant is `[25.158, 55.236]` (Al Quoz). Comments: single-line why-comments only.

All commands run from `frontend/`. Branch: `feat/command-center-frontend` (already created).

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `app/globals.css` | Dark theme tokens, body, Leaflet dark popup/zoom overrides, scrollbar | Modify |
| `app/layout.tsx` | Wire Geist fonts, swap TopBar→SideRail, dark `main` | Modify |
| `components/SideRail.tsx` | Left vertical icon nav, app-wide | Create |
| `components/icons.tsx` | Shared lucide icon re-exports + map marker SVG strings | Create |
| `components/CommandMap.tsx` | Leaflet dark map: tiles, markers, routes, health overlay | Create |
| `components/CommandMapClient.tsx` | `dynamic({ssr:false})` wrapper for CommandMap | Create |
| `components/KpiStat.tsx` | Dark KPI card with icon + tone (replaces KpiCard usage on home) | Create |
| `lib/insights.ts` | Pure helpers: network-risk derivation, active-order filter, health counts | Create |
| `components/LiveOrdersPanel.tsx` | Right panel: LIVE pulse + active-order list | Create |
| `app/page.tsx` | Command-center composition | Rewrite |
| `components/BarChart.tsx` | Dark restyle | Modify |
| `components/RecentCalls.tsx` | Dark restyle | Modify |
| `components/NeedsAttention.tsx` | Dark restyle | Modify |
| `components/DeliveryMap.tsx` | Dark tiles + icon parity (order-detail map) | Modify |
| `components/MapClient.tsx` | Dark loading state | Modify |
| `components/TopBar.tsx` | Superseded by SideRail | Delete (Task 9) |
| `components/DeliveriesMap.tsx`, `DeliveriesMapClient.tsx` | Superseded by CommandMap | Delete (Task 9) |

---

### Task 1: Dependencies + dark theme tokens + fonts

**Files:**
- Modify: `frontend/package.json` (via install)
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Install icon library**

Run: `npm install lucide-react`
Expected: `lucide-react` added to dependencies, no peer warnings that block (React 19 supported).

- [ ] **Step 2: Replace `app/globals.css` with dark tokens**

```css
@import "tailwindcss";

@theme {
  --color-shipa-blue: #2b3ff2;
  --color-shipa-blue-soft: #3b4ff5;
  --color-ink: #0b0d12;
  --color-panel: #11141b;
  --color-panel-2: #161a22;
  --color-hairline: rgba(255, 255, 255, 0.08);
  --color-txt: #e6e9ef;
  --color-txt-dim: rgba(230, 233, 239, 0.6);
  --color-txt-faint: rgba(230, 233, 239, 0.38);
  --color-ok: #34d399;
  --color-warn: #f59e0b;
  --color-bad: #ef4444;
  --color-muted: #94a3b8;
}

:root {
  color-scheme: dark;
}

body {
  background: var(--color-ink);
  color: var(--color-txt);
  font-family: var(--font-jost), system-ui, sans-serif;
}

/* Jost = Shipa brand sans; Geist Mono = data/telemetry. Tailwind maps these to font-sans/font-mono. */
@theme inline {
  --font-sans: var(--font-jost);
  --font-mono: var(--font-geist-mono);
}

/* Leaflet dark overrides */
.leaflet-container {
  background: #0b0d12 !important;
  font-family: var(--font-geist-mono), monospace;
}
.leaflet-popup-content-wrapper,
.leaflet-popup-tip {
  background: var(--color-panel-2) !important;
  color: var(--color-txt) !important;
  border: 1px solid var(--color-hairline);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}
.leaflet-popup-content a { color: var(--color-shipa-blue-soft); }
.leaflet-bar a {
  background: var(--color-panel-2) !important;
  color: var(--color-txt) !important;
  border-color: var(--color-hairline) !important;
}
.leaflet-bar a:hover { background: var(--color-panel) !important; }
.leaflet-control-attribution {
  background: rgba(11, 13, 18, 0.7) !important;
  color: var(--color-txt-faint) !important;
}
.leaflet-control-attribution a { color: var(--color-txt-dim) !important; }

/* Slim dark scrollbars */
* { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.18) transparent; }
*::-webkit-scrollbar { width: 8px; height: 8px; }
*::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.18); border-radius: 4px; }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
.live-dot { animation: pulse-dot 1.6s ease-in-out infinite; }
```

- [ ] **Step 3: Wire Geist fonts + dark main in `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Jost, Geist_Mono } from "next/font/google";
import AutoRefresh from "@/components/AutoRefresh";
import SideRail from "@/components/SideRail";
import "./globals.css";

// Jost = Shipa's brand typeface (verified from shipa.com). Geist Mono for telemetry/data.
const jost = Jost({ subsets: ["latin"], variable: "--font-jost" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "SHIPA · Command Center",
  description: "Real-time last-mile delivery monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${jost.variable} ${geistMono.variable}`}>
      <body>
        <AutoRefresh />
        <SideRail />
        <main className="min-h-screen pl-16">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Type-check (SideRail not yet created — expect one error)**

Run: `npx tsc --noEmit`
Expected: FAIL only on `Cannot find module '@/components/SideRail'`. This is resolved in Task 2. No other errors.

- [ ] **Step 5: Commit**

```bash
git add app/globals.css app/layout.tsx package.json package-lock.json
git commit -m "feat(fe): dark theme tokens, geist fonts, lucide dep"
```

---

### Task 2: SideRail navigation (app-wide)

**Files:**
- Create: `frontend/components/icons.tsx`
- Create: `frontend/components/SideRail.tsx`

- [ ] **Step 1: Create `components/icons.tsx` (lucide re-exports)**

```tsx
// Single import surface for icons so usage stays consistent across the app.
export {
  LayoutGrid,
  Package,
  Users,
  Phone,
  CalendarClock,
  Search,
  TriangleAlert,
  Activity,
  TrendingUp,
  DollarSign,
  Warehouse,
  Truck,
  MapPin,
} from "lucide-react";
```

- [ ] **Step 2: Create `components/SideRail.tsx`**

```tsx
"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid, Package, Users, Phone, CalendarClock, Search, TriangleAlert,
} from "@/components/icons";

const links = [
  { href: "/", label: "Overview", Icon: LayoutGrid },
  { href: "/orders", label: "Orders", Icon: Package },
  { href: "/customers", label: "Customers", Icon: Users },
  { href: "/calls", label: "Calls", Icon: Phone },
  { href: "/reschedules", label: "Reschedules", Icon: CalendarClock },
  { href: "/investigations", label: "Investigations", Icon: Search },
  { href: "/escalations", label: "Escalations", Icon: TriangleAlert },
];

export default function SideRail() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 z-[1100] flex h-screen w-16 flex-col items-center gap-1 border-r border-hairline bg-panel py-4">
      <Link href="/" className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-shipa-blue" aria-label="SHIPA home">
        <Image src="/shipa-logo.svg" alt="SHIPA" width={22} height={22} priority />
      </Link>
      <nav className="flex flex-1 flex-col items-center gap-1">
        {links.map(({ href, label, Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              aria-label={label}
              className={`group relative grid h-11 w-11 place-items-center rounded-xl transition-colors ${
                active ? "bg-shipa-blue text-white" : "text-txt-dim hover:bg-panel-2 hover:text-txt"
              }`}
            >
              <Icon size={20} strokeWidth={active ? 2.4 : 2} />
              <span className="pointer-events-none absolute left-14 z-50 whitespace-nowrap rounded-md border border-hairline bg-panel-2 px-2 py-1 text-xs text-txt opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS (Task 1's missing-module error now resolved).

- [ ] **Step 4: Manual check**

Run: `npm run dev`, open `http://localhost:3000`. Expected: dark background, left icon rail visible, hovering an icon shows a label tooltip, clicking each icon navigates and highlights the active item in SHIPA blue. (Note: the SHIPA logo svg is dark-on-? — if it disappears on the blue tile, that's fixed in Task 9 polish; acceptable for now.)

- [ ] **Step 5: Commit**

```bash
git add components/icons.tsx components/SideRail.tsx
git commit -m "feat(fe): left icon rail navigation (app-wide)"
```

---

### Task 3: insights helpers (pure logic)

**Files:**
- Create: `frontend/lib/insights.ts`

- [ ] **Step 1: Create `lib/insights.ts`**

```ts
import type { Insights, MapPoint } from "@/lib/types";

export type RiskLevel = "LOW" | "MED" | "HIGH";

// Network risk derived from real operational signals (no fabricated metric).
export function networkRisk(na: Insights["needs_attention"]): RiskLevel {
  if (na.open_escalations > 0 || na.failed_orders >= 2) return "HIGH";
  if (na.failed_orders > 0 || na.pending_reschedules > 0) return "MED";
  return "LOW";
}

const ACTIVE = new Set(["out_for_delivery", "pending"]);

export function activeOrders(points: MapPoint[]): MapPoint[] {
  return points.filter((p) => ACTIVE.has(p.status));
}

// "At risk" = stops that are failed or otherwise off-nominal.
export function healthCounts(points: MapPoint[]) {
  const atRisk = points.filter((p) => p.status === "failed").length;
  return { nominal: points.length - atRisk, atRisk, activeRoutes: points.length };
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add lib/insights.ts
git commit -m "feat(fe): network-risk + health-count helpers"
```

---

### Task 4: CommandMap (the hero)

**Files:**
- Create: `frontend/components/CommandMap.tsx`
- Create: `frontend/components/CommandMapClient.tsx`

- [ ] **Step 1: Create `components/CommandMap.tsx`**

```tsx
"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { MapPoint } from "@/lib/types";
import { healthCounts } from "@/lib/insights";

type LatLng = [number, number];
const HUB: LatLng = [25.158, 55.236]; // Al Quoz fulfilment hub (matches seed origin)

const STATUS_COLOR: Record<string, string> = {
  out_for_delivery: "#3b82f6",
  pending: "#f59e0b",
  failed: "#ef4444",
  rescheduled: "#94a3b8",
};

const LEGEND: [string, string][] = [
  ["Out for delivery", STATUS_COLOR.out_for_delivery],
  ["Pending", STATUS_COLOR.pending],
  ["Failed", STATUS_COLOR.failed],
  ["Rescheduled", STATUS_COLOR.rescheduled],
];

// Rounded-square marker matching the reference; SVG glyph is inlined for divIcon.
const PIN_GLYPH =
  '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9h18v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="m3 9 2-5h14l2 5"/></svg>';

function stopIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:24px;height:24px;border-radius:7px;border:1.5px solid rgba(255,255,255,.85);box-shadow:0 2px 8px rgba(0,0,0,.5),0 0 0 1px ${color}55;display:flex;align-items:center;justify-content:center">${PIN_GLYPH}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });
}

function hubIcon() {
  return L.divIcon({
    className: "",
    html: `<div style="background:#2b3ff2;width:28px;height:28px;border-radius:8px;border:2px solid #fff;box-shadow:0 0 16px #2b3ff2;display:flex;align-items:center;justify-content:center"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35"/><path d="M2 8.35 12 2l10 6.35"/><path d="M6 18h12"/></svg></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 11);
    else if (points.length > 1) map.fitBounds(points, { padding: [60, 60] });
  }, [map, points]);
  return null;
}

export type CommandMapProps = { points: MapPoint[]; height?: string };

export default function CommandMap({ points, height = "68vh" }: CommandMapProps) {
  const router = useRouter();
  const latlngs = points.map((p) => [p.delivery_lat, p.delivery_lng] as LatLng);
  const bounds: LatLng[] = [HUB, ...latlngs];
  const health = healthCounts(points);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-hairline">
      <MapContainer
        center={HUB}
        zoom={11}
        scrollWheelZoom
        touchZoom
        style={{ height, width: "100%", background: "#0b0d12" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />
        {points.map((p) => (
          <Polyline
            key={`r-${p.order_id}`}
            positions={[HUB, [p.delivery_lat, p.delivery_lng]]}
            pathOptions={{ color: "#34d399", weight: 1, opacity: 0.22 }}
          />
        ))}
        {points.map((p) => (
          <Marker
            key={p.order_id}
            position={[p.delivery_lat, p.delivery_lng]}
            icon={stopIcon(STATUS_COLOR[p.status] ?? "#94a3b8")}
            eventHandlers={{ click: () => router.push(`/orders/${p.order_id}`) }}
          >
            <Popup>
              <strong>{p.twin_order_ref}</strong>
              <br />
              {p.delivery_area ?? "—"}
              <br />
              Status: {p.status.replace(/_/g, " ")}
            </Popup>
          </Marker>
        ))}
        <Marker position={HUB} icon={hubIcon()}>
          <Popup>
            <strong>SHIPA hub</strong>
            <br />
            Al Quoz fulfilment
          </Popup>
        </Marker>
        <FitBounds points={bounds} />
      </MapContainer>

      <div className="pointer-events-none absolute bottom-4 left-4 z-[1000] rounded-xl border border-hairline bg-ink/85 px-4 py-3 font-mono text-[11px] text-txt shadow-2xl backdrop-blur">
        <div className="mb-2 uppercase tracking-widest text-txt-faint">Network health</div>
        <div className="flex justify-between gap-6"><span className="text-ok">— Nominal</span><span>{health.nominal}</span></div>
        <div className="flex justify-between gap-6"><span className="text-warn">— At Risk</span><span>{health.atRisk}</span></div>
        <div className="mt-1 border-t border-hairline pt-1 text-txt-dim">ACTIVE_ROUTES: {health.activeRoutes}</div>
      </div>

      <div className="pointer-events-none absolute right-4 top-4 z-[1000] rounded-xl border border-hairline bg-ink/85 px-3 py-2 text-[11px] text-txt-dim shadow-2xl backdrop-blur">
        {LEGEND.map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `components/CommandMapClient.tsx`**

```tsx
"use client";

import dynamic from "next/dynamic";
import type { CommandMapProps } from "@/components/CommandMap";

const CommandMap = dynamic(() => import("@/components/CommandMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center rounded-2xl border border-hairline bg-panel text-txt-dim" style={{ height: "68vh" }}>
      Loading live map…
    </div>
  ),
});

export default function CommandMapClient(props: CommandMapProps) {
  return <CommandMap {...props} />;
}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add components/CommandMap.tsx components/CommandMapClient.tsx
git commit -m "feat(fe): dark CARTO command map with icon markers + health overlay"
```

---

### Task 5: KpiStat + LiveOrdersPanel

**Files:**
- Create: `frontend/components/KpiStat.tsx`
- Create: `frontend/components/LiveOrdersPanel.tsx`

- [ ] **Step 1: Create `components/KpiStat.tsx`**

```tsx
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
  label, value, sub, tone = "neutral", Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  Icon: ComponentType<{ size?: number; className?: string }>;
}) {
  return (
    <div className="flex items-start justify-between rounded-2xl border border-hairline bg-panel p-5">
      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-txt-faint">{label}</div>
        <div className={`mt-2 text-3xl font-semibold ${TONE[tone]}`}>{value}</div>
        {sub && <div className="mt-1 text-xs text-txt-dim">{sub}</div>}
      </div>
      <span className={`grid h-9 w-9 place-items-center rounded-lg ${ICON_TONE[tone]}`}>
        <Icon size={18} />
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Create `components/LiveOrdersPanel.tsx`**

```tsx
import Link from "next/link";
import type { MapPoint } from "@/lib/types";

const DOT: Record<string, string> = {
  out_for_delivery: "bg-[#3b82f6]",
  pending: "bg-warn",
  failed: "bg-bad",
  rescheduled: "bg-muted",
};

export default function LiveOrdersPanel({ points }: { points: MapPoint[] }) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-txt">Live Orders</h2>
          <div className="font-mono text-[10px] uppercase tracking-widest text-txt-faint">Shipa Delivery</div>
        </div>
        <span className="flex items-center gap-1.5 text-[11px] font-medium text-ok">
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-ok" /> LIVE
        </span>
      </div>
      <div className="flex items-center gap-3 border-b border-hairline px-5 py-2 font-mono text-[10px] uppercase tracking-widest text-txt-faint">
        <span className="flex-1">Route</span>
        <span className="w-24">Area</span>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {points.map((p) => (
          <li key={p.order_id}>
            <Link
              href={`/orders/${p.order_id}`}
              className="flex items-center gap-3 border-b border-hairline/60 px-5 py-3 text-sm transition-colors hover:bg-panel-2"
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[p.status] ?? "bg-muted"}`} />
              <span className="flex-1 truncate font-mono text-txt">{p.twin_order_ref}</span>
              <span className="w-24 truncate text-txt-dim">{p.delivery_area ?? "—"}</span>
            </Link>
          </li>
        ))}
        {points.length === 0 && (
          <li className="px-5 py-6 text-center text-sm text-txt-dim">No active orders</li>
        )}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add components/KpiStat.tsx components/LiveOrdersPanel.tsx
git commit -m "feat(fe): dark KPI stat card + live orders panel"
```

---

### Task 6: Dark-restyle shared home components

**Files:**
- Modify: `frontend/components/BarChart.tsx`
- Modify: `frontend/components/RecentCalls.tsx`
- Modify: `frontend/components/NeedsAttention.tsx`

- [ ] **Step 1: Restyle `BarChart.tsx`** (swap light classes for dark tokens)

Replace the outer wrapper and bar/label classes:
- Wrapper `div`: `className="rounded-2xl border border-hairline bg-panel p-5"`
- `h2`: `className="mb-4 text-sm font-semibold text-txt"`
- Vertical label `div`: `className="text-[10px] text-txt-faint"`
- Vertical bar fill: `className="w-full rounded-t bg-shipa-blue"` (keep height style)
- Horizontal label `div`: `className="w-28 truncate text-txt-dim"`
- Horizontal track: `className="h-4 flex-1 rounded bg-panel-2"`
- Horizontal fill: `className="h-4 rounded bg-shipa-blue"` (keep width style)
- Horizontal value: `className="w-8 text-right text-txt-dim"`

Full file:

```tsx
export type Bar = { label: string; value: number };

export default function BarChart({
  title, data, orientation = "vertical",
}: { title: string; data: Bar[]; orientation?: "vertical" | "horizontal" }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="rounded-2xl border border-hairline bg-panel p-5">
      <h2 className="mb-4 text-sm font-semibold text-txt">{title}</h2>
      {orientation === "vertical" ? (
        <div className="flex h-40 items-stretch gap-1">
          {data.map((d) => (
            <div key={d.label} className="flex h-full flex-1 flex-col items-center gap-1" title={`${d.label}: ${d.value}`}>
              <div className="flex w-full flex-1 items-end">
                <div className="w-full rounded-t bg-shipa-blue" style={{ height: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="text-[10px] text-txt-faint">{d.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data.map((d) => (
            <div key={d.label} className="flex items-center gap-2 text-sm">
              <div className="w-28 truncate text-txt-dim" title={d.label}>{d.label}</div>
              <div className="h-4 flex-1 rounded bg-panel-2">
                <div className="h-4 rounded bg-shipa-blue" style={{ width: `${(d.value / max) * 100}%` }} />
              </div>
              <div className="w-8 text-right text-txt-dim">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Restyle `RecentCalls.tsx`**

```tsx
import type { CallSummary } from "@/lib/types";

export default function RecentCalls({ calls }: { calls: CallSummary[] }) {
  return (
    <div className="rounded-2xl border border-hairline bg-panel">
      <h2 className="border-b border-hairline px-5 py-3 text-sm font-semibold text-txt">Recent calls</h2>
      <table className="w-full text-left text-sm">
        <thead className="font-mono text-[10px] uppercase tracking-widest text-txt-faint">
          <tr>
            <th className="px-4 py-2 font-medium">When</th>
            <th className="px-4 py-2 font-medium">Customer</th>
            <th className="px-4 py-2 font-medium">Intent</th>
            <th className="px-4 py-2 font-medium">Disposition</th>
            <th className="px-4 py-2 font-medium">CSAT</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c) => (
            <tr key={c.call_id} className="border-t border-hairline/60 text-txt">
              <td className="px-4 py-2 text-txt-dim">{new Date(c.started_at).toLocaleString()}</td>
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

- [ ] **Step 3: Restyle `NeedsAttention.tsx`**

```tsx
import Link from "next/link";

type Item = { label: string; count: number; href: string; tone: string };

export default function NeedsAttention({
  openEscalations, pendingReschedules, failedOrders,
}: { openEscalations: number; pendingReschedules: number; failedOrders: number }) {
  const items: Item[] = [
    { label: "Open escalations", count: openEscalations, href: "/escalations", tone: "text-bad" },
    { label: "Pending reschedules", count: pendingReschedules, href: "/reschedules", tone: "text-warn" },
    { label: "Failed / returned orders", count: failedOrders, href: "/orders", tone: "text-bad" },
  ];
  return (
    <div className="rounded-2xl border border-hairline bg-panel p-5">
      <h2 className="mb-3 text-sm font-semibold text-txt">Needs attention</h2>
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.label}>
            <Link href={it.href} className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-panel-2">
              <span className="text-sm text-txt-dim">{it.label}</span>
              <span className={`text-lg font-bold ${it.count > 0 ? it.tone : "text-txt-faint"}`}>{it.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add components/BarChart.tsx components/RecentCalls.tsx components/NeedsAttention.tsx
git commit -m "feat(fe): dark restyle bar chart, recent calls, needs attention"
```

---

### Task 7: Command-center home composition

**Files:**
- Rewrite: `frontend/app/page.tsx`

- [ ] **Step 1: Rewrite `app/page.tsx`**

```tsx
import Link from "next/link";
import BarChart from "@/components/BarChart";
import CommandMapClient from "@/components/CommandMapClient";
import KpiStat from "@/components/KpiStat";
import LiveOrdersPanel from "@/components/LiveOrdersPanel";
import NeedsAttention from "@/components/NeedsAttention";
import RecentCalls from "@/components/RecentCalls";
import { Activity, Package, TrendingUp, TriangleAlert } from "@/components/icons";
import { getCalls, getInsights, getMetrics } from "@/lib/api";
import { activeOrders, networkRisk } from "@/lib/insights";

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

const RANGES: { label: string; days: number }[] = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
];

const RISK_TONE = { LOW: "ok", MED: "warn", HIGH: "bad" } as const;

export default async function CommandCenter({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const { range } = await searchParams;
  const selected = RANGES.find((r) => r.label === range) ?? RANGES[1];
  const [metrics, insights, calls] = await Promise.all([
    getMetrics(),
    getInsights(selected.days),
    getCalls(),
  ]);

  const active = activeOrders(insights.map_points);
  const risk = networkRisk(insights.needs_attention);
  const callsPerDay = insights.calls_per_day.map((d) => ({
    label: String(Number(d.date.slice(8, 10))),
    value: d.count,
  }));
  const intentMix = insights.intent_mix.map((d) => ({ label: d.intent, value: d.count }));

  return (
    <div className="space-y-6 px-6 py-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-txt">Shipa Delivery</h1>
          <div className="font-mono text-xs uppercase tracking-[0.3em] text-txt-faint">Real-time monitoring</div>
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
        <KpiStat label="Service Level" value={pct(metrics.first_attempt_rate)} sub="first-attempt" tone="ok" Icon={Activity} />
        <KpiStat label="Active Orders" value={active.length.toString()} sub="out for delivery" Icon={Package} />
        <KpiStat label="Deflection" value={pct(metrics.deflection_rate)} sub="self-served" Icon={TrendingUp} />
        <KpiStat label="Network Risk" value={risk} tone={RISK_TONE[risk]} Icon={TriangleAlert} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <CommandMapClient points={insights.map_points} />
        <div className="h-[68vh]">
          <LiveOrdersPanel points={active} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title={`Calls per day (${selected.label})`} data={callsPerDay} />
        <BarChart title={`Intent mix (${selected.label})`} data={intentMix} orientation="horizontal" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1">
          <NeedsAttention
            openEscalations={insights.needs_attention.open_escalations}
            pendingReschedules={insights.needs_attention.pending_reschedules}
            failedOrders={insights.needs_attention.failed_orders}
          />
        </div>
        <div className="md:col-span-2"><RecentCalls calls={calls.slice(0, 10)} /></div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check + build**

Run: `npx tsc --noEmit && npm run build`
Expected: PASS. (Build compiles all routes; confirms no SSR/Leaflet leakage since map is dynamic ssr:false.)

- [ ] **Step 3: Manual check**

Run: `npm run dev`. Expected at `/`: header, 4 KPI cards (Network Risk colored by level), dark map with hub + status markers + faint routes + Network Health overlay + legend, right Live Orders panel with LIVE pulse and clickable rows, charts + needs-attention + recent calls below. Pinch/scroll zoom + +/- buttons work. Clicking a map marker or a Live Orders row opens `/orders/{id}`.

- [ ] **Step 4: Commit**

```bash
git add app/page.tsx
git commit -m "feat(fe): command-center home composition"
```

---

### Task 8: Order-detail map parity (dark)

**Files:**
- Modify: `frontend/components/DeliveryMap.tsx`
- Modify: `frontend/components/MapClient.tsx`

- [ ] **Step 1: Read current `DeliveryMap.tsx`**

Run: `sed -n '1,60p' components/DeliveryMap.tsx` (to see exact tile URL + marker code before editing).

- [ ] **Step 2: Switch its TileLayer to CARTO dark**

In `components/DeliveryMap.tsx`, change the tile `url` from the `light_all` CARTO URL to:
`url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"`
and set the `MapContainer` `style` background to `#0b0d12`. Keep existing markers/logic. (If markers use a hardcoded light color that vanishes on dark, give the delivery marker `#3b82f6` and merchant marker `#2b3ff2`.)

- [ ] **Step 3: Dark loading state in `MapClient.tsx`**

Replace the `loading` div className with:
`className="flex h-[420px] items-center justify-center rounded-2xl border border-hairline bg-panel text-txt-dim"`

- [ ] **Step 4: Type-check**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Manual check**

Open an order detail page (`/orders/<id>`). Expected: map is dark and consistent with the command center.

- [ ] **Step 6: Commit**

```bash
git add components/DeliveryMap.tsx components/MapClient.tsx
git commit -m "feat(fe): dark map on order detail for parity"
```

---

### Task 9: Cleanup, dead-code removal, final verification

**Files:**
- Delete: `frontend/components/TopBar.tsx`
- Delete: `frontend/components/DeliveriesMap.tsx`, `frontend/components/DeliveriesMapClient.tsx`

- [ ] **Step 1: Confirm nothing imports the doomed files**

Run: `grep -rn "TopBar\|DeliveriesMap" app components --include="*.tsx"`
Expected: no matches outside the files themselves. (`page.tsx` now uses `CommandMapClient`; `layout.tsx` now uses `SideRail`.) If any match remains, fix the importer before deleting.

- [ ] **Step 2: Delete superseded files**

```bash
git rm components/TopBar.tsx components/DeliveriesMap.tsx components/DeliveriesMapClient.tsx
```

- [ ] **Step 3: Verify SHIPA logo visibility on the blue rail tile**

Run: `cat public/shipa-logo.svg` — if the logo paths are dark (would disappear on the blue tile), the rail tile in `SideRail.tsx` already provides a blue background; confirm contrast in the browser. If invisible, set the logo container to `bg-white` instead of `bg-shipa-blue` in `SideRail.tsx`. (Decide visually.)

- [ ] **Step 4: Full gate**

Run: `npx tsc --noEmit && npm run lint && npm run build`
Expected: all PASS, no type errors, no lint errors, build succeeds for all routes.

- [ ] **Step 5: Manual smoke across routes**

Run `npm run dev`; visit `/`, `/orders`, `/customers`, `/calls`, `/reschedules`, `/investigations`, `/escalations`, one order detail, one customer detail. Expected: rail present and navigable everywhere; home is the command center; no console errors; map interactions work.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore(fe): remove superseded TopBar + DeliveriesMap; final polish"
```

---

## Self-Review

**Spec coverage:**
- Left rail app-wide → Task 2. ✓
- Dark theme tokens + Geist fonts → Task 1. ✓
- CARTO dark real map, pinch+button zoom, custom icon markers, click→order, Network Health overlay → Task 4. ✓
- KPIs from real signals incl. derived Network Risk → Tasks 3 (logic) + 5 (card) + 7 (wiring). ✓
- Live Orders panel with LIVE pulse → Task 5 + 7. ✓
- Charts/needs-attention/recent-calls retained, dark → Task 6 + 7. ✓
- Order-detail map parity → Task 8. ✓
- Cleanup of superseded components → Task 9. ✓
- "Clean & professional map" (muted basemap, ≤0.25 route opacity, non-interactive overlays, fitBounds padding) → encoded in Task 4 code. ✓
- Out of scope honored: no backend change, no Mapbox, no choropleth, no fabricated revenue, inner pages not individually reworked. ✓

**Placeholder scan:** No TBD/TODO; every code step has complete code; commands have expected output. ✓

**Type consistency:** `CommandMapProps` exported from `CommandMap.tsx` and imported by `CommandMapClient.tsx`. `MapPoint` used consistently from `@/lib/types`. `networkRisk`/`activeOrders`/`healthCounts` defined in `lib/insights.ts` (Task 3) before use in Tasks 4/7. `RiskLevel` keys (`LOW`/`MED`/`HIGH`) match `RISK_TONE` map in `page.tsx`. `KpiStat` `tone` union (`neutral|ok|warn|bad`) matches `RISK_TONE` values. `Icon` prop is a component; `@/components/icons` re-exports the lucide icons used. ✓

**Known residual (flagged, accepted for this pass):** inner-page tables (`OrdersTable`, `CallsTable`, detail pages) still use light card classes → they render as light cards on the dark canvas. Functional and readable; full dark rework deferred to the "assess" phase per scope decision.
