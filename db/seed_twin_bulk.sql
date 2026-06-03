-- ============================================================
-- Shipa — BULK mock Twin data (read side: customers + orders)
-- For demos: ~200 customers, ~600 orders, predictable refs.
-- Idempotent: re-running inserts nothing new (ON CONFLICT DO NOTHING).
-- Independent of seed_twin_mock.sql (different ref namespace: *-B*).
-- Mock OTPs — do NOT run against a real/production Twin database.
--
-- Tune volume: change the generate_series bounds below.
--   customers = N (customer block), orders = N * 3 (order block).
-- Predictable test handles:
--   customer ref   TWIN-CUST-B<g>      (g = 1..N)
--   primary phone  +97150<g zero-pad7> (e.g. +971500000042)
--   order ref      TWIN-B<g*100+s>     (s = 1..3 orders per customer)
-- ============================================================
BEGIN;

-- ---- customers ---------------------------------------------
WITH params AS (
  SELECT
    ARRAY['Aisha','Omar','Fatima','Mohammed','Priya','Yusuf','Layla','Hassan','Sara','Ali',
          'Noor','Khalid','Mariam','Rashid','Zainab','Tariq','Huda','Bilal','Reem','Saif'] AS firsts,
    ARRAY['Khan','Al Farsi','Noor','Saeed','Nair','Ahmed','Hassan','Al Mansoori','Patel','Rahman',
          'Sheikh','Al Qasimi','Iqbal','Habib','Al Suwaidi','Aziz','Malik','Al Zaabi','Nasser','Raman'] AS lasts
)
INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at)
SELECT gen_random_uuid(),
       'TWIN-CUST-B' || g,
       p.firsts[1 + (g % array_length(p.firsts, 1))] || ' ' ||
       p.lasts [1 + ((g * 7) % array_length(p.lasts, 1))],
       '+97150' || lpad(g::text, 7, '0'),
       CASE WHEN g % 5 = 0 THEN '+97155' || lpad(g::text, 7, '0') ELSE NULL END,
       CASE WHEN g % 2 = 0 THEN 'ar' ELSE 'en' END,
       now()
FROM generate_series(1, 200) AS g
CROSS JOIN params p
ON CONFLICT (twin_customer_ref) DO NOTHING;

-- ---- orders (3 per customer; covers every status/merchant/area) ----
WITH cfg AS (
  SELECT
    ARRAY['Amazon','Temu','Trendyol','Noon','SHEIN','AliExpress'] AS merchants,
    ARRAY['pending','out_for_delivery','delivered','failed','rescheduled','returned','cancelled'] AS statuses,
    ARRAY['Dubai Marina','Al Barsha','Business Bay','Deira','JLT','Downtown','JVC','Mirdif','Silicon Oasis','Karama'] AS areas,
    ARRAY['Rahul P.','Sara M.','Ali K.','Yusuf A.','Fatima Z.','Deepak R.','Hana S.','Marco T.'] AS drivers,
    ARRAY[' 09:00-12:00',' 13:00-17:00',' 18:00-21:00'] AS windows
),
gen AS (
  SELECT g, s, (g * 100 + s) AS n
  FROM generate_series(1, 200) AS g
  CROSS JOIN generate_series(1, 3) AS s
)
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces, last_synced_at)
SELECT gen_random_uuid(),
       'TWIN-B' || gen.n,
       c.customer_id,
       cfg.merchants[1 + (gen.n % array_length(cfg.merchants, 1))],
       st.status,
       'Unit ' || gen.s || ', ' || ar.area || ' Bldg ' || gen.g,
       ar.area,
       CASE
         WHEN st.status IN ('out_for_delivery','rescheduled')
           THEN to_char(now()::date + (gen.n % 3), 'YYYY-MM-DD') || cfg.windows[1 + (gen.n % 3)]
         WHEN st.status IN ('delivered','failed')
           THEN to_char(now()::date - (1 + gen.n % 3), 'YYYY-MM-DD') || cfg.windows[1 + (gen.n % 3)]
         ELSE NULL
       END,
       -- OTP only exists once a parcel is on the road or handed over.
       CASE WHEN st.status IN ('out_for_delivery','delivered')
            THEN lpad(((gen.n * 7919) % 10000)::text, 4, '0') ELSE NULL END,
       CASE WHEN st.status IN ('pending','cancelled')
            THEN NULL ELSE cfg.drivers[1 + (gen.n % array_length(cfg.drivers, 1))] END,
       1 + (gen.n % 4),
       now()
FROM gen
CROSS JOIN cfg
JOIN customers c ON c.twin_customer_ref = 'TWIN-CUST-B' || gen.g
JOIN LATERAL (SELECT cfg.statuses[1 + (gen.n % array_length(cfg.statuses, 1))] AS status) st ON true
JOIN LATERAL (SELECT cfg.areas   [1 + (gen.n % array_length(cfg.areas,    1))] AS area)   ar ON true
ON CONFLICT (twin_order_ref) DO NOTHING;

COMMIT;

-- Sanity checks:
-- SELECT count(*) AS customers FROM customers WHERE twin_customer_ref LIKE 'TWIN-CUST-B%';
-- SELECT status, count(*) FROM orders WHERE twin_order_ref LIKE 'TWIN-B%' GROUP BY status ORDER BY status;
-- SELECT o.twin_order_ref, c.full_name, c.primary_phone, o.merchant, o.status, o.delivery_area, o.otp_code
--   FROM orders o JOIN customers c USING (customer_id)
--   WHERE o.twin_order_ref LIKE 'TWIN-B%' ORDER BY o.twin_order_ref LIMIT 20;
