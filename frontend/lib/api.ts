import type {
  CustomerDetail,
  CustomerListItem,
  OrderDetail,
  OrderListItem,
} from "@/lib/types";

const BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const KEY = process.env.DASHBOARD_API_KEY ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "X-API-Key": KEY },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getOrders = () => get<OrderListItem[]>("/orders");
export const getOrder = (id: string) => get<OrderDetail>(`/orders/${id}`);
export const getCustomers = () => get<CustomerListItem[]>("/customers");
export const getCustomer = (id: string) => get<CustomerDetail>(`/customers/${id}`);
