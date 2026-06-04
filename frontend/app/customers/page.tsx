import { Suspense } from "react";
import CustomersTable from "@/components/CustomersTable";
import { getCustomers } from "@/lib/api";

export default async function CustomersPage() {
  const customers = await getCustomers();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Customers</h1>
      <Suspense fallback={<div className="text-sm text-txt-dim">Loading…</div>}>
        <CustomersTable customers={customers} />
      </Suspense>
    </div>
  );
}
