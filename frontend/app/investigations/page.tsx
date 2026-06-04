import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { getInvestigations } from "@/lib/api";

export default async function InvestigationsPage() {
  const rows = await getInvestigations();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Investigations</h1>
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
                    {r.order_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3">{r.type}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {r.callback_due_at ? new Date(r.callback_due_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">{new Date(r.opened_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-txt-dim">No investigations yet.</p>}
      </div>
    </div>
  );
}
