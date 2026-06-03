HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}

ORDER_PAYLOAD = {
    "orders": [
        {
            "twin_order_ref": "TWIN-3001", "customer_name": "Omar Said",
            "customer_phone": "+971500000123", "merchant": "Noon", "status": "pending",
            "delivery_address": "Villa 12, Mirdif", "delivery_area": "Mirdif", "otp_code": "9090",
        }
    ]
}

CALL_PAYLOAD = {
    "calls": [
        {
            "happyrobot_call_id": "HR-CALL-1",
            "direction": "inbound",
            "caller_number": "+971500000123",
            "language": "en",
            "intent": "tracking",
            "disposition": "resolved_info",
            "csat_score": 4.5,
            "notes": "customer reassured",
        }
    ]
}


def test_calls_sync_requires_auth(client):
    assert client.post("/calls/sync", json=CALL_PAYLOAD).status_code == 401


def test_calls_sync_upserts(client):
    r = client.post("/calls/sync", headers=HEADERS, json=CALL_PAYLOAD)
    assert r.status_code == 200
    assert r.json()["upserted"] == 1
    # replay with same happyrobot_call_id updates, not duplicates
    r2 = client.post("/calls/sync", headers=HEADERS, json=CALL_PAYLOAD)
    assert r2.json()["upserted"] == 1

    # replay updated the same row instead of duplicating it
    listed = client.get("/calls", headers={"X-API-Key": "dev-dashboard-key-change-me"})
    assert listed.status_code == 200
    matching = [c for c in listed.json() if c.get("intent") == "tracking"]
    assert len(matching) == 1


def test_calls_sync_rejects_bad_disposition(client):
    bad = {"calls": [{"happyrobot_call_id": "HR-CALL-2", "disposition": "not_a_real_value"}]}
    assert client.post("/calls/sync", headers=HEADERS, json=bad).status_code == 422


def test_calls_sync_links_order_and_scrubs_otp(client):
    client.post("/orders/sync", headers=HEADERS, json=ORDER_PAYLOAD)
    payload = {
        "calls": [
            {
                "happyrobot_call_id": "HR-CALL-3",
                "twin_order_ref": "TWIN-3001",
                "transcript": "your code is 9090 thanks",
            }
        ]
    }
    r = client.post("/calls/sync", headers=HEADERS, json=payload)
    assert r.status_code == 200
    # OTP must not survive in stored transcript
    assert "9090" not in r.text
    listed = client.get(
        "/calls", headers={"X-API-Key": "dev-dashboard-key-change-me"}
    )
    linked = [c for c in listed.json() if c.get("twin_order_ref") == "TWIN-3001"]
    assert len(linked) == 1
