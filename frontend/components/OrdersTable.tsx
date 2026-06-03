"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import type { OrderListItem } from "@/lib/types";

export default function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  const [status, setStatus] = useState("");
  const statuses = useMemo(() => Array.from(new Set(orders.map((o) => o.status))).sort(), [orders]);
  const rows = status ? orders.filter((o) => o.status === status) : orders;
  const failed = orders.filter((o) => o.status === "failed" || o.status === "returned").length;

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-shipa-sky-accent px-3 py-2 text-sm">
          <option value="">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
        <span className="text-sm text-shipa-ink/60">{orders.length} orders · {failed} failed/returned</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Customer</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Area</th>
              <th className="px-4 py-3 font-semibold">Driver</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.order_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">{o.twin_order_ref}</Link>
                </td>
                <td className="px-4 py-3">{o.customer_name}</td>
                <td className="px-4 py-3">{o.merchant}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3">{o.delivery_area ?? "—"}</td>
                <td className="px-4 py-3">{o.assigned_driver ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
