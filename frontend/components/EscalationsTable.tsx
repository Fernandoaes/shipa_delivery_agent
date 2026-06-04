"use client";

import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import StatusBadge from "@/components/StatusBadge";
import type { EscalationSummary } from "@/lib/types";

export default function EscalationsTable({ rows: data }: { rows: EscalationSummary[] }) {
  const { get, set } = useTableFilters();
  const rows = useMemo(
    () =>
      applyFilters(data, {
        query: get("q"),
        textFields: ["category", "reason"],
        equals: { status: get("status"), category: get("category") },
      }),
    [data, get],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Category or reason…" />
        <FilterSelect value={get("status")} onChange={(v) => set("status", v)} options={optionsFor(data, "status")} allLabel="All statuses" />
        <FilterSelect value={get("category")} onChange={(v) => set("category", v)} options={optionsFor(data, "category")} allLabel="All categories" />
        <span className="text-sm text-txt-dim">{rows.length} of {data.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.escalation_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">{r.category}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No escalations match.</p>}
      </div>
    </div>
  );
}
