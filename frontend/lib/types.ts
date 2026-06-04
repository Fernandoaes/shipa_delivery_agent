export type CallSummary = {
  call_id: string;
  order_id: string | null;
  direction: string;
  language: string | null;
  verification_status: string;
  intent: string | null;
  disposition: string | null;
  csat_score: number | null;
  started_at: string;
  ended_at: string | null;
  customer_name: string | null;
  twin_order_ref: string | null;
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
  twin_order_ref: string | null;
  type: string;
  status: string;
  callback_due_at: string | null;
  opened_at: string;
};

export type EscalationSummary = {
  escalation_id: string;
  call_id: string;
  category: string;
  reason: string | null;
  status: string;
  created_at: string;
};

export type Metrics = {
  total_calls: number;
  first_attempt_success: number;
  on_time_rate: number;
  active_deliveries: number;
  at_risk: number;
  containment_rate: number;
  recovery_rate: number;
  avg_csat: number | null;
  avg_handle_time_seconds: number | null;
};

export type MapPoint = {
  order_id: string;
  twin_order_ref: string;
  status: string;
  delivery_area: string | null;
  delivery_lat: number;
  delivery_lng: number;
  merchant: string;
  merchant_lat: number | null;
  merchant_lng: number | null;
};

export type ChannelDay = { date: string; channels: Record<string, number> };
export type AreaCount = { area: string; count: number };

export type Insights = {
  interactions_per_day: ChannelDay[];
  intent_mix: { intent: string; count: number }[];
  disposition_mix: { disposition: string; count: number }[];
  failures_by_area: AreaCount[];
  needs_attention: {
    open_escalations: number;
    overdue_callbacks: number;
    pending_reschedules: number;
    pending_address_flags: number;
  };
  map_points: MapPoint[];
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
  calls: CallSummary[];
  avg_csat: number | null;
  last_contact_at: string | null;
  needs_follow_up: boolean;
};
