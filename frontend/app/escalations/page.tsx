import StatusBadge from "@/components/StatusBadge";
import { getEscalations } from "@/lib/api";

export default async function EscalationsPage() {
  const rows = await getEscalations();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Escalations</h1>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.escalation_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">{r.category}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-shipa-ink/60">No escalations yet.</p>}
      </div>
    </div>
  );
}
