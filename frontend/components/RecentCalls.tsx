import type { CallSummary } from "@/lib/types";

export default function RecentCalls({ calls }: { calls: CallSummary[] }) {
  return (
    <div className="rounded-2xl border border-hairline bg-panel">
      <h2 className="border-b border-hairline px-5 py-3 text-sm font-semibold text-txt">Recent calls</h2>
      <table className="w-full text-left text-sm">
        <thead className="font-mono text-[10px] uppercase tracking-widest text-txt-faint">
          <tr>
            <th className="px-4 py-2 font-medium">When</th>
            <th className="px-4 py-2 font-medium">Customer</th>
            <th className="px-4 py-2 font-medium">Intent</th>
            <th className="px-4 py-2 font-medium">Disposition</th>
            <th className="px-4 py-2 font-medium">CSAT</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c) => (
            <tr key={c.call_id} className="border-t border-hairline/60 text-txt">
              <td className="px-4 py-2 text-txt-dim">{new Date(c.started_at).toLocaleString()}</td>
              <td className="px-4 py-2">{c.customer_name ?? "—"}</td>
              <td className="px-4 py-2">{c.intent ?? "—"}</td>
              <td className="px-4 py-2">{c.disposition ?? "—"}</td>
              <td className="px-4 py-2">{c.csat_score ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
