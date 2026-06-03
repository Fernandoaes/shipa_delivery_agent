-- ============================================================
-- Shipa — Twin read-side seed for a NEW workflow / fresh environment.
-- Self-contained: creates the read-side tables if missing (matches the
-- Alembic initial schema), then seeds demo customers + orders.
-- Featured test user: Ahmed Hassan (TWIN-CUST-WF-AHMED) with orders
-- covering the agent's main intents (tracking, out-for-delivery, failed).
-- Idempotent: re-running inserts nothing new (ON CONFLICT DO NOTHING).
-- Own ref namespace (*-WF-*); independent of the other seed files.
-- Mock OTPs — do NOT run against a real/production Twin database.
-- If Alembic migrations already ran, the CREATE TABLE block is a no-op.
-- ============================================================
BEGIN;

-- ---- read-side tables (no-op if migrations already created them) ----
CREATE TABLE IF NOT EXISTS customers (
  customer_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  twin_customer_ref text UNIQUE,
  full_name         text NOT NULL,
  primary_phone     varchar NOT NULL,
  alt_phone         varchar,
  language_pref     varchar,
  last_synced_at    timestamp NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customers_primary_phone ON customers (primary_phone);

CREATE TABLE IF NOT EXISTS orders (
  order_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  twin_order_ref   text NOT NULL UNIQUE,
  customer_id      uuid NOT NULL REFERENCES customers (customer_id),
  merchant         text NOT NULL,
  status           text NOT NULL,
  delivery_address text NOT NULL,
  delivery_area    text,
  delivery_window  text,
  otp_code         text,
  assigned_driver  text,
  expected_pieces  integer,
  last_synced_at   timestamp NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);

-- ---- customers ---------------------------------------------
INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at) VALUES
  (gen_random_uuid(), 'TWIN-CUST-WF-AHMED', 'Ahmed Hassan',  '+971500000001', '+971550000001', 'en', now()),
  (gen_random_uuid(), 'TWIN-CUST-WF-1',     'Layla Noor',    '+971500000002', NULL,            'ar', now()),
  (gen_random_uuid(), 'TWIN-CUST-WF-2',     'Omar Saeed',    '+971500000003', NULL,            'en', now())
ON CONFLICT (twin_customer_ref) DO NOTHING;

-- ---- orders ------------------------------------------------
-- Ahmed Hassan — four orders spanning the agent's main branches.
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(), v.twin_order_ref, c.customer_id,
       v.merchant, v.status, v.delivery_address, v.delivery_area, v.delivery_window,
       v.otp_code, v.assigned_driver, v.expected_pieces, now()
FROM customers c
CROSS JOIN (VALUES
  -- tracking: scheduled, no OTP yet
  ('TWIN-WF-AHMED-1', 'Amazon', 'pending',          'Apt 1203, Marina Heights, Dubai Marina', 'Dubai Marina',
     to_char(now()::date + 2, 'YYYY-MM-DD') || ' 09:00-12:00', NULL,   NULL,       2),
  -- out for delivery: OTP issued, driver assigned
  ('TWIN-WF-AHMED-2', 'Noon',   'out_for_delivery', 'Apt 1203, Marina Heights, Dubai Marina', 'Dubai Marina',
     to_char(now()::date,     'YYYY-MM-DD') || ' 13:00-17:00', '4821', 'Sara M.',  1),
  -- failed delivery: window in the past, OTP from the attempt
  ('TWIN-WF-AHMED-3', 'Temu',   'failed',           'Apt 1203, Marina Heights, Dubai Marina', 'Dubai Marina',
     to_char(now()::date - 1, 'YYYY-MM-DD') || ' 18:00-21:00', '7193', 'Ali K.',   3),
  -- delivered: closed, for "not received" branch
  ('TWIN-WF-AHMED-4', 'SHEIN',  'delivered',        'Apt 1203, Marina Heights, Dubai Marina', 'Dubai Marina',
     to_char(now()::date - 3, 'YYYY-MM-DD') || ' 09:00-12:00', '2056', 'Yusuf A.', 1)
) AS v(twin_order_ref, merchant, status, delivery_address, delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces)
WHERE c.twin_customer_ref = 'TWIN-CUST-WF-AHMED'
ON CONFLICT (twin_order_ref) DO NOTHING;

-- Layla Noor — out for delivery today (Arabic-pref caller).
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(), 'TWIN-WF-1', c.customer_id,
       'Trendyol', 'out_for_delivery', 'Villa 8, Al Barsha 2', 'Al Barsha',
       to_char(now()::date, 'YYYY-MM-DD') || ' 13:00-17:00', '6630', 'Fatima Z.', 1, now()
FROM customers c WHERE c.twin_customer_ref = 'TWIN-CUST-WF-1'
ON CONFLICT (twin_order_ref) DO NOTHING;

-- Omar Saeed — rescheduled order (reschedule branch).
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(), 'TWIN-WF-2', c.customer_id,
       'AliExpress', 'rescheduled', 'Office 14, Business Bay Tower', 'Business Bay',
       to_char(now()::date + 1, 'YYYY-MM-DD') || ' 18:00-21:00', NULL, 'Deepak R.', 2, now()
FROM customers c WHERE c.twin_customer_ref = 'TWIN-CUST-WF-2'
ON CONFLICT (twin_order_ref) DO NOTHING;

COMMIT;

-- Sanity check:
-- SELECT o.twin_order_ref, c.full_name, c.primary_phone, o.merchant, o.status, o.delivery_window, o.otp_code
--   FROM orders o JOIN customers c USING (customer_id)
--   WHERE o.twin_order_ref LIKE 'TWIN-WF-%' ORDER BY o.twin_order_ref;
