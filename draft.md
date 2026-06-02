# Shipa Voice Automation — Implementation Draft

> Status: **draft for discussion**. Captures the proposed architecture so we can challenge it before committing. Open questions are at the bottom.
>
> Related documents: `shipa_database_schema.md` (full table spec), `shipa_outbound_confirmation_prompt.md`, `shipa_inbound_exception_prompt.md` (agent prompts).

## 1. What we're building

Two voice agents for Shipa's last-mile delivery operation, plus the system they talk to:

1. **Outbound delivery confirmation agent** — proactively calls customers before a delivery attempt, confirms address + availability, reschedules or reads out the delivery code.
2. **Inbound exception handler** — answers customer calls, **verifies the caller**, classifies the issue (tracking, not received, failed delivery, wrong items, reschedule, cancel), and resolves or escalates.

Both run on HappyRobot. Both call into a shared backend for data. An ops dashboard sits on top for visibility.

## 2. The stack

| Layer | Tech | Hosted on | Built with |
|---|---|---|---|
| Voice agents + telephony + STT/TTS | HappyRobot platform | HappyRobot | HappyRobot workflow builder |
| Backend API + business logic | (proposed) Node/Express **or** Python/FastAPI | Railway | Claude Code |
| Database | PostgreSQL | Railway (managed Postgres) | Claude Code (schema + migrations) |
| Ops dashboard (frontend) | React / Next.js | Railway | Claude Code |

The idea: HappyRobot owns the *conversation*; our backend owns the *data and the actions*; the dashboard gives Shipa ops a window into both. Railway hosts everything we build (frontend, backend, DB as Railway services), so we have one deploy target.

**Two design principles we're holding to:**
- **No business logic in HappyRobot.** The agent calls a tool (`verify_caller`, `reschedule`, `open_investigation`); the backend decides what that means. Keeps the prompts thin and the logic testable in Claude Code.
- **Verify before disclosing or acting.** The inbound agent shares no order detail and takes no write action until `verify_caller` returns `passed`. This is the same safety principle as the OTP guardrail, applied to the whole inbound flow.

## 3. How it fits together

```
Customer phone  ──▶  HappyRobot agent  ──webhooks/tools──▶  Backend API (Railway)  ──▶  Postgres (Railway)
                          │                                        ▲
                          │                                        │
                     STT / TTS / LLM                         Ops dashboard (Railway) ── Shipa ops users
                                                                   │
                                              Twin (Shipa order source) ──sync──┘
                                              WhatsApp / SMS provider ◀── fallback
```

Flow in words: a call comes in (or Twin triggers an outbound call). The HappyRobot agent runs the conversation and, whenever it needs to verify a caller, read status, or take an action (reschedule, open an investigation), it calls a webhook on our backend. The backend reads/writes Postgres — which is kept in sync from **Twin** — and returns a result the agent can speak. Every call ends by writing a disposition row. The dashboard reads from the same backend so ops can action investigations, escalations, and reschedules, and watch the metrics.

## 4. Backend (Claude Code)

### Responsibilities
- Expose the **tool endpoints** the HappyRobot agents call.
- Hold the **order data** the agents need, synced from **Twin** (or seeded with mock data for the pilot).
- Own the **verification logic** — match caller-supplied key terms against Twin-sourced orders.
- Record **calls, verifications, dispositions, investigations, escalations, reschedules**.
- Serve the **dashboard** read/write API.

### Data model
Full field-level spec — columns, types, primary/foreign keys, enums — lives in `shipa_database_schema.md`. In short:

- **Read side (synced from Twin):** `customers`, `orders`. Orders are keyed by `twin_order_ref`, which is also the **verification lookup key**.
- **Write side (created by the agent + dashboard):** `calls`, `verifications`, `reschedules`, `investigations`, `escalations`, `address_flags`, `fallback_messages`, `merchant_referrals`. Every operational row links back to the `call` that produced it.

### Tool endpoints (the agent ↔ backend contract)
These map 1:1 to the tools in the agent prompts.

- `POST /verify` → **verify_caller**: takes the key terms the agent extracted from the call (`order_ref`, `name`, optionally registered phone / delivery area / item); looks the order up and validates the match; returns `passed` / `partial` / `failed` **and the matched order on pass**. *(inbound — called first, gates everything else)*
- `GET  /orders/{id}/status` → current status + ETA
- `POST /orders/{id}/reschedule` → write a new date back to Twin
- `POST /orders/{id}/reattempt` → schedule a priority re-attempt; log driver no-contact
- `POST /orders/{id}/investigation` → open a "not received" case with a callback SLA
- `POST /orders/{id}/merchant-referral` → log a contents issue referred to the merchant
- `POST /orders/{id}/address-flag` → flag an address correction for ops
- `POST /orders/{id}/escalate` → hand off to a human
- `POST /orders/{id}/fallback-message` → trigger SMS/WhatsApp (tracking link, never the OTP)
- `POST /calls/{id}/disposition` → log the single outcome + CSAT at end of call

Write endpoints should be **idempotent per call** so an agent retry doesn't create duplicate reschedules or cases.

### Dashboard endpoints
- `GET /calls`, `GET /investigations`, `GET /reschedules`, `GET /escalations`
- `GET /metrics` → first-attempt rate, call-deflection rate, CSAT, average handle time

## 5. Frontend / ops dashboard (Railway)

The window for Shipa's operations team. Minimum useful version:
- **Call log** — every call, direction, language, verification result, disposition, link to recording/transcript.
- **Investigations queue** — "delivered but not received" cases to action, with callback-due timers.
- **Escalations** — handoffs from either agent.
- **Reschedules** — captured new dates, and whether they synced to Twin.
- **Metrics** — the success numbers we're judged on (first-attempt rate, deflection, CSAT, AHT).

Read-only is enough for the pilot; write actions (resolve an investigation, reassign an escalation) come once the queues are real.

## 6. Integrations to nail down

- **Twin (order source)** — the biggest dependency. We need orders (and their live status + OTP) flowing into our backend, and a way for `verify_caller` to look them up by reference. Options: a real-time API, a webhook, or a batch/CSV sync. For the pilot we can run on seeded mock data shaped like the real Twin feed.
- **WhatsApp / SMS** — customers already share WhatsApp locations and get WhatsApp delivery notices, so this is part of the no-answer fallback. Need to know their existing provider.
- **CSAT** — they already run an "evaluate the system" prompt at call end; we mirror that and store the score.

## 7. Security & data handling

- **Webhook auth** between HappyRobot and the backend — shared secret or signed requests. The tool endpoints must not be open to the world.
- **Caller verification** — disclosure and write actions are gated on `verify_caller` returning `passed`. The agent holds no order data before that, so there is nothing to leak early. Verification is capped at 3 attempts, then escalates.
- **OTP discipline** — the code is read aloud only to a verified customer (outbound: after identity + address are confirmed), never to voicemail or a third party. On our side, restrict where it's returned and keep it out of stored transcripts where possible.
- **PII** — name, phone, address. Encrypt at rest, access-control the dashboard, set a retention policy on recordings/transcripts.
- **Data residency** — UAE. Worth checking whether Shipa requires data to stay in-region (affects where Railway/Postgres and recordings live). Flagging early because it can constrain the whole hosting choice.

## 8. Suggested build phases

- **Phase 0 — data contract.** Agree with Shipa how we get orders from Twin (API / webhook / batch), who owns the OTP, and the verification policy (accepted key-term combinations). Define the mock data shape.
- **Phase 1 — backend + outbound.** Claude Code scaffolds backend, schema, and tool endpoints against mock Twin data. Build the outbound agent in HappyRobot. Dashboard shows a read-only call log.
- **Phase 2 — inbound.** Add the inbound agent + `verify_caller` matching logic, classification, investigations, escalations, and EN/AR handling. Dashboard gets the queues.
- **Phase 3 — go-live.** Real Twin integration, WhatsApp/SMS fallback, metrics dashboard, limited pilot on real traffic.

## 9. Open questions / decisions

1. **Twin access** — real-time API, webhook, or batch? And can `verify_caller` query it by order reference fast enough for a live call? This gates Phase 3.
2. **OTP source of truth** — does it live in Twin, or do we generate/store it?
3. **Hosting** — is everything we build on Railway, or do backend/DB need to sit elsewhere (e.g. for UAE data residency)?
4. **Verification policy** — the key decision for inbound. Which key-term combinations pass? (e.g. order ref + name; registered phone read aloud + name + area.) And how do we handle the common case where a marketplace customer **doesn't have their order reference** — letting them read out the registered phone number is the most useful fallback. This ruleset lives in `verify_caller`, not the prompt.
5. **Arabic** — TTS/STT quality and dialect; how we read codes and references phonetically in Arabic.
6. **Dashboard auth** — how Shipa ops users log in, and what they're allowed to see/do.
7. **Scope of phase 1** — outbound only, or both agents from the start? (They share the backbone, so the cost delta is smaller than it looks.)