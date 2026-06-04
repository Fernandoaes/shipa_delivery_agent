"""Demo seed: one call per *-D* order, plus a few escalations / reschedules /
investigations so the dashboard's insights + needs-attention are populated.

Idempotent: calls keyed by happyrobot_call_id 'HR-<order ref>' + ON CONFLICT;
operation rows keyed by the unique call_id + ON CONFLICT. Run:

    railway run --service Postgres -- uv run python db/seed_demo_calls.py

Mock data only — never run against a real Twin database.
"""

import os
import sys

import psycopg

URL = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
if not URL:
    sys.exit("No DATABASE_PUBLIC_URL / DATABASE_URL in environment")
URL = URL.replace("postgresql+psycopg://", "postgresql://")

# Deterministic int in [0, n) from a stable hash of the order ref.
def _h(expr_col: str, lo: int, span: int, slc: str) -> str:
    return f"({lo} + (('x'||substr(md5({expr_col}),{slc}))::bit(16)::int % {span}))"

CALLS_SQL = f"""
INSERT INTO calls (call_id, happyrobot_call_id, order_id, customer_id, direction, agent_type,
                   language, verification_status, intent, disposition, csat_score,
                   caller_number, notes, started_at)
SELECT gen_random_uuid(), 'HR-' || o.twin_order_ref, o.order_id, o.customer_id,
       'inbound', 'inbound_support', cu.language_pref,
       CASE WHEN o.status IN ('delivered','out_for_delivery') THEN 'passed'
            WHEN o.status IN ('failed','rescheduled') THEN 'partial'
            ELSE 'not_started' END,
       CASE o.status WHEN 'failed' THEN 'not_received'
                     WHEN 'rescheduled' THEN 'reschedule'
                     WHEN 'returned' THEN 'return_query'
                     ELSE 'delivery_status' END,
       CASE o.status WHEN 'failed' THEN 'investigation_opened'
                     WHEN 'rescheduled' THEN 'rescheduled'
                     WHEN 'returned' THEN 'escalated'
                     WHEN 'pending' THEN NULL
                     ELSE 'info_provided' END,
       -- CSAT tracks outcome: resolved customers rate high, exceptions lower.
       CASE o.status
            WHEN 'returned' THEN 2
            WHEN 'failed' THEN 3
            WHEN 'rescheduled' THEN 4
            ELSE 4 + ({_h("o.twin_order_ref", 0, 4, "1,4")} > 0)::int
       END::numeric,
       -- mock UAE mobile, deterministic per order so re-runs are stable
       '+9715' || lpad({_h("o.twin_order_ref", 0, 90000000, "1,8")}::text, 8, '0'),
       CASE o.status
            WHEN 'failed' THEN 'Customer reports package not received. Verified address, opened investigation and scheduled a callback.'
            WHEN 'rescheduled' THEN 'Customer not home during the window. Confirmed a new delivery date and synced the reschedule to Twin.'
            WHEN 'returned' THEN 'Customer wants to return the item. Escalated to the merchant for return approval.'
            WHEN 'pending' THEN NULL
            ELSE 'Provided live delivery status and ETA. Customer satisfied, no further action needed.'
       END,
       now()
         - ({_h("o.twin_order_ref", 0, 30, "5,4")} || ' days')::interval
         - ({_h("o.twin_order_ref", 0, 24, "9,4")} || ' hours')::interval
FROM orders o JOIN customers cu ON cu.customer_id = o.customer_id
WHERE o.twin_order_ref LIKE 'TWIN-D%'
ON CONFLICT (happyrobot_call_id) DO NOTHING;
"""

# Re-spread started_at across the last 30 days (anchored to now) so every
# range filter (1d/7d/30d) has data; deterministic per call, idempotent-by-shape.
SPREAD_SQL = f"""
UPDATE calls
SET started_at = now()
      - ({_h("happyrobot_call_id", 0, 30, "5,4")} || ' days')::interval
      - ({_h("happyrobot_call_id", 0, 24, "9,4")} || ' hours')::interval
WHERE happyrobot_call_id LIKE 'HR-TWIN-D%';
"""

ENDED_SQL = f"""
UPDATE calls
SET ended_at = started_at + ({_h("happyrobot_call_id", 45, 150, "1,4")} || ' seconds')::interval
WHERE happyrobot_call_id LIKE 'HR-TWIN-D%';
"""

ESCALATIONS_SQL = """
INSERT INTO escalations (escalation_id, call_id, order_id, category, reason, status, created_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, 'delivery_dispute', 'Customer dispute (mock)',
       'open', c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'returned'
ON CONFLICT (call_id) DO NOTHING;
"""

RESCHEDULES_SQL = """
INSERT INTO reschedules (reschedule_id, call_id, order_id, requested_date, requested_window,
                         reason, status, synced_to_twin_at, created_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, (now()::date + 2), '13:00-17:00',
       'Not home (mock)', 'requested', NULL, c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'rescheduled'
ON CONFLICT (call_id) DO NOTHING;
"""

INVESTIGATIONS_SQL = f"""
INSERT INTO investigations (investigation_id, call_id, order_id, type, status, callback_due_at, opened_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, 'not_received', 'open',
       -- spread callbacks around now so the queue shows both overdue and upcoming work
       now() + (({_h("o.twin_order_ref", 0, 48, "1,4")} - 30) || ' hours')::interval, c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'failed'
ON CONFLICT (call_id) DO NOTHING;
"""

# Address-fixes for at-risk orders. Recovery counts an at-risk order as recovered
# if it ever got a reschedule OR address-fix; this is what lifts recovery_rate off 0%.
# Cover 3 of every 4 at-risk orders (~75% recovery) — a row-number skip is stable
# at this small denominator, where per-hash thresholds swing between 50% and 100%.
ADDRESS_FLAGS_SQL = """
WITH atr AS (
  SELECT c.call_id, c.order_id, o.delivery_address, c.started_at,
         row_number() OVER (ORDER BY o.twin_order_ref) AS rn
  FROM calls c JOIN orders o ON o.order_id = c.order_id
  WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status IN ('failed','returned')
)
INSERT INTO address_flags (flag_id, call_id, order_id, original_address, correction_text, status, created_at)
SELECT gen_random_uuid(), call_id, order_id, delivery_address,
       'Tower B entrance, gate code at reception (mock)', 'pending', started_at
FROM atr WHERE rn % 4 <> 0
ON CONFLICT (call_id) DO NOTHING;
"""


# Clears the demo calls + their operation rows so a re-run re-applies changed
# intents/CSAT/dispositions (ON CONFLICT DO NOTHING alone never updates them).
RESET_SQL = """
DELETE FROM escalations    WHERE call_id IN (SELECT call_id FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%');
DELETE FROM reschedules     WHERE call_id IN (SELECT call_id FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%');
DELETE FROM investigations  WHERE call_id IN (SELECT call_id FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%');
DELETE FROM address_flags   WHERE call_id IN (SELECT call_id FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%');
DELETE FROM calls           WHERE happyrobot_call_id LIKE 'HR-TWIN-D%';
"""


def main() -> None:
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(RESET_SQL)
            cur.execute(CALLS_SQL)
            cur.execute(SPREAD_SQL)
            cur.execute(ENDED_SQL)
            cur.execute(ESCALATIONS_SQL)
            cur.execute(RESCHEDULES_SQL)
            cur.execute(INVESTIGATIONS_SQL)
            cur.execute(ADDRESS_FLAGS_SQL)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM calls WHERE happyrobot_call_id LIKE 'HR-TWIN-D%%'")
            calls = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM escalations WHERE status='open'")
            esc = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM reschedules WHERE synced_to_twin_at IS NULL")
            resc = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM investigations WHERE status='open'")
            inv = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM address_flags WHERE status='pending'")
            flags = cur.fetchone()[0]
    print(
        f"calls(D)={calls}  open_escalations={esc}  pending_reschedules={resc}  "
        f"open_investigations={inv}  pending_address_flags={flags}"
    )


if __name__ == "__main__":
    main()
