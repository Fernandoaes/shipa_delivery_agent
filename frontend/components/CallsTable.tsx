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
          <aside className="h-full w-[34rem] max-w-[90vw] overflow-y-auto border-l border-hairline bg-panel shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between border-b border-hairline px-6 py-5">
              <div>
                <p className="text-xs uppercase tracking-wide text-txt-faint">Call detail</p>
                <h2 className="mt-1 text-xl font-bold text-txt">{selected.customer_name ?? "Unknown caller"}</h2>
                <p className="mt-1 text-sm text-txt-dim">
                  {new Date(selected.started_at).toLocaleString()} · {selected.direction}
                </p>
              </div>
              <button onClick={() => setSelected(null)} className="text-lg text-txt-faint hover:text-txt">✕</button>
            </div>

            <div className="space-y-6 px-6 py-5">
              <Section title="Call">
                <Fact label="Intent" value={selected.intent ?? "—"} />
                <Fact label="Disposition">
                  {selected.disposition ? <StatusBadge status={selected.disposition} /> : "—"}
                </Fact>
                <Fact label="Verification">
                  <StatusBadge status={selected.verification_status} />
                </Fact>
                <Fact label="CSAT" value={selected.csat_score?.toString() ?? "—"} />
                <Fact label="Language" value={selected.language ?? "—"} />
                <Fact label="Caller" value={selected.caller_number ?? "—"} />
                <Fact label="Ended" value={selected.ended_at ? new Date(selected.ended_at).toLocaleString() : "—"} />
              </Section>

              {selected.reschedule && (
                <Section title="Reschedule" accent>
                  <Fact label="Requested" value={new Date(selected.reschedule.requested_date).toLocaleDateString()} />
                  <Fact label="Window" value={selected.reschedule.requested_window ?? "—"} />
                  <Fact label="Reason" value={selected.reschedule.reason ?? "—"} />
                  <Fact label="Status">
                    <StatusBadge status={selected.reschedule.status} />
                  </Fact>
                  <Fact
                    label="Synced to Twin"
                    value={selected.reschedule.synced_to_twin_at ? new Date(selected.reschedule.synced_to_twin_at).toLocaleString() : "pending"}
                  />
                </Section>
              )}

              {selected.notes && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-txt-faint">Notes</p>
                  <p className="whitespace-pre-wrap rounded-lg border border-hairline bg-panel-2 p-3 text-sm leading-relaxed text-txt">
                    {selected.notes}
                  </p>
                </div>
              )}

              {selected.order_id && (
                <Link href={`/orders/${selected.order_id}`} className="inline-block text-sm font-medium text-shipa-blue hover:underline">
                  Order {selected.twin_order_ref ?? "detail"} →
                </Link>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function Section({ title, accent, children }: { title: string; accent?: boolean; children: React.ReactNode }) {
  return (
    <div className={accent ? "rounded-lg border-l-2 border-warn bg-panel-2 p-4" : ""}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-txt-faint">{title}</p>
      <dl className="divide-y divide-hairline text-sm">{children}</dl>
    </div>
  );
}

function Fact({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-txt-dim">{label}</dt>
      <dd className="text-right font-medium text-txt">{children ?? value}</dd>
    </div>
  );
}
