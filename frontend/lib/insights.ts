import type { Insights, MapPoint, OrderListItem } from "@/lib/types";

export type LatLng = [number, number];

// Al Quoz fulfilment hub (matches seed origin) — shared across map + routing helpers.
export const HUB: LatLng = [25.158, 55.236];

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

export type DriverRoute = {
  driver: string;
  position: LatLng; // representative en-route position (derived, not live GPS)
  path: LatLng[]; // hub → ordered stops
  atRisk: boolean;
};

function dist(a: LatLng, b: LatLng) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

// Order stops as a simple nearest-neighbour route starting from the hub.
function nearestNeighbourPath(stops: LatLng[]): LatLng[] {
  const remaining = [...stops];
  const path: LatLng[] = [HUB];
  let cur = HUB;
  while (remaining.length) {
    let bi = 0;
    for (let i = 1; i < remaining.length; i++) {
      if (dist(cur, remaining[i]) < dist(cur, remaining[bi])) bi = i;
    }
    cur = remaining.splice(bi, 1)[0];
    path.push(cur);
  }
  return path;
}

// Synthesize per-driver routes by joining active stops (coords) to their assigned driver.
// Positions are representative (partway to the first stop), not live telemetry.
export function buildDriverRoutes(orders: OrderListItem[], points: MapPoint[]): DriverRoute[] {
  const driverByOrder = new Map(orders.map((o) => [o.order_id, o.assigned_driver]));
  const groups = new Map<string, MapPoint[]>();
  for (const p of points) {
    const driver = driverByOrder.get(p.order_id);
    if (!driver) continue;
    const g = groups.get(driver);
    if (g) g.push(p);
    else groups.set(driver, [p]);
  }

  const routes: DriverRoute[] = [];
  for (const [driver, pts] of groups) {
    const stops = pts.map((p) => [p.delivery_lat, p.delivery_lng] as LatLng);
    const path = nearestNeighbourPath(stops);
    const firstStop = path[1] ?? HUB;
    const position: LatLng = [
      HUB[0] + (firstStop[0] - HUB[0]) * 0.45,
      HUB[1] + (firstStop[1] - HUB[1]) * 0.45,
    ];
    routes.push({ driver, position, path, atRisk: pts.some((p) => p.status === "failed") });
  }
  return routes;
}
