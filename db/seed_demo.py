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

N_CUST = 40

# Single Shipa fulfilment hub (Al Quoz) — origin for every merchant leg.
HUB_LAT, HUB_LNG = 25.158, 55.236

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

# delivery_lat/lng arrays are index-aligned with areas (real Dubai centroids).
ORDERS_SQL = """
WITH cfg AS (
  SELECT
    ARRAY['Amazon','Temu','Trendyol','Noon','SHEIN','AliExpress'] AS merchants,
    ARRAY['pending','out_for_delivery','delivered','failed','rescheduled','returned','cancelled'] AS statuses,
    ARRAY['Dubai Marina','Al Barsha','Business Bay','Deira','JLT','Downtown','JVC','Mirdif','Silicon Oasis','Karama'] AS areas,
    ARRAY[25.077,25.113,25.187,25.271,25.069,25.197,25.058,25.217,25.121,25.245] AS lats,
    ARRAY[55.139,55.196,55.263,55.312,55.143,55.274,55.209,55.418,55.378,55.304] AS lngs,
    ARRAY['Rahul P.','Sara M.','Ali K.','Yusuf A.','Fatima Z.','Deepak R.','Hana S.','Marco T.'] AS drivers,
    ARRAY[' 09:00-12:00',' 13:00-17:00',' 18:00-21:00'] AS windows
),
gen AS (
  SELECT g, s, (g * 100 + s) AS n
  FROM generate_series(1, %(n)s) AS g
  CROSS JOIN generate_series(1, 3) AS s
)
INSERT INTO orders (order_id, twin_order_ref, customer_id, merchant, status, delivery_address,
                    delivery_area, delivery_window, otp_code, assigned_driver, expected_pieces,
                    merchant_lat, merchant_lng, delivery_lat, delivery_lng, last_synced_at)
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
       {hub_lat}, {hub_lng},
       ar.lat + ((((gen.n * 13) %% 21) - 10) * 0.0009),
       ar.lng + ((((gen.n * 29) %% 21) - 10) * 0.0009),
       now()
FROM gen
CROSS JOIN cfg
JOIN customers c ON c.twin_customer_ref = 'TWIN-CUST-D' || gen.g
JOIN LATERAL (SELECT cfg.statuses[1 + (gen.n %% array_length(cfg.statuses, 1))] AS status) st ON true
JOIN LATERAL (
  SELECT idx,
         cfg.areas[idx] AS area, cfg.lats[idx] AS lat, cfg.lngs[idx] AS lng
  FROM (SELECT 1 + (gen.n %% array_length(cfg.areas, 1)) AS idx) i
) ar ON true
ON CONFLICT (twin_order_ref) DO NOTHING;
""".format(hub_lat=HUB_LAT, hub_lng=HUB_LNG)


def main() -> None:
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
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
    print(f"customers(D)={cust}  orders(D)={ords}  orders_with_coords={coords}")


if __name__ == "__main__":
    main()
