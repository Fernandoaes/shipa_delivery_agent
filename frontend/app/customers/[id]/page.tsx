import Link from "next/link";
import BackButton from "@/components/BackButton";
import StatusBadge from "@/components/StatusBadge";
import { getCustomer } from "@/lib/api";

export default async function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await getCustomer(id);
  return (
    <div className="px-8 py-8">
      <BackButton href="/customers" label="Customers" />
      <h1 className="mb-1 mt-3 text-2xl font-bold text-txt">{c.full_name}</h1>
      <p className="mb-6 text-sm text-txt-dim">
        {c.primary_phone}
        {c.language_pref ? ` · ${c.language_pref}` : ""}
      </p>

      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-hairline bg-panel p-4">
          <div className="text-xs uppercase tracking-wide text-txt-faint">Avg CSAT</div>
          <div className="mt-1 text-2xl font-bold text-txt">{c.avg_csat?.toFixed(1) ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-hairline bg-panel p-4">
          <div className="text-xs uppercase tracking-wide text-txt-faint">Last contact</div>
          <div className="mt-1 text-sm font-medium text-txt">
            {c.last_contact_at ? new Date(c.last_contact_at).toLocaleDateString() : "—"}
          </div>
        </div>
        <div className="rounded-xl border border-hairline bg-panel p-4">
          <div className="text-xs uppercase tracking-wide text-txt-faint">Status</div>
          <div className={`mt-1 text-sm font-semibold ${c.needs_follow_up ? "text-bad" : "text-ok"}`}>
            {c.needs_follow_up ? "Needs follow-up" : "Healthy"}
          </div>
        </div>
      </div>

      <h2 className="mb-3 text-lg font-semibold text-txt">Orders</h2>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Area</th>
            </tr>
          </thead>
          <tbody>
            {c.orders.map((o) => (
              <tr key={o.order_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.order_id}`} className="font-medium text-shipa-blue hover:underline">
                    {o.twin_order_ref}
                  </Link>
                </td>
                <td className="px-4 py-3">{o.merchant}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3">{o.delivery_area ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="mb-3 mt-8 text-lg font-semibold text-txt">Call history</h2>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-2 font-semibold">When</th>
              <th className="px-4 py-2 font-semibold">Intent</th>
              <th className="px-4 py-2 font-semibold">Disposition</th>
              <th className="px-4 py-2 font-semibold">CSAT</th>
            </tr>
          </thead>
          <tbody>
            {c.calls.length === 0 && (
              <tr><td className="px-4 py-3 text-txt-faint" colSpan={4}>No calls yet.</td></tr>
            )}
            {c.calls.map((call) => (
              <tr key={call.call_id} className="border-t border-hairline">
                <td className="px-4 py-2 text-txt-dim">{new Date(call.started_at).toLocaleString()}</td>
                <td className="px-4 py-2">{call.intent ?? "—"}</td>
                <td className="px-4 py-2">{call.disposition ?? "—"}</td>
                <td className="px-4 py-2">{call.csat_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
