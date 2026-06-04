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
