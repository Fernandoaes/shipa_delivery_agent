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
