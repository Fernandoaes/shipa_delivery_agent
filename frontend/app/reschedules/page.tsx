import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { getReschedules } from "@/lib/api";

export default async function ReschedulesPage() {
  const rows = await getReschedules();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-shipa-ink">Reschedules</h1>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Requested date</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Synced to Twin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.reschedule_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
                <td className="px-4 py-3">
                  <Link href={`/orders/${r.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {r.order_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">{r.requested_date}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {r.synced_to_twin_at ? new Date(r.synced_to_twin_at).toLocaleString() : "pending"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="px-4 py-6 text-sm text-shipa-ink/60">No reschedules yet.</p>}
      </div>
    </div>
  );
}
