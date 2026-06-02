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
                     json={"happyrobot_call_id": "hr-act", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    return {"order_id": ok["order"]["order_id"], "call_id": ok["call_id"]}


def _h(verified):
    return {**HEADERS, "X-Call-Id": verified["call_id"]}


def test_reschedule(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/reschedule", headers=_h(verified),
                    json={"requested_date": _future_working_day(), "requested_window": "09:00-12:00", "reason": "not home"})
    assert r.status_code == 200
    assert r.json()["status"] == "requested"


def test_investigation(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/investigation", headers=_h(verified),
                    json={"type": "not_received"})
    assert r.status_code == 200
    assert r.json()["status"] == "open"
    assert r.json()["callback_due_at"] is not None


def test_merchant_referral(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/merchant-referral", headers=_h(verified),
                    json={"reason": "wrong items"})
    assert r.status_code == 200


def test_address_flag(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/address-flag", headers=_h(verified),
                    json={"correction_text": "Building B not A"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


def test_escalate(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/escalate", headers=_h(verified),
                    json={"category": "complaint", "reason": "angry customer"})
    assert r.status_code == 200


def test_fallback_never_carries_otp(client, verified):
    r = client.post(f"/orders/{verified['order_id']}/fallback-message", headers=_h(verified),
                    json={"channel": "whatsapp", "content_type": "tracking_link"})
    assert r.status_code == 200
    # content_type other than tracking_link/notice is rejected
    bad = client.post(f"/orders/{verified['order_id']}/fallback-message", headers=_h(verified),
                      json={"channel": "sms", "content_type": "otp"})
    assert bad.status_code == 422


def test_reschedule_rejects_past_date(client, verified):
    past = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    r = client.post(f"/orders/{verified['order_id']}/reschedule", headers=_h(verified),
                    json={"requested_date": past})
    assert r.status_code == 422


def test_reschedule_rejects_weekend(client, verified):
    # find the next Saturday
    d = dt.date.today() + dt.timedelta(days=1)
    while d.weekday() != 5:
        d += dt.timedelta(days=1)
    r = client.post(f"/orders/{verified['order_id']}/reschedule", headers=_h(verified),
                    json={"requested_date": d.isoformat()})
    assert r.status_code == 422
