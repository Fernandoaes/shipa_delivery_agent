import type { CallSummary } from "@/lib/types";

export default function RecentCalls({ calls }: { calls: CallSummary[] }) {
  return (
    <div className="rounded-xl border border-shipa-sky-accent bg-white">
      <h2 className="border-b border-shipa-sky-accent px-5 py-3 text-sm font-semibold text-shipa-ink">Recent calls</h2>
      <table className="w-full text-left text-sm">
        <thead className="bg-shipa-sky text-shipa-ink/70">
          <tr>
            <th className="px-4 py-2 font-semibold">When</th>
            <th className="px-4 py-2 font-semibold">Customer</th>
            <th className="px-4 py-2 font-semibold">Intent</th>
            <th className="px-4 py-2 font-semibold">Disposition</th>
            <th className="px-4 py-2 font-semibold">CSAT</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c) => (
            <tr key={c.call_id} className="border-t border-shipa-sky-accent">
              <td className="px-4 py-2 text-shipa-ink/70">{new Date(c.started_at).toLocaleString()}</td>
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
