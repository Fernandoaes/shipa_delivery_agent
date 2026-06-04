import StatusBadge from "@/components/StatusBadge";
import { getEscalations } from "@/lib/api";

export default async function EscalationsPage() {
  const rows = await getEscalations();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Escalations</h1>
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
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No escalations yet.</p>}
      </div>
    </div>
  );
}
