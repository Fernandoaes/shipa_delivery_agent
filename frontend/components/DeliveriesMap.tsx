"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { MapPoint } from "@/lib/types";

type LatLng = [number, number];

const STATUS_COLOR: Record<string, string> = {
  out_for_delivery: "#3b82f6",
  pending: "#f59e0b",
  failed: "#ef4444",
  rescheduled: "#94a3b8",
};

// Fixed SHIPA fulfilment hub (Al Quoz) — matches the seed origin.
const HUB: LatLng = [25.158, 55.236];

const LEGEND: [string, string][] = [
  ["Out for delivery", STATUS_COLOR.out_for_delivery],
  ["Pending", STATUS_COLOR.pending],
  ["Failed", STATUS_COLOR.failed],
  ["Rescheduled", STATUS_COLOR.rescheduled],
];

function pin(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:16px;height:16px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid #0b0d12;box-shadow:0 0 8px ${color}aa"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 16],
    popupAnchor: [0, -16],
  });
}

function hubIcon() {
  return L.divIcon({
    className: "",
    html: `<div style="background:#6366f1;width:22px;height:22px;border-radius:6px;border:2px solid white;box-shadow:0 0 10px #6366f1;display:flex;align-items:center;justify-content:center;color:white;font-size:13px;line-height:1">▦</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -12],
  });
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) map.fitBounds(points, { padding: [50, 50] });
  }, [map, points]);
  return null;
}

export type DeliveriesMapProps = { points: MapPoint[] };

export default function DeliveriesMap({ points }: DeliveriesMapProps) {
  const latlngs = points.map((p) => [p.delivery_lat, p.delivery_lng] as LatLng);
  const bounds: LatLng[] = [HUB, ...latlngs];
  return (
    <div className="relative">
      <MapContainer center={HUB} zoom={11} scrollWheelZoom={false}
        style={{ height: "460px", width: "100%", borderRadius: "0.75rem" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />
        {points.map((p) => (
          <Polyline key={`r-${p.order_id}`} positions={[HUB, [p.delivery_lat, p.delivery_lng]]}
            pathOptions={{ color: "#34d399", weight: 1, opacity: 0.22 }} />
        ))}
        {points.map((p) => (
          <Marker key={p.order_id} position={[p.delivery_lat, p.delivery_lng]}
            icon={pin(STATUS_COLOR[p.status] ?? "#94a3b8")}>
            <Popup>
              <strong>{p.twin_order_ref}</strong><br />
              {p.delivery_area ?? "—"}<br />
              Status: {p.status.replace(/_/g, " ")}<br />
              <a href={`/orders/${p.order_id}`}>Open order →</a>
            </Popup>
          </Marker>
        ))}
        <Marker position={HUB} icon={hubIcon()}>
          <Popup><strong>SHIPA hub</strong><br />Al Quoz fulfilment</Popup>
        </Marker>
        <FitBounds points={bounds} />
      </MapContainer>
      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-lg border border-white/10 bg-shipa-ink/80 px-3 py-2 text-[11px] text-white/80 shadow-lg">
        <div className="mb-1 font-mono uppercase tracking-wide text-white/50">Network health</div>
        {LEGEND.map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
