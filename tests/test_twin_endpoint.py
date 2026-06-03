import datetime as dt

import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

WEBHOOK = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


def _future_working_day() -> dt.date:
    d = dt.date.today() + dt.timedelta(days=7)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


@pytest.fixture()
def seeded(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def test_twin_orders_requires_webhook_secret(client, seeded):
    assert client.get("/twin/orders").status_code == 401


def test_twin_orders_lists_seeded_orders(client, seeded):
    r = client.get("/twin/orders", headers=WEBHOOK)
    assert r.status_code == 200
    refs = {o["twin_order_ref"] for o in r.json()}
    assert {"TWIN-1001", "TWIN-1002", "TWIN-1003"} <= refs


def test_twin_orders_never_leaks_otp_or_address(client, seeded):
    r = client.get("/twin/orders", headers=WEBHOOK)
    assert r.status_code == 200
    assert r.json()
    for o in r.json():
        assert "otp_code" not in o
        assert "delivery_address" not in o


def test_twin_orders_reflects_reschedule(client, seeded):
    ok = client.post("/verify", headers=WEBHOOK,
                     json={"happyrobot_call_id": "hr-twin", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    new_date = _future_working_day()
    rs = client.post(f"/orders/{ok['order']['order_id']}/reschedule",
                     headers={**WEBHOOK, "X-Call-Id": ok["call_id"]},
                     json={"requested_date": new_date.isoformat()})
    assert rs.status_code == 200

    r = client.get("/twin/orders", headers=WEBHOOK)
    row = next(o for o in r.json() if o["twin_order_ref"] == "TWIN-1001")
    assert row["reschedule_requested_date"] == new_date.isoformat()


def test_twin_orders_reflects_escalation(client, seeded):
    ok = client.post("/verify", headers=WEBHOOK,
                     json={"happyrobot_call_id": "hr-twin-esc", "name": "Omar Al Farsi", "order_ref": "TWIN-1002"}).json()
    es = client.post(f"/orders/{ok['order']['order_id']}/escalate",
                     headers={**WEBHOOK, "X-Call-Id": ok["call_id"]},
                     json={"category": "complaint"})
    assert es.status_code == 200

    r = client.get("/twin/orders", headers=WEBHOOK)
    row = next(o for o in r.json() if o["twin_order_ref"] == "TWIN-1002")
    assert row["escalated"] is True
