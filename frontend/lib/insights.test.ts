import { describe, expect, it } from "vitest";
import { arcPath, buildMerchantNodes, type LatLng } from "@/lib/insights";
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
