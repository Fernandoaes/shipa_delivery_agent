import { Suspense } from "react";
import OrdersTable from "@/components/OrdersTable";
import { getOrders } from "@/lib/api";

export default async function OrdersPage() {
  const orders = await getOrders();
  return (
    <div className="px-8 py-8">
      <h1 className="mb-6 text-2xl font-bold text-txt">Orders</h1>
      <Suspense fallback={<div className="text-sm text-txt-dim">Loading…</div>}>
        <OrdersTable orders={orders} />
      </Suspense>
    </div>
  );
}
