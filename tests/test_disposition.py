import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}


@pytest.fixture()
def verified(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    return client.post("/verify", headers=HEADERS,
                       json={"happyrobot_call_id": "hr-disp", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()


def test_disposition_sets_outcome_and_ends_call(client, verified):
    cid = verified["call_id"]
    r = client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                    json={"disposition": "resolved_info", "intent": "tracking", "csat_score": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["disposition"] == "resolved_info"
    assert body["ended_at"] is not None


def test_disposition_scrubs_otp_from_transcript(client, verified):
    cid = verified["call_id"]
    r = client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                    json={"disposition": "resolved_info", "transcript": "your code is 4821 thanks"})
    assert r.status_code == 200
    assert "4821" not in r.json()["transcript"]


def test_disposition_requires_webhook_secret(client, verified):
    # Pins the router-level auth so a refactor can't silently expose this write endpoint.
    cid = verified["call_id"]
    r = client.post(f"/calls/{cid}/disposition", json={"disposition": "resolved_info"})
    assert r.status_code == 401


def test_disposition_is_one_per_call(client, verified):
    cid = verified["call_id"]
    client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                json={"disposition": "resolved_info", "csat_score": 5})
    # a second, different disposition must NOT overwrite the first
    second = client.post(f"/calls/{cid}/disposition", headers=HEADERS,
                         json={"disposition": "escalated", "csat_score": 1}).json()
    assert second["disposition"] == "resolved_info"
    assert second["csat_score"] == 5
