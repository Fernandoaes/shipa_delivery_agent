import datetime as dt

import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _future_working_day(days_ahead: int = 7) -> str:
    d = dt.date.today() + dt.timedelta(days=days_ahead)
    while d.weekday() >= 5:  # bump Sat/Sun to Monday
        d += dt.timedelta(days=1)
    return d.isoformat()

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def verified(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    ok = client.post("/verify", headers=HEADERS,
                     json={"happyrobot_call_id": "hr-idem", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    return {"order_id": ok["order"]["order_id"], "call_id": ok["call_id"]}


def test_reschedule_retry_is_noop(client, verified):
    h = {**HEADERS, "X-Call-Id": verified["call_id"]}
    body = {"requested_date": _future_working_day()}
    first = client.post(f"/orders/{verified['order_id']}/reschedule", headers=h, json=body).json()
    second = client.post(f"/orders/{verified['order_id']}/reschedule", headers=h, json=body).json()
    assert first["reschedule_id"] == second["reschedule_id"]   # same row, not a duplicate


def test_investigation_retry_is_noop(client, verified):
    h = {**HEADERS, "X-Call-Id": verified["call_id"]}
    first = client.post(f"/orders/{verified['order_id']}/investigation", headers=h, json={"type": "not_received"}).json()
    second = client.post(f"/orders/{verified['order_id']}/investigation", headers=h, json={"type": "not_received"}).json()
    assert first["investigation_id"] == second["investigation_id"]
