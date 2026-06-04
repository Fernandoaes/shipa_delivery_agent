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
