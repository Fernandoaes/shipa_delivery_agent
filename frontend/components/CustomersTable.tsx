"use client";

import Link from "next/link";
import { useMemo } from "react";
import FilterSelect from "@/components/filters/FilterSelect";
import SearchInput from "@/components/filters/SearchInput";
import { applyFilters, optionsFor, useTableFilters } from "@/components/filters/useTableFilters";
import type { CustomerListItem } from "@/lib/types";

export default function CustomersTable({ customers }: { customers: CustomerListItem[] }) {
  const { get, set } = useTableFilters();
  const rows = useMemo(() => {
    const filtered = applyFilters(customers, {
      query: get("q"),
      textFields: ["full_name", "primary_phone"],
      equals: { language_pref: get("lang") },
    });
    return get("sort") === "orders"
      ? [...filtered].sort((a, b) => b.order_count - a.order_count)
      : filtered;
  }, [customers, get]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={get("q")} onChange={(v) => set("q", v)} placeholder="Name or phone…" />
        <FilterSelect value={get("lang")} onChange={(v) => set("lang", v)} options={optionsFor(customers, "language_pref")} allLabel="All languages" />
        <FilterSelect value={get("sort")} onChange={(v) => set("sort", v)} options={["orders"]} allLabel="Default order" />
        <span className="text-sm text-txt-dim">{rows.length} of {customers.length}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Phone</th>
              <th className="px-4 py-3 font-semibold">Language</th>
              <th className="px-4 py-3 font-semibold">Orders</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.customer_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/customers/${c.customer_id}`} className="font-medium text-shipa-blue hover:underline">{c.full_name}</Link>
                </td>
                <td className="px-4 py-3">{c.primary_phone}</td>
                <td className="px-4 py-3">{c.language_pref ?? "—"}</td>
                <td className="px-4 py-3">{c.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No customers match.</p>}
      </div>
    </div>
  );
}
