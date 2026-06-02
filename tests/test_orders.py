import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def _verify(client, ref="TWIN-1001", name="Aisha Khan", call_id="hr-status"):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": call_id, "name": name, "order_ref": ref})
    return r.json()


def test_status_requires_verified_call(client, seeded):
    # Make an order id available but use a fresh unverified call header
    body = _verify(client, name="Nobody", ref="NOPE", call_id="hr-unv")
    cid = body["call_id"]
    # find any order id via a passing verify on a different call
    ok = _verify(client, call_id="hr-ok")
    order_id = ok["order"]["order_id"]
    r = client.get(f"/orders/{order_id}/status", headers={**HEADERS, "X-Call-Id": cid})
    assert r.status_code == 403


def test_status_returns_for_verified(client, seeded):
    ok = _verify(client, call_id="hr-ok2")
    order_id = ok["order"]["order_id"]
    cid = ok["call_id"]
    r = client.get(f"/orders/{order_id}/status", headers={**HEADERS, "X-Call-Id": cid})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"pending", "out_for_delivery", "delivered", "failed", "rescheduled", "returned", "cancelled"}
    assert "otp_code" not in body
