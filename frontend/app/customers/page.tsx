import Link from "next/link";
import { getCustomers } from "@/lib/api";

export default async function CustomersPage() {
  const customers = await getCustomers();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Customers</h1>
      <div className="overflow-hidden rounded-xl border border-hairline bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-2 text-txt-dim">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Phone</th>
              <th className="px-4 py-3 font-semibold">Language</th>
              <th className="px-4 py-3 font-semibold">Orders</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.customer_id} className="border-t border-hairline hover:bg-panel-2">
                <td className="px-4 py-3">
                  <Link href={`/customers/${c.customer_id}`} className="font-medium text-shipa-blue hover:underline">
                    {c.full_name}
                  </Link>
                </td>
                <td className="px-4 py-3">{c.primary_phone}</td>
                <td className="px-4 py-3">{c.language_pref ?? "—"}</td>
                <td className="px-4 py-3">{c.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
