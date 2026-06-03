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
                   language, verification_status, intent, disposition, csat_score, started_at)
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
       {_h("o.twin_order_ref", 2, 4, "1,4")}::numeric,
       now()
         - ({_h("o.twin_order_ref", 0, 14, "5,4")} || ' days')::interval
         - ({_h("o.twin_order_ref", 0, 24, "9,4")} || ' hours')::interval
FROM orders o JOIN customers cu ON cu.customer_id = o.customer_id
WHERE o.twin_order_ref LIKE 'TWIN-D%'
ON CONFLICT (happyrobot_call_id) DO NOTHING;
"""

ENDED_SQL = f"""
UPDATE calls
SET ended_at = started_at + ({_h("happyrobot_call_id", 40, 320, "1,4")} || ' seconds')::interval
WHERE happyrobot_call_id LIKE 'HR-TWIN-D%' AND ended_at IS NULL;
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

INVESTIGATIONS_SQL = """
INSERT INTO investigations (investigation_id, call_id, order_id, type, status, callback_due_at, opened_at)
SELECT gen_random_uuid(), c.call_id, c.order_id, 'not_received', 'open',
       now() + interval '1 day', c.started_at
FROM calls c JOIN orders o ON o.order_id = c.order_id
WHERE c.happyrobot_call_id LIKE 'HR-TWIN-D%' AND o.status = 'failed'
ON CONFLICT (call_id) DO NOTHING;
"""


def main() -> None:
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CALLS_SQL)
            cur.execute(ENDED_SQL)
            cur.execute(ESCALATIONS_SQL)
            cur.execute(RESCHEDULES_SQL)
            cur.execute(INVESTIGATIONS_SQL)
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
    print(f"calls(D)={calls}  open_escalations={esc}  pending_reschedules={resc}  open_investigations={inv}")


if __name__ == "__main__":
    main()
