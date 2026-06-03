-- ============================================================
-- Shipa — mock Twin data (read side: customers + orders)
-- Idempotent: re-running inserts nothing new (ON CONFLICT DO NOTHING).
-- Rows TWIN-1001..1003 mirror the backend MockTwinClient.
-- Mock OTPs — do NOT run against a real/production Twin database.
-- ============================================================
BEGIN;

-- ---- customers (dedupe key: twin_customer_ref) -------------
INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at) VALUES
  (gen_random_uuid(), 'TWIN-CUST-1', 'Aisha Khan',     '+971500000001', NULL,            'en', now()),
  (gen_random_uuid(), 'TWIN-CUST-2', 'Omar Al Farsi',  '+971500000002', NULL,            'ar', now()),
  (gen_random_uuid(), 'TWIN-CUST-3', 'Fatima Noor',    '+971500000003', NULL,            'en', now()),
  (gen_random_uuid(), 'TWIN-CUST-4', 'Mohammed Saeed', '+971500000004', '+971500000444', 'ar', now()),
  (gen_random_uuid(), 'TWIN-CUST-5', 'Priya Nair',     '+971500000005', NULL,            'en', now())
ON CONFLICT (twin_customer_ref) DO NOTHING;

-- ---- orders (dedupe key: twin_order_ref; FK via subquery) --
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address, delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at) VALUES
  -- tracking / OTP read-out (out for delivery)
  (gen_random_uuid(), 'TWIN-1001', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-1'),
   'Amazon',   'out_for_delivery', 'Apt 12, Marina Gate 1, Dubai Marina', 'Dubai Marina',  '2026-06-03 09:00-12:00', '4821', 'Rahul P.', 1, 24.9180, 55.1610, 25.0805, 55.1403, now()),
  -- failed delivery / re-attempt
  (gen_random_uuid(), 'TWIN-1002', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-2'),
   'Temu',     'failed',           'Villa 7, Al Barsha 2',                'Al Barsha',     '2026-06-02 14:00-18:00', '7310', 'Sara M.',  3, 24.9700, 55.1800, 25.1107, 55.2014, now()),
  -- delivered but "not received" -> investigation
  (gen_random_uuid(), 'TWIN-1003', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-3'),
   'Trendyol', 'delivered',        'Office 401, Business Bay Tower',      'Business Bay',  '2026-06-01 10:00-13:00', '1599', 'Ali K.',   2, 25.1200, 55.2000, 25.1857, 55.2645, now()),
  -- reschedule scenario (out for delivery)
  (gen_random_uuid(), 'TWIN-1004', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-4'),
   'Amazon',   'out_for_delivery', 'Shop 3, Naif Road, Deira',            'Deira',         '2026-06-03 13:00-17:00', '5566', 'Yusuf A.', 2, 24.9180, 55.1610, 25.2730, 55.3050, now()),
  -- same customer, second order, pending -> no OTP yet (multi-order customer)
  (gen_random_uuid(), 'TWIN-1005', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-4'),
   'Noon',     'pending',          'Shop 3, Naif Road, Deira',            'Deira',         NULL,                     NULL,   NULL,       1, 24.9700, 55.1800, 25.2730, 55.3050, now()),
  -- wrong / missing items (delivered, multi-piece)
  (gen_random_uuid(), 'TWIN-1006', (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-5'),
   'Trendyol', 'delivered',        'Apt 9, JLT Cluster C',                'JLT',           '2026-06-01 09:00-12:00', '8842', 'Ali K.',   3, 25.1200, 55.2000, 25.0693, 55.1440, now())
ON CONFLICT (twin_order_ref) DO NOTHING;

COMMIT;

-- Quick check:
-- SELECT o.twin_order_ref, c.full_name, o.status, o.delivery_area
--   FROM orders o JOIN customers c USING (customer_id) ORDER BY o.twin_order_ref;
