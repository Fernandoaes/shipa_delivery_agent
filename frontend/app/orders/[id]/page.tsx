import BackButton from "@/components/BackButton";
import MapClient from "@/components/MapClient";
import StatusBadge from "@/components/StatusBadge";
import { getOrder } from "@/lib/api";

type LatLng = [number, number];

function pair(lat: number | null, lng: number | null): LatLng | null {
  return lat != null && lng != null ? [lat, lng] : null;
}

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const o = await getOrder(id);
  const rows: [string, string][] = [
    ["Merchant", o.merchant],
    ["Delivery address", o.delivery_address],
    ["Area", o.delivery_area ?? "—"],
    ["Window", o.delivery_window ?? "—"],
    ["Driver", o.assigned_driver ?? "—"],
    ["Pieces", o.expected_pieces?.toString() ?? "—"],
    ["Customer", `${o.customer.full_name} · ${o.customer.primary_phone}`],
  ];
  return (
    <div className="px-8 py-8">
      <BackButton href="/orders" label="Orders" />
      <div className="mb-6 mt-3 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-txt">{o.twin_order_ref}</h1>
        <StatusBadge status={o.status} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-hairline bg-panel p-5">
          <dl className="divide-y divide-hairline">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
                <dt className="text-txt-dim">{k}</dt>
                <dd className="text-right font-medium text-txt">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
        <MapClient
          merchant={o.merchant}
          deliveryAddress={o.delivery_address}
          status={o.status}
          merchantLatLng={pair(o.merchant_lat, o.merchant_lng)}
          deliveryLatLng={pair(o.delivery_lat, o.delivery_lng)}
        />
      </div>
    </div>
  );
}
