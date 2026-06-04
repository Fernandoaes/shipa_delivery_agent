WH = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}
API = {"X-API-Key": "dev-dashboard-key-change-me"}

ORDER = {
    "orders": [
        {
            "twin_order_ref": "TWIN-7001", "customer_name": "Sara Khan",
            "customer_phone": "+971500007001", "merchant": "Noon", "status": "pending",
            "delivery_address": "Flat 4, Deira", "delivery_area": "Deira", "otp_code": "1234",
        }
    ]
}


def _seed_order(client):
    assert client.post("/orders/sync", headers=WH, json=ORDER).status_code == 200


def test_action_sync_requires_auth(client):
    assert client.post("/escalations/sync", json={"escalations": []}).status_code == 401


def test_reschedule_sync_upserts_and_shows(client):
    _seed_order(client)
    payload = {"reschedules": [{
        "happyrobot_call_id": "HR-R1", "twin_order_ref": "TWIN-7001",
        "requested_date": "2020-01-06", "status": "requested",  # past date allowed in sync
    }]}
    r = client.post("/reschedules/sync", headers=WH, json=payload)
    assert r.status_code == 200 and r.json()["upserted"] == 1
    # replay updates the same row (one-per-call)
    payload["reschedules"][0]["status"] = "confirmed"
    assert client.post("/reschedules/sync", headers=WH, json=payload).json()["upserted"] == 1

    listed = client.get("/reschedules", headers=API).json()
    assert len(listed) == 1 and listed[0]["status"] == "confirmed"


def test_escalation_sync_without_order(client):
    payload = {"escalations": [{"happyrobot_call_id": "HR-E1", "category": "cancel", "reason": "no longer needed"}]}
    r = client.post("/escalations/sync", headers=WH, json=payload)
    assert r.status_code == 200
    listed = client.get("/escalations", headers=API).json()
    assert listed[0]["category"] == "cancel"


def test_escalation_sync_rejects_bad_category(client):
    bad = {"escalations": [{"happyrobot_call_id": "HR-E2", "category": "nonsense"}]}
    assert client.post("/escalations/sync", headers=WH, json=bad).status_code == 422


def test_investigation_sync_shows_on_dashboard(client):
    _seed_order(client)
    payload = {"investigations": [{
        "happyrobot_call_id": "HR-I1", "twin_order_ref": "TWIN-7001",
        "type": "not_received", "status": "resolved", "resolution_notes": "found at neighbour",
    }]}
    assert client.post("/investigations/sync", headers=WH, json=payload).status_code == 200
    listed = client.get("/investigations", headers=API).json()
    assert listed[0]["status"] == "resolved"


def test_sync_rejects_unknown_order(client):
    payload = {"merchant_referrals": [{"happyrobot_call_id": "HR-M1", "twin_order_ref": "NOPE"}]}
    r = client.post("/merchant-referrals/sync", headers=WH, json=payload)
    assert r.status_code == 400
    assert "NOPE" in r.json()["detail"]


def test_merchant_referral_and_address_flag_show(client):
    _seed_order(client)
    assert client.post("/merchant-referrals/sync", headers=WH, json={
        "merchant_referrals": [{"happyrobot_call_id": "HR-M2", "twin_order_ref": "TWIN-7001", "reason": "refund"}]
    }).status_code == 200
    assert client.post("/address-flags/sync", headers=WH, json={
        "address_flags": [{"happyrobot_call_id": "HR-A1", "twin_order_ref": "TWIN-7001",
                           "correction_text": "Flat 5 not 4"}]
    }).status_code == 200

    refs = client.get("/merchant-referrals", headers=API).json()
    flags = client.get("/address-flags", headers=API).json()
    assert refs[0]["reason"] == "refund"
    assert flags[0]["original_address"] == "Flat 4, Deira"  # defaulted from the order
    assert flags[0]["correction_text"] == "Flat 5 not 4"


def test_fallback_message_sync_is_idempotent_per_channel_type(client):
    _seed_order(client)
    payload = {"fallback_messages": [{
        "happyrobot_call_id": "HR-F1", "twin_order_ref": "TWIN-7001",
        "channel": "sms", "content_type": "tracking_link", "status": "queued",
    }]}
    assert client.post("/fallback-messages/sync", headers=WH, json=payload).status_code == 200
    payload["fallback_messages"][0]["status"] = "sent"
    assert client.post("/fallback-messages/sync", headers=WH, json=payload).status_code == 200

    msgs = client.get("/fallback-messages", headers=API).json()
    assert len(msgs) == 1 and msgs[0]["status"] == "sent"


def test_action_sync_auto_creates_call_and_links_order(client):
    _seed_order(client)
    payload = {"reschedules": [{
        "happyrobot_call_id": "HR-NEW", "twin_order_ref": "TWIN-7001", "requested_date": "2020-02-03",
    }]}
    assert client.post("/reschedules/sync", headers=WH, json=payload).status_code == 200
    # stub call was created and linked to the order
    calls = client.get("/calls", headers=API).json()
    new = [c for c in calls if c["twin_order_ref"] == "TWIN-7001"]
    assert len(new) == 1
