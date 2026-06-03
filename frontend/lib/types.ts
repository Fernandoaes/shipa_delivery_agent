export type CallSummary = {
  call_id: string;
  direction: string;
  language: string | null;
  verification_status: string;
  intent: string | null;
  disposition: string | null;
  csat_score: number | null;
  started_at: string;
  ended_at: string | null;
};

export type RescheduleSummary = {
  reschedule_id: string;
  call_id: string;
  order_id: string;
  requested_date: string;
  status: string;
  synced_to_twin_at: string | null;
};

export type InvestigationSummary = {
  investigation_id: string;
  call_id: string;
  order_id: string;
  type: string;
  status: string;
  callback_due_at: string | null;
  opened_at: string;
};

export type EscalationSummary = {
  escalation_id: string;
  call_id: string;
  category: string;
  status: string;
  created_at: string;
};

export type Metrics = {
  total_calls: number;
  first_attempt_rate: number;
  deflection_rate: number;
  avg_csat: number | null;
  avg_handle_time_seconds: number | null;
};

export type OrderListItem = {
  order_id: string;
  twin_order_ref: string;
  merchant: string;
  status: string;
  delivery_area: string | null;
  delivery_window: string | null;
  assigned_driver: string | null;
  customer_name: string;
};

export type CustomerBrief = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
};

export type OrderDetail = {
  order_id: string;
  twin_order_ref: string;
  merchant: string;
  status: string;
  delivery_address: string;
  delivery_area: string | null;
  delivery_window: string | null;
  assigned_driver: string | null;
  expected_pieces: number | null;
  merchant_lat: number | null;
  merchant_lng: number | null;
  delivery_lat: number | null;
  delivery_lng: number | null;
  last_synced_at: string;
  customer: CustomerBrief;
};

export type CustomerListItem = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
  order_count: number;
};

export type CustomerDetail = {
  customer_id: string;
  full_name: string;
  primary_phone: string;
  language_pref: string | null;
  orders: OrderListItem[];
};
