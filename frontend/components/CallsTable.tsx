"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import type { CallSummary } from "@/lib/types";

export default function CallsTable({ calls }: { calls: CallSummary[] }) {
  const [q, setQ] = useState("");
  const [intent, setIntent] = useState("");
  const [selected, setSelected] = useState<CallSummary | null>(null);

  const intents = useMemo(
    () => Array.from(new Set(calls.map((c) => c.intent).filter(Boolean))) as string[],
    [calls],
  );

  const rows = calls.filter((c) => {
    const hay = `${c.customer_name ?? ""} ${c.twin_order_ref ?? ""} ${c.disposition ?? ""}`.toLowerCase();
    return (!q || hay.includes(q.toLowerCase())) && (!intent || c.intent === intent);
  });

  return (
    <div className="relative">
      <div className="mb-4 flex gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search customer / order / disposition"
          className="w-72 rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt placeholder:text-txt-faint" />
        <select value={intent} onChange={(e) => setIntent(e.target.value)}
          className="rounded-lg border border-hairline bg-panel-2 px-3 py-2 text-sm text-txt">
          <option value="">All intents</option>
          {intents.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">When</th>
              <th className="px-4 py-3 font-semibold">Customer</th>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Intent</th>
              <th className="px-4 py-3 font-semibold">Disposition</th>
              <th className="px-4 py-3 font-semibold">Verified</th>
              <th className="px-4 py-3 font-semibold">CSAT</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.call_id} onClick={() => setSelected(c)}
                className="cursor-pointer border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3 text-txt-dim">{new Date(c.started_at).toLocaleString()}</td>
                <td className="px-4 py-3">{c.customer_name ?? "—"}</td>
                <td className="px-4 py-3">{c.twin_order_ref ?? "—"}</td>
                <td className="px-4 py-3">{c.intent ?? "—"}</td>
                <td className="px-4 py-3">{c.disposition ?? "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={c.verification_status} /></td>
                <td className="px-4 py-3">{c.csat_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No calls match.</p>}
      </div>

      {selected && (
        <div className="fixed inset-0 z-20 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelected(null)}>
          <aside className="h-full w-96 overflow-y-auto border-l border-hairline bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-txt">Call detail</h2>
              <button onClick={() => setSelected(null)} className="text-txt-faint hover:text-txt">✕</button>
            </div>
            <dl className="divide-y divide-hairline text-sm">
              {([
                ["When", new Date(selected.started_at).toLocaleString()],
                ["Ended", selected.ended_at ? new Date(selected.ended_at).toLocaleString() : "—"],
                ["Customer", selected.customer_name ?? "—"],
                ["Direction", selected.direction],
                ["Language", selected.language ?? "—"],
                ["Verification", selected.verification_status],
                ["Intent", selected.intent ?? "—"],
                ["Disposition", selected.disposition ?? "—"],
                ["CSAT", selected.csat_score?.toString() ?? "—"],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2.5">
                  <dt className="text-txt-dim">{k}</dt>
                  <dd className="text-right font-medium text-txt">{v}</dd>
                </div>
              ))}
            </dl>
            {selected.order_id && (
              <Link href={`/orders/${selected.order_id}`} className="mt-4 inline-block text-sm text-shipa-blue hover:underline">
                Order {selected.twin_order_ref ?? "detail"} →
              </Link>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
