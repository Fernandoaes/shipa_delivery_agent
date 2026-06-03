-- ============================================================
-- Shipa — single EASY test user for manual end-to-end call testing.
-- One customer, one out_for_delivery order (richest branch: OTP +
-- driver + today's window). Round, memorable values for live demos.
-- Idempotent: re-running inserts nothing new (ON CONFLICT DO NOTHING).
-- Own ref namespace (*-DEMO-*); independent of the other seed files.
-- Mock OTP — do NOT run against a real/production Twin database.
-- ============================================================
BEGIN;

INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at) VALUES
  (gen_random_uuid(), 'TWIN-CUST-DEMO', 'Test User', '+10000000001', NULL, 'en', now())
ON CONFLICT (twin_customer_ref) DO NOTHING;

INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces,
                    merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at)
SELECT gen_random_uuid(), 'DEMO-0001', c.customer_id,
       'Amazon', 'out_for_delivery', 'Apt 100, Marina Heights, Dubai Marina', 'Dubai Marina',
       to_char(now()::date, 'YYYY-MM-DD') || ' 09:00-12:00', '0000', 'Sara M.', 1,
       24.9180, 55.1610, 25.0805, 55.1403, now()
FROM customers c WHERE c.twin_customer_ref = 'TWIN-CUST-DEMO'
ON CONFLICT (twin_order_ref) DO NOTHING;

COMMIT;

-- Sanity check:
-- SELECT o.twin_order_ref, c.full_name, c.primary_phone, o.merchant, o.status, o.delivery_window, o.otp_code
--   FROM orders o JOIN customers c USING (customer_id)
--   WHERE o.twin_order_ref = 'DEMO-0001';
