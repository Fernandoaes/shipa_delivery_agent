import type {
  CallSummary,
  CustomerDetail,
  CustomerListItem,
  EscalationSummary,
  Insights,
  InvestigationSummary,
  Metrics,
  OrderDetail,
  OrderListItem,
  RescheduleSummary,
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

export const getCalls = () => get<CallSummary[]>("/calls");
export const getReschedules = () => get<RescheduleSummary[]>("/reschedules");
export const getInvestigations = () => get<InvestigationSummary[]>("/investigations");
export const getEscalations = () => get<EscalationSummary[]>("/escalations");
export const getMetrics = () => get<Metrics>("/metrics");
export const getInsights = () => get<Insights>("/insights");
export const getOrders = () => get<OrderListItem[]>("/orders");
export const getOrder = (id: string) => get<OrderDetail>(`/orders/${id}`);
export const getCustomers = () => get<CustomerListItem[]>("/customers");
export const getCustomer = (id: string) => get<CustomerDetail>(`/customers/${id}`);
