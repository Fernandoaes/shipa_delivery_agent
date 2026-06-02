-- ============================================================
-- Shipa — mock verification data (write side: calls + verifications)
-- Depends on seed_twin_mock.sql (customers TWIN-CUST-*, orders TWIN-100*).
-- Idempotent: calls dedupe on happyrobot_call_id; verifications/escalations
--   guarded by NOT EXISTS, so re-running inserts nothing new.
-- Rows mirror the scoring rules in app/services/verification.py:
--   strong pass = {order_ref, name}; fallback pass = {registered_phone, name, delivery_area};
--   any other non-empty factor set = partial; empty = failed.
--   verification_max_attempts = 3 -> attempt 4 escalates (category verification_failed).
-- Mock data — do NOT run against production.
-- ============================================================
BEGIN;

-- ---- calls (dedupe key: happyrobot_call_id) ----------------
-- One inbound exception call per scenario. order_id/customer_id are set only
-- on a passing call, matching verify_caller(); non-passed calls leave them NULL.
INSERT INTO calls (call_id, happyrobot_call_id, order_id, customer_id, direction, agent_type,
                   caller_number, language, verification_status, intent, disposition, started_at, ended_at) VALUES
  -- V1: strong pass (order_ref + name), tracking read-out
  (gen_random_uuid(), 'HR-MOCK-V1',
   (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1001'),
   (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-1'),
   'inbound', 'inbound_exception', '+971500000001', 'en', 'passed', 'tracking', 'resolved_info',
   now() - interval '50 min', now() - interval '46 min'),
  -- V2: fallback pass (registered_phone + name + delivery_area), failed-delivery re-attempt
  (gen_random_uuid(), 'HR-MOCK-V2',
   (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1002'),
   (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-2'),
   'inbound', 'inbound_exception', '+971500000002', 'ar', 'passed', 'failed_delivery', 're_attempt_scheduled',
   now() - interval '40 min', now() - interval '34 min'),
  -- V3: partial then pass over two attempts, "not received" investigation
  (gen_random_uuid(), 'HR-MOCK-V3',
   (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1003'),
   (SELECT customer_id FROM customers WHERE twin_customer_ref='TWIN-CUST-3'),
   'inbound', 'inbound_exception', '+971500000003', 'en', 'passed', 'not_received', 'investigation_opened',
   now() - interval '30 min', now() - interval '22 min'),
  -- V4: four failed attempts (no matching order) -> exceeds cap -> escalation
  (gen_random_uuid(), 'HR-MOCK-V4', NULL, NULL,
   'inbound', 'inbound_exception', '+971555550000', 'en', 'failed', 'other', 'verification_failed',
   now() - interval '20 min', now() - interval '12 min'),
  -- V5: single failed attempt, ref matches no order -> no_order_found
  (gen_random_uuid(), 'HR-MOCK-V5', NULL, NULL,
   'inbound', 'inbound_exception', '+971555550001', 'en', 'failed', NULL, 'no_order_found',
   now() - interval '10 min', now() - interval '8 min'),
  -- V6: partial only (order_ref alone), caller dropped before completing
  (gen_random_uuid(), 'HR-MOCK-V6', NULL, NULL,
   'inbound', 'inbound_exception', '+971500000005', 'en', 'partial', 'wrong_items', NULL,
   now() - interval '5 min', now() - interval '3 min')
ON CONFLICT (happyrobot_call_id) DO NOTHING;

-- ---- verifications (guard: NOT EXISTS on (call_id, attempt_no)) ----
-- V1 — strong pass, attempt 1
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id,
       (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1001'),
       ARRAY['order_ref','name'], ARRAY['order_ref','name'], 'passed', 1, now() - interval '49 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V1'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=1);

-- V2 — fallback pass, attempt 1
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id,
       (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1002'),
       ARRAY['registered_phone','name','delivery_area'], ARRAY['registered_phone','name','delivery_area'],
       'passed', 1, now() - interval '39 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V2'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=1);

-- V3 — attempt 1: only name matched -> partial
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id,
       (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1003'),
       ARRAY['order_ref','name'], ARRAY['name'], 'partial', 1, now() - interval '29 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V3'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=1);

-- V3 — attempt 2: order_ref + name -> passed
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id,
       (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1003'),
       ARRAY['order_ref','name'], ARRAY['order_ref','name'], 'passed', 2, now() - interval '27 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V3'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=2);

-- V4 — four failed attempts (no candidate order; nothing passes)
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id, NULL,
       ARRAY['order_ref','name'], ARRAY[]::text[], 'failed', a.n,
       now() - make_interval(mins => 20 - a.n)
FROM calls c CROSS JOIN (VALUES (1),(2),(3),(4)) AS a(n)
WHERE c.happyrobot_call_id='HR-MOCK-V4'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=a.n);

-- V5 — single failed attempt, ref matches no order
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id, NULL,
       ARRAY['order_ref'], ARRAY[]::text[], 'failed', 1, now() - interval '9 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V5'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=1);

-- V6 — partial: order_ref alone matched (candidate TWIN-1006), name not given
INSERT INTO verifications (verification_id, call_id, order_id, factors_checked, factors_passed, result, attempt_no, created_at)
SELECT gen_random_uuid(), c.call_id,
       (SELECT order_id FROM orders WHERE twin_order_ref='TWIN-1006'),
       ARRAY['order_ref'], ARRAY['order_ref'], 'partial', 1, now() - interval '4 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V6'
  AND NOT EXISTS (SELECT 1 FROM verifications v WHERE v.call_id=c.call_id AND v.attempt_no=1);

-- ---- escalation produced by V4 exceeding the attempt cap ----
INSERT INTO escalations (escalation_id, call_id, order_id, category, reason, status, created_at)
SELECT gen_random_uuid(), c.call_id, NULL, 'verification_failed',
       'exceeded verification attempt cap', 'open', now() - interval '12 min'
FROM calls c WHERE c.happyrobot_call_id='HR-MOCK-V4'
  AND NOT EXISTS (SELECT 1 FROM escalations e WHERE e.call_id=c.call_id);

COMMIT;

-- Quick check:
-- SELECT c.happyrobot_call_id, v.attempt_no, v.result, v.factors_checked, v.factors_passed
--   FROM verifications v JOIN calls c USING (call_id)
--   ORDER BY c.happyrobot_call_id, v.attempt_no;
