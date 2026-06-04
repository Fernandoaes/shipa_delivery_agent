"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { InvestigationSummary } from "@/lib/types";

// ISO string of the page render time, passed from the server component so that
// the client filter predicate never calls Date.now() during render.
export default function InvestigationsTable({ rows: data, renderTime }: { rows: InvestigationSummary[]; renderTime: string }) {
  const { get, set } = useTableFilters();
  const overdue = get("overdue") === "1";
  const rows = useMemo(
    () =>
      applyFilters(data, {
        query: get("q"),
        textFields: ["twin_order_ref"],
        equals: { status: get("status"), type: get("type") },
        // ISO string comparison works because both are ISO 8601 — lexicographic
        // order matches chronological order for dates without timezone mixing.
        predicate: overdue
          ? (r) => r.status === "open" && !!r.callback_due_at && r.callback_due_at < renderTime
          : undefined,
      }),
    [data, get, overdue, renderTime],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Order ref…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(data, "status")} allLabel="All statuses" />
        <FilterSelect value={get("type")} onChange={(v) => set("type", v)} options={optionsFor(data, "type")} allLabel="All types" />
        <label className="flex items-center gap-2 text-sm text-txt-dim">
          <input type="checkbox" checked={overdue} onChange={(e) => set("overdue", e.target.checked ? "1" : "")} />
          Overdue only
        </label>
        <span className="text-sm text-txt-dim">{rows.length} of {data.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Type</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Callback due</th>
              <th className="px-4 py-3 font-semibold">Opened</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.investigation_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/orders/${r.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {r.twin_order_ref ?? r.order_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3">{r.type}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">{r.callback_due_at ? new Date(r.callback_due_at).toLocaleString() : "—"}</td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.opened_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No investigations match.</p>}
      </div>
    </div>
  );
}
