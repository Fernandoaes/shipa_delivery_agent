import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

WEBHOOK = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}
APIKEY = {"X-API-Key": "dev-dashboard-key-change-me"}


@pytest.fixture()
def with_activity(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    ok = client.post("/verify", headers=WEBHOOK,
                     json={"happyrobot_call_id": "hr-dash", "name": "Aisha Khan", "order_ref": "TWIN-1001"}).json()
    client.post(f"/orders/{ok['order']['order_id']}/investigation",
                headers={**WEBHOOK, "X-Call-Id": ok["call_id"]}, json={"type": "not_received"})
    client.post(f"/calls/{ok['call_id']}/disposition", headers=WEBHOOK,
                json={"disposition": "investigation_opened", "intent": "not_received", "csat_score": 4})
    return ok


def test_dashboard_requires_api_key(client, with_activity):
    assert client.get("/calls").status_code == 401


def test_calls_list_hides_otp(client, with_activity):
    r = client.get("/calls", headers=APIKEY)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert "otp_code" not in r.json()[0]


def test_investigations_list(client, with_activity):
    r = client.get("/investigations", headers=APIKEY)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "open"


def test_metrics_shape(client, with_activity):
    r = client.get("/metrics", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    for key in ("total_calls", "first_attempt_success", "on_time_rate", "active_deliveries",
                "at_risk", "containment_rate", "recovery_rate", "avg_csat", "avg_handle_time_seconds"):
        assert key in body
