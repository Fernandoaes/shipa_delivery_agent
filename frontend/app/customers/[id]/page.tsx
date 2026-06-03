import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { getCustomer } from "@/lib/api";

export default async function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await getCustomer(id);
  return (
    <div>
      <Link href="/customers" className="text-sm text-shipa-blue hover:underline">← Customers</Link>
      <h1 className="mb-1 mt-2 text-2xl font-bold text-shipa-ink">{c.full_name}</h1>
      <p className="mb-6 text-sm text-shipa-ink/60">
        {c.primary_phone}
        {c.language_pref ? ` · ${c.language_pref}` : ""}
      </p>
      <h2 className="mb-3 text-lg font-semibold text-shipa-ink">Orders</h2>
      <div className="overflow-hidden rounded-xl border border-shipa-sky-accent bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-shipa-sky text-shipa-ink/70">
            <tr>
              <th className="px-4 py-3 font-semibold">Order</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Area</th>
            </tr>
          </thead>
          <tbody>
            {c.orders.map((o) => (
              <tr key={o.order_id} className="border-t border-shipa-sky-accent hover:bg-shipa-sky/50">
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
    </div>
  );
}
