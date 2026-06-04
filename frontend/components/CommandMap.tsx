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
