"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";

type LatLng = [number, number];

function pin(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:18px;height:18px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 18],
    popupAnchor: [0, -18],
  });
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) {
      map.setView(points[0], 13);
    } else if (points.length > 1) {
      map.fitBounds(points, { padding: [60, 60] });
    }
  }, [map, points]);
  return null;
}

export type DeliveryMapProps = {
  merchant: string;
  deliveryAddress: string;
  status: string;
  merchantLatLng: LatLng | null;
  deliveryLatLng: LatLng | null;
};

export default function DeliveryMap({
  merchant,
  deliveryAddress,
  status,
  merchantLatLng,
  deliveryLatLng,
}: DeliveryMapProps) {
  const points = [merchantLatLng, deliveryLatLng].filter(Boolean) as LatLng[];
  if (points.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-shipa-sky-accent bg-shipa-sky text-shipa-ink/60">
        Coordinates unavailable for this order.
      </div>
    );
  }
  return (
    <MapContainer
      center={points[0]}
      zoom={12}
      scrollWheelZoom={false}
      style={{ height: "420px", width: "100%", borderRadius: "0.75rem" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
      />
      {merchantLatLng && (
        <Marker position={merchantLatLng} icon={pin("#0b0d12")}>
          <Popup>
            <strong>{merchant}</strong>
            <br />
            Merchant origin
          </Popup>
        </Marker>
      )}
      {deliveryLatLng && (
        <Marker position={deliveryLatLng} icon={pin("#2b3ff2")}>
          <Popup>
            <strong>Delivery</strong>
            <br />
            {deliveryAddress}
            <br />
            Status: {status.replace(/_/g, " ")}
          </Popup>
        </Marker>
      )}
      {merchantLatLng && deliveryLatLng && (
        <Polyline positions={[merchantLatLng, deliveryLatLng]} pathOptions={{ color: "#2b3ff2", weight: 3, dashArray: "6 8" }} />
      )}
      <FitBounds points={points} />
    </MapContainer>
  );
}
