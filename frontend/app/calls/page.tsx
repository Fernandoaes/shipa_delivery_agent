import StatusBadge from "@/components/StatusBadge";
import { getCalls } from "@/lib/api";

function fmt(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString();
}

export default async function CallsPage() {
  const calls = await getCalls();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Calls</h1>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Started</th>
              <th className="px-4 py-3 font-semibold">Direction</th>
              <th className="px-4 py-3 font-semibold">Language</th>
              <th className="px-4 py-3 font-semibold">Verification</th>
              <th className="px-4 py-3 font-semibold">Intent</th>
              <th className="px-4 py-3 font-semibold">Disposition</th>
              <th className="px-4 py-3 font-semibold">CSAT</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((c) => (
              <tr key={c.call_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3 whitespace-nowrap">{fmt(c.started_at)}</td>
                <td className="px-4 py-3">{c.direction}</td>
                <td className="px-4 py-3 uppercase">{c.language ?? "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={c.verification_status} /></td>
                <td className="px-4 py-3">{c.intent ?? "—"}</td>
                <td className="px-4 py-3">{c.disposition ?? "—"}</td>
                <td className="px-4 py-3">{c.csat_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {calls.length === 0 && (
          <p className="px-4 py-6 text-sm text-shipa-ink/60">No calls yet.</p>
        )}
      </div>
    </div>
  );
}
