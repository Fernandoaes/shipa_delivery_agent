# Shipa Inbound Voice Backend

FastAPI backend for the Shipa inbound exception-handler voice agent. See
`docs/superpowers/specs/2026-06-02-shipa-inbound-backend-design.md` for the design.

## Setup
```bash
docker compose up -d db          # local Postgres
cp .env.example .env
uv sync
uv run alembic upgrade head      # apply schema
uv run uvicorn app.main:app --reload
```

## Seed mock orders
```bash
uv run python -c "from app.db import SessionLocal; from app.twin.mock import MockTwinClient; from app.twin.sync import upsert_orders; s=SessionLocal(); upsert_orders(s, MockTwinClient().fetch_all()); s.commit()"
```

## Test
```bash
uv run pytest -v
```

## Auth
- Agent tool + ingest endpoints: `X-Webhook-Secret` header (`WEBHOOK_SECRET`).
- Dashboard read endpoints: `X-API-Key` header (`DASHBOARD_API_KEY`).
- Gated endpoints additionally require an `X-Call-Id` header pointing at a verified call.

## Safety invariants
- Order detail/actions require `verify_caller` == passed (enforced by `require_verified_call`).
- OTP never appears in responses or stored transcripts, never on the fallback channel.
- Verification capped at 3 attempts, then auto-escalates.
- Write actions are idempotent per call.
