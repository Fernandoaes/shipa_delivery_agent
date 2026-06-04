"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { MapPoint } from "@/lib/types";
import { HUB, healthCounts, buildMerchantNodes, arcPath, type DriverRoute, type LatLng } from "@/lib/insights";

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

// Customer/recipient marker — person glyph in status colour.
const PERSON_GLYPH =
  '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.5"/><path d="M6 20v-1a6 6 0 0 1 12 0v1"/></svg>';

const TRUCK_GLYPH =
  '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="white" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M14 17V6a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h1"/><path d="M14 9h4l4 4v3a1 1 0 0 1-1 1h-1"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></svg>';

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

function stopIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:24px;height:24px;border-radius:7px;border:1.5px solid rgba(255,255,255,.85);box-shadow:0 2px 8px rgba(0,0,0,.5),0 0 0 1px ${color}55;display:flex;align-items:center;justify-content:center">${PERSON_GLYPH}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });
}

function driverIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:26px;height:26px;border-radius:50%;border:2px solid #fff;box-shadow:0 2px 10px ${color}aa;display:flex;align-items:center;justify-content:center">${TRUCK_GLYPH}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
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

export type CommandMapProps = { points: MapPoint[]; drivers?: DriverRoute[]; height?: string };

export default function CommandMap({ points, drivers = [], height = "68vh" }: CommandMapProps) {
  const router = useRouter();
  const latlngs = points.map((p) => [p.delivery_lat, p.delivery_lng] as LatLng);
  const merchants = buildMerchantNodes(points);
  const bounds: LatLng[] = [HUB, ...latlngs, ...merchants.map((m) => m.position)];
  const health = healthCounts(points);

  return (
    <div className="relative isolate overflow-hidden rounded-2xl border border-hairline">
      <MapContainer
        center={HUB}
        zoom={11}
        scrollWheelZoom
        touchZoom
        style={{ height, width: "100%", background: "#0b0d12" }}
      >
        <TileLayer
          className="cc-tiles"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />

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

        {drivers.map((d) => (
          <Marker key={`drv-${d.driver}`} position={d.position} icon={driverIcon(d.atRisk ? "#f59e0b" : "#22d3ee")}>
            <Popup>
              <strong>{d.driver}</strong>
              <br />
              {d.path.length - 1} stop{d.path.length - 1 === 1 ? "" : "s"} on route
              <br />
              {d.atRisk ? "⚠ at risk" : "on schedule"}
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
