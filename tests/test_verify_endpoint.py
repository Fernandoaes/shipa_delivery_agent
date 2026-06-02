import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def test_verify_requires_auth(client, seeded):
    r = client.post("/verify", json={"happyrobot_call_id": "hr-x", "name": "Aisha Khan", "order_ref": "TWIN-1001"})
    assert r.status_code == 401


def test_verify_pass_returns_order(client, seeded):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": "hr-1", "name": "Aisha Khan", "order_ref": "TWIN-1001"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"] == "passed"
    assert body["order"]["twin_order_ref"] == "TWIN-1001"
    assert "otp_code" not in body["order"]   # safety: OTP never in verify response


def test_verify_fail_hides_order(client, seeded):
    r = client.post("/verify", headers=HEADERS,
                    json={"happyrobot_call_id": "hr-2", "name": "Nobody", "order_ref": "NOPE"})
    assert r.status_code == 200
    assert r.json()["result"] == "failed"
    assert r.json()["order"] is None
