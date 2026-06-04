"""Demo seed: customers + orders WITH delivery-map coordinates.

Unlike the .sql seeds, this populates merchant_/delivery_ lat/lng so the
dashboard map renders. Idempotent via the TWIN-*-D* ref namespace +
ON CONFLICT DO NOTHING. Run locally against Railway PG:

    railway run --service Postgres -- uv run python db/seed_demo.py

Mock data only — never run against a real Twin database.
"""

import os
import sys

import psycopg

URL = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
if not URL:
    sys.exit("No DATABASE_PUBLIC_URL / DATABASE_URL in environment")
URL = URL.replace("postgresql+psycopg://", "postgresql://")

N_CUST = 30

CUSTOMERS_SQL = """
WITH params AS (
  SELECT
    ARRAY['Aisha','Omar','Fatima','Mohammed','Priya','Yusuf','Layla','Hassan','Sara','Ali',
          'Noor','Khalid','Mariam','Rashid','Zainab','Tariq','Huda','Bilal','Reem','Saif'] AS firsts,
    ARRAY['Khan','Al Farsi','Noor','Saeed','Nair','Ahmed','Hassan','Al Mansoori','Patel','Rahman',
          'Sheikh','Al Qasimi','Iqbal','Habib','Al Suwaidi','Aziz','Malik','Al Zaabi','Nasser','Raman'] AS lasts
)
INSERT INTO customers (customer_id, twin_customer_ref, full_name, primary_phone, alt_phone, language_pref, last_synced_at)
SELECT gen_random_uuid(),
       'TWIN-CUST-D' || g,
       p.firsts[1 + (g %% array_length(p.firsts, 1))] || ' ' ||
       p.lasts [1 + ((g * 7) %% array_length(p.lasts, 1))],
       '+97152' || lpad(g::text, 7, '0'),
       CASE WHEN g %% 5 = 0 THEN '+97153' || lpad(g::text, 7, '0') ELSE NULL END,
       CASE WHEN g %% 2 = 0 THEN 'ar' ELSE 'en' END,
       now()
FROM generate_series(1, %(n)s) AS g
CROSS JOIN params p
ON CONFLICT (twin_customer_ref) DO NOTHING;
"""

# areas / lats / lngs (real UAE centroids) and hub_lats / hub_lngs (regional
# fulfilment origin per area) are all index-aligned. Spread across four emirates:
# Dubai (1-14), Sharjah (15-18), Ajman (19-20), Abu Dhabi (21-25).
ORDERS_SQL = """
WITH cfg AS (
  SELECT
    ARRAY['Amazon','Temu','Trendyol','Noon','SHEIN','AliExpress','Namshi','Carrefour'] AS merchants,
    -- Weighted toward delivered to reflect a healthy operation: ~72 pct delivered,
    -- ~12 pct active (out_for_delivery/pending), small tail of exceptions the agent recovers.
    ARRAY['delivered','delivered','delivered','delivered','delivered','delivered','delivered','delivered',
          'delivered','delivered','delivered','delivered','delivered','delivered','delivered','delivered',
          'delivered','delivered',
          'out_for_delivery','out_for_delivery','out_for_delivery',
          'pending',
          'rescheduled',
          'failed',
          'returned'] AS statuses,
    ARRAY['Dubai Marina','Al Barsha','Business Bay','Deira','JLT','Downtown','JVC','Mirdif',
          'Silicon Oasis','Karama','Jumeirah','Palm Jumeirah','International City','Dubai Hills',
          'Al Majaz','Al Nahda','Muweilah','Al Khan',
          'Ajman Corniche','Al Nuaimiya',
          'Al Reem Island','Khalifa City','Yas Island','Corniche AD','Al Raha'] AS areas,
    ARRAY[25.077,25.113,25.187,25.271,25.069,25.197,25.058,25.217,25.121,25.245,25.203,25.112,25.166,25.103,
          25.327,25.297,25.290,25.330,
          25.411,25.396,
          24.498,24.419,24.499,24.466,24.456] AS lats,
    ARRAY[55.139,55.196,55.263,55.312,55.143,55.274,55.209,55.418,55.378,55.304,55.244,55.138,55.408,55.247,
          55.382,55.371,55.470,55.365,
          55.435,55.477,
          54.404,54.578,54.607,54.330,54.610] AS lngs,
    ARRAY[25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,25.130,
          25.317,25.317,25.317,25.317,
          25.405,25.405,
          24.350,24.350,24.350,24.350,24.350] AS hub_lats,
    ARRAY[55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,55.233,
          55.420,55.420,55.420,55.420,
          55.510,55.510,
          54.500,54.500,54.500,54.500,54.500] AS hub_lngs,
    ARRAY['Rahul P.','Sara M.','Ali K.','Yusuf A.','Fatima Z.','Deepak R.','Hana S.','Marco T.',
          'Imran B.','Lena O.','Faisal R.','Grace W.'] AS drivers,
    ARRAY[' 09:00-12:00',' 13:00-17:00',' 18:00-21:00'] AS windows
),
gen AS (
  SELECT g, s, (g * 100 + s) AS n
  FROM generate_series(1, %(n)s) AS g
  CROSS JOIN generate_series(1, 3) AS s
)
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces,
                    merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at,
                    attempt_count, delivered_at, sla_due_at)
SELECT gen_random_uuid(),
       'TWIN-D' || gen.n,
       c.customer_id,
       cfg.merchants[1 + (gen.n %% array_length(cfg.merchants, 1))],
       st.status,
       'Unit ' || gen.s || ', ' || ar.area || ' Bldg ' || gen.g,
       ar.area,
       CASE
         WHEN st.status IN ('out_for_delivery','rescheduled')
           THEN to_char(now()::date + (gen.n %% 3), 'YYYY-MM-DD') || cfg.windows[1 + (gen.n %% 3)]
         WHEN st.status IN ('delivered','failed')
           THEN to_char(now()::date - (1 + gen.n %% 3), 'YYYY-MM-DD') || cfg.windows[1 + (gen.n %% 3)]
         ELSE NULL
       END,
       CASE WHEN st.status IN ('out_for_delivery','delivered')
            THEN lpad(((gen.n * 7919) %% 10000)::text, 4, '0') ELSE NULL END,
       CASE WHEN st.status IN ('pending','cancelled')
            THEN NULL ELSE cfg.drivers[1 + (gen.n %% array_length(cfg.drivers, 1))] END,
       1 + (gen.n %% 4),
       ar.hub_lat, ar.hub_lng,
       ar.lat + ((((gen.n * 13) %% 21) - 10) * 0.0009),
       ar.lng + ((((gen.n * 29) %% 21) - 10) * 0.0009),
       now(),
       -- attempt_count: failed/returned/rescheduled took >=2 attempts; a minority of delivered took 2-3
       CASE
         WHEN st.status IN ('failed','returned') THEN 2 + (gen.n %% 2)
         WHEN st.status = 'rescheduled' THEN 2
         WHEN st.status = 'delivered' AND gen.n %% 16 = 0 THEN 2
         ELSE 1
       END,
       -- delivered_at: set for delivered rows, derived from the window date
       CASE WHEN st.status = 'delivered'
            THEN (now()::date - (1 + gen.n %% 3)) + time '10:30' ELSE NULL END,
       -- sla_due_at: promised deadline; ~94 pct of delivered land on/before it
       CASE
         WHEN st.status = 'delivered'
           THEN (now()::date - (1 + gen.n %% 3)) + CASE WHEN gen.n %% 18 = 0 THEN time '09:00' ELSE time '17:00' END
         WHEN st.status IN ('out_for_delivery','rescheduled','failed','returned')
           THEN (now()::date + (gen.n %% 3)) + time '17:00'
         ELSE NULL
       END
FROM gen
CROSS JOIN cfg
JOIN customers c ON c.twin_customer_ref = 'TWIN-CUST-D' || gen.g
-- gen.n = g*100+s collapses to s under %% array_length; use (7g+s) so the weighted mix spreads.
JOIN LATERAL (SELECT cfg.statuses[1 + ((gen.g * 7 + gen.s) %% array_length(cfg.statuses, 1))] AS status) st ON true
JOIN LATERAL (
  SELECT cfg.areas[idx] AS area,
         cfg.lats[idx] AS lat, cfg.lngs[idx] AS lng,
         cfg.hub_lats[idx] AS hub_lat, cfg.hub_lngs[idx] AS hub_lng
  -- gen.n = g*100+s collapses to s under %% array_length; use (3g+s) so all areas are hit.
  FROM (SELECT 1 + ((gen.g * 3 + gen.s) %% array_length(cfg.areas, 1)) AS idx) i
) ar ON true
ON CONFLICT (twin_order_ref) DO NOTHING;
"""


# Clears the demo namespace (TWIN-D* / TWIN-CUST-D*) in FK-dependency order so the
# seed is a true reset — ON CONFLICT DO NOTHING alone never re-applies a changed mix.
# Mock namespace only; never touches real Twin refs.
RESET_SQL = """
DELETE FROM escalations    WHERE order_id IN (SELECT order_id FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%');
DELETE FROM reschedules     WHERE order_id IN (SELECT order_id FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%');
DELETE FROM investigations  WHERE order_id IN (SELECT order_id FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%');
DELETE FROM address_flags   WHERE order_id IN (SELECT order_id FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%');
DELETE FROM calls           WHERE order_id IN (SELECT order_id FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%');
DELETE FROM orders          WHERE twin_order_ref LIKE 'TWIN-D%%';
DELETE FROM customers       WHERE twin_customer_ref LIKE 'TWIN-CUST-D%%';
"""


def main() -> None:
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(RESET_SQL)
            cur.execute(CUSTOMERS_SQL, {"n": N_CUST})
            cur.execute(ORDERS_SQL, {"n": N_CUST})
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM customers WHERE twin_customer_ref LIKE 'TWIN-CUST-D%%'")
            cust = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%'")
            ords = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%' "
                "AND delivery_lat IS NOT NULL AND delivery_lng IS NOT NULL"
            )
            coords = cur.fetchone()[0]
            cur.execute("SELECT count(DISTINCT delivery_area) FROM orders WHERE twin_order_ref LIKE 'TWIN-D%%'")
            areas = cur.fetchone()[0]
    print(f"customers(D)={cust}  orders(D)={ords}  orders_with_coords={coords}  distinct_areas={areas}")


if __name__ == "__main__":
    main()
