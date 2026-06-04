"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { OrderListItem } from "@/lib/types";

const AT_RISK = new Set(["failed", "returned"]);

export default function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  const { get, set } = useTableFilters();
  const riskOnly = get("risk") === "1";
  const rows = useMemo(
    () =>
      applyFilters(orders, {
        query: get("q"),
        textFields: ["twin_order_ref", "customer_name", "merchant"],
        equals: { status: get("status"), delivery_area: get("area"), merchant: get("merchant"), assigned_driver: get("driver") },
        predicate: riskOnly ? (o) => AT_RISK.has(o.status) : undefined,
      }),
    [orders, get, riskOnly],
  );

  return (
    <div>
      {riskOnly && (
        <div className="mb-4 flex items-center gap-3">
          <h2 className="text-lg font-semibold text-bad">At-risk orders</h2>
          <span className="font-mono text-sm text-txt-dim">{rows.length} failed / returned</span>
          <button onClick={() => set("risk", "")} className="text-xs text-shipa-blue hover:underline">
            clear
          </button>
        </div>
      )}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Order, customer, merchant…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(orders, "status")} allLabel="All statuses" />
        <FilterSelect value={get("area")} onChange={(v) => set("area", v)} options={optionsFor(orders, "delivery_area")} allLabel="All areas" />
        <FilterSelect value={get("merchant")} onChange={(v) => set("merchant", v)} options={optionsFor(orders, "merchant")} allLabel="All merchants" />
        <FilterSelect value={get("driver")} onChange={(v) => set("driver", v)} options={optionsFor(orders, "assigned_driver")} allLabel="All drivers" />
        <span className="text-sm text-txt-dim">{rows.length} of {orders.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Customer</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Issue</th>
              <th className="px-4 py-3 font-semibold">Area</th>
              <th className="px-4 py-3 font-semibold">Driver</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.order_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">{o.twin_order_ref}</Link>
                </td>
                <td className="px-4 py-3">{o.customer_name}</td>
                <td className="px-4 py-3">{o.merchant}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3">
                  {o.issue ? (
                    <span className="text-[#ff8585]">{o.issue}</span>
                  ) : o.attempt_count > 1 ? (
                    <span className="text-warn">Attempt {o.attempt_count}</span>
                  ) : (
                    <span className="text-txt-faint">—</span>
                  )}
                </td>
                <td className="px-4 py-3">{o.delivery_area ?? "—"}</td>
                <td className="px-4 py-3">{o.assigned_driver ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No orders match.</p>}
      </div>
    </div>
  );
}
