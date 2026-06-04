import type { MapPoint, OrderListItem } from "@/lib/types";

export type LatLng = [number, number];

// Al Quoz fulfilment hub (matches seed origin) — shared across map + routing helpers.
export const HUB: LatLng = [25.158, 55.236];

const ACTIVE = new Set(["out_for_delivery", "pending"]);

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
