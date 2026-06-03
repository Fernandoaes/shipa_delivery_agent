-- ============================================================
-- Shipa — named TEST customers (read side: customers + orders)
-- Hand-picked rows for manual demo/testing against the inbound agent.
-- Idempotent: re-running inserts nothing new (ON CONFLICT DO NOTHING).
-- Own ref namespace (*-TEST-*); independent of the other seed files.
-- Mock OTPs — do NOT run against a real/production Twin database.
-- ============================================================
BEGIN;

-- ---- customers ---------------------------------------------
INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at) VALUES
  (gen_random_uuid(), 'TWIN-CUST-TEST-1', 'Ahmed Hassan', '+12345678902', NULL, 'en', now()),
  (gen_random_uuid(), 'TWIN-CUST-TEST-2', 'John Doe',     '+12345678903', NULL, 'en', now())
ON CONFLICT (twin_customer_ref) DO NOTHING;

-- ---- orders ------------------------------------------------
-- Ahmed Hassan: Amazon, scheduled for next week (pending -> no OTP yet).
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(), 'TWIN-TEST-1', c.customer_id,
       'Amazon', 'pending', 'Apt 101, Marina Heights, Dubai Marina', 'Dubai Marina',
       to_char(now()::date + 7, 'YYYY-MM-DD') || ' 09:00-12:00', NULL, NULL, 1, now()
FROM customers c WHERE c.twin_customer_ref = 'TWIN-CUST-TEST-1'
ON CONFLICT (twin_order_ref) DO NOTHING;

-- John Doe: failed delivery (window in the past, OTP issued at the attempt).
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(), 'TWIN-TEST-2', c.customer_id,
       'Amazon', 'failed', 'Villa 22, Al Barsha 1', 'Al Barsha',
       to_char(now()::date - 1, 'YYYY-MM-DD') || ' 13:00-17:00', '4417', 'Sara M.', 2, now()
FROM customers c WHERE c.twin_customer_ref = 'TWIN-CUST-TEST-2'
ON CONFLICT (twin_order_ref) DO NOTHING;

COMMIT;

-- Sanity check:
-- SELECT o.twin_order_ref, c.full_name, c.primary_phone, o.merchant, o.status, o.delivery_window, o.otp_code
--   FROM orders o JOIN customers c USING (customer_id)
--   WHERE o.twin_order_ref LIKE 'TWIN-TEST-%' ORDER BY o.twin_order_ref;
