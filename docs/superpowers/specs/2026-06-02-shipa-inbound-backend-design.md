# Shipa Inbound Voice Backend — Design Spec

> Status: **approved for implementation planning** (2026-06-02).
> Scope: backend only, inbound exception handler only. Dashboard frontend deferred (its read API is in scope).
> Source documents: `draft.md`, `database_schema.md`.

## 1. Goal

Build the backend that the **inbound exception-handler voice agent** (running on HappyRobot) calls into. The backend owns all data and actions; HappyRobot owns the conversation. The agent answers a customer call, the backend **verifies the caller**, then lets the agent read status and take resolution actions (reschedule, investigation, escalation, address flag, merchant referral, fallback message) and log a disposition.

Out of scope for this build: the outbound-confirmation agent, the React/Next.js dashboard UI, real Twin integration. The pilot runs on seeded mock data shaped like the real Twin feed.

## 2. Safety principles (non-negotiable)

These are the spine of the design. Every endpoint and service is built around them.

1. **Verify before disclosing or acting.** No order detail is returned and no write action is taken until `verify_caller` has returned `passed` for that call. Before a pass, the backend holds the agent at arm's length — there is nothing to leak because nothing is disclosed. This is enforced in the service layer (a shared guard), not left to the prompt.
2. **OTP discipline.** The `otp_code` is treated as a secret. It is never returned by dashboard read endpoints, never written to stored transcripts (scrubbed where present), and only returned to the agent through a tightly scoped path for a *verified* caller. It is never sent over the SMS/WhatsApp fallback channel.
3. **PII minimization.** `full_name`, `primary_phone`, `delivery_address` are restricted in API responses to the minimum the caller-facing flow needs. Dashboard reads expose only what ops needs to action a queue.
4. **Attempt capping.** Verification is capped at 3 attempts per call; the 4th triggers an automatic escalation with category `verification_failed`. This prevents brute-forcing the verification gate over a single call.
5. **Authenticated endpoints.** Tool endpoints require a webhook shared secret; dashboard endpoints require an API key. No endpoint is open to the world.
6. **Idempotency.** Agent retries during a live call must not create duplicate cases, reschedules, or escalations. Enforced at the database level.

When a safety principle and a convenience trade off, safety wins. Where a control is deferred (see §8), it is deferred explicitly with a stated reason, never silently dropped.

## 3. Architecture

Layered FastAPI service: `routers → services → models`, with Twin behind an adapter.

```
HappyRobot agent ──webhook(+secret)──▶ FastAPI tool router ──▶ services ──▶ SQLAlchemy models ──▶ Postgres
                                            │                     │
                                       (auth dep)           TwinClient (Protocol)
                                                                  └─ MockTwinClient (seeded)  ← real client later
Ops dashboard ──API key──▶ dashboard read router ──▶ services ──▶ Postgres
```

- **HTTP layer stays thin:** parse + validate (Pydantic), authenticate, call a service, return a filtered response model.
- **All business logic lives in services**, so `verify_caller` and the action logic are plain Python, testable without a web server.
- **Twin is the only formalized adapter boundary** — it is the known future swap. No hexagonal/ports-everywhere over-engineering for a pilot.

## 4. Project structure

```
shipa_delivery_agent/
├── pyproject.toml            # deps + ruff + pytest config (managed with uv)
├── .env.example              # DATABASE_URL, WEBHOOK_SECRET, DASHBOARD_API_KEY
├── docker-compose.yml        # local Postgres, mirrors Railway managed PG
├── alembic.ini
├── migrations/               # alembic versions
├── app/
│   ├── main.py               # app factory, router mount, health check
│   ├── config.py             # pydantic-settings
│   ├── db.py                 # engine + session factory
│   ├── deps.py               # DB session dep, webhook-auth dep, api-key dep
│   ├── enums.py              # status / intent / disposition / verification_status / category enums
│   ├── security.py           # auth checks, OTP/PII response filtering & transcript scrubbing
│   ├── models/
│   │   ├── read.py           # customers, orders (Twin-synced read side)
│   │   ├── calls.py          # calls (the spine)
│   │   └── operations.py     # verifications, reschedules, investigations, escalations,
│   │                         #   address_flags, fallback_messages, merchant_referrals
│   ├── schemas/              # Pydantic request + response models per endpoint
│   ├── routers/
│   │   ├── tools.py          # agent contract endpoints (webhook auth)
│   │   └── dashboard.py      # read endpoints (api-key auth)
│   ├── services/
│   │   ├── verification.py   # verify_caller matching + policy (heaviest tests)
│   │   ├── guard.py          # "verified for this call?" gate used by all action services
│   │   ├── orders.py         # status lookup
│   │   ├── actions.py        # reschedule / investigation / referral / address-flag / escalate / fallback
│   │   ├── calls.py          # call creation + disposition logging
│   │   └── metrics.py        # dashboard metrics aggregation
│   └── twin/
│       ├── base.py           # TwinClient Protocol
│       ├── mock.py           # MockTwinClient + seed dataset
│       └── sync.py           # upsert orders/customers on twin_order_ref / phone
└── tests/
    ├── conftest.py           # Postgres fixtures (create/drop), client, seed
    ├── test_verification.py  # the policy matrix — most coverage
    ├── test_guard.py         # unverified calls cannot read/act
    ├── test_tools.py         # endpoint contract + auth
    ├── test_idempotency.py   # retries are no-ops
    └── test_dashboard.py     # reads never leak OTP/PII
```

Models are grouped by role (read side / spine / operations) rather than one-file-per-table, to keep related tables and their relationships readable together.

## 5. The endpoint contract (inbound subset)

**Agent tools — webhook shared-secret auth:**

| Method & path | Tool | Notes |
|---|---|---|
| `POST /verify` | `verify_caller` | Called first. Gates everything else. Returns `passed`/`partial`/`failed` + matched order **only on pass**. |
| `GET /orders/{id}/status` | status + ETA | Requires verified call. |
| `POST /orders/{id}/reschedule` | new date back to Twin | Validates future working day. Idempotent per call. |
| `POST /orders/{id}/investigation` | open "not received" case | Sets callback-due SLA. Idempotent per call. |
| `POST /orders/{id}/merchant-referral` | log contents issue | Idempotent per call. |
| `POST /orders/{id}/address-flag` | flag address correction | Idempotent per call. |
| `POST /orders/{id}/escalate` | hand off to human | Idempotent per call. |
| `POST /orders/{id}/fallback-message` | trigger SMS/WhatsApp | `tracking_link`/`notice` only — never the OTP. |
| `POST /calls/{id}/disposition` | log single outcome + CSAT | One per call, ends the call. |

A `call` row is created at call start (`POST /calls` or implicit on first `/verify`) so every operational row can link back to it.

**Dashboard reads — API-key auth:** `GET /calls`, `GET /investigations`, `GET /reschedules`, `GET /escalations`, `GET /metrics` (first-attempt rate, call-deflection rate, CSAT, average handle time). All read responses are filtered through the OTP/PII rules in §2.

`/reattempt` from the full contract is omitted as an endpoint (it's the outbound driver-no-contact path), but `re_attempt_scheduled` remains a valid disposition enum value.

## 6. `verify_caller` — the gate

A standalone service in `verification.py` with an explicit, configurable policy. Default policy:

- **Pass** when either:
  - `order_ref` matches **AND** `name` matches; **or**
  - `registered_phone` matches **AND** `name` matches **AND** `delivery_area` matches (the marketplace "no order ref" fallback).
- **Partial:** some factors match but not a passing combination → agent collects more.
- **Failed:** no usable match.
- **Attempt cap:** 3 attempts per call; the next attempt auto-escalates (`verification_failed`).

Matching is **normalized and fuzzy on free-text fields** (name, area) because input arrives via voice STT — case-folded, whitespace-collapsed, accent-stripped, with a token-overlap / edit-distance threshold. `order_ref` and `phone` are normalized then compared exactly. Each attempt writes a `verifications` row (`factors_checked`, `factors_passed`, `result`, `attempt_no`) for later tuning. The matched order is attached to the `call` and returned **only on pass**.

The default policy and thresholds are constants in one place so the real verification policy (draft open question #4) can be tuned without touching control flow. This module gets the heaviest test coverage — a full matrix of factor combinations and adversarial near-misses.

## 7. Idempotency

Each action table (`reschedules`, `investigations`, `escalations`, `address_flags`, `merchant_referrals`) carries a **unique partial index on `call_id`** — at most one of each per call. The POST handlers **return the existing row on conflict** rather than erroring, so an agent retry mid-call is a safe no-op returning the same result. `disposition` is likewise one-per-call (enforced on the `calls` row). This is simpler and DB-enforced versus a general idempotency-key store, which is overkill for the pilot.

## 8. Twin, security, deferrals

- **Twin adapter:** `TwinClient` Protocol + `MockTwinClient` seeded with realistic orders (Amazon/Temu/Trendyol; statuses across the enum; OTPs; emirate areas; expected pieces). `sync.py` upserts `orders` on `twin_order_ref` and derives `customers` (dedupe on phone). The real client implements the same Protocol later with zero service changes. For OTP and status the design assumes a **live pull at call start** so the agent never reads a stale code; the mock simulates this.
- **Auth:** `WEBHOOK_SECRET` (constant-time compare) for tool endpoints; `DASHBOARD_API_KEY` for reads. Both via `deps.py`.
- **OTP/PII filtering:** response models for dashboard reads exclude `otp_code` and minimize PII; a transcript-scrub helper strips OTP patterns before persistence.
- **Explicitly deferred (with reasons), not dropped:**
  - *Column-level encryption at rest* — deferred in favor of response/transcript filtering for the pilot; revisit before real PII flows. Tracked, not silent.
  - *UAE data-residency hosting decision* — flagged; affects where Railway/Postgres live, decided before go-live.
  - *Real Twin integration, WhatsApp/SMS provider* — Phase 3.

## 9. Testing

pytest against a **real Postgres** (docker-compose), because the schema uses PG-specific types (`uuid`, `text[]`, `tstzrange`). Fixtures create/drop tables per test session and seed mock data. Priority coverage, in order: (1) `verify_caller` policy matrix, (2) the verification guard — unverified calls cannot read order detail or take actions, (3) dashboard reads never leak OTP/PII, (4) idempotency — retries are no-ops, (5) endpoint auth.

## 10. Tooling

- **uv** for env + dependency management (the `.venv`).
- **SQLAlchemy 2.0** (typed) + **Alembic** migrations.
- **Pydantic v2** / **pydantic-settings** for schemas + config.
- **ruff** for lint/format, **pytest** for tests.
- **docker-compose** for local Postgres; Railway managed Postgres in deployment.
