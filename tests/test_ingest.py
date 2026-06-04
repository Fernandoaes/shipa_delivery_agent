HEADERS = {"X-Webhook-Secret": "dev-webhook-secret-change-me"}

PAYLOAD = {
    "orders": [
        {
            "twin_order_ref": "TWIN-2001", "customer_name": "Layla Hassan",
            "customer_phone": "+971500000099", "merchant": "Amazon", "status": "pending",
            "delivery_address": "Apt 9, JLT Cluster C", "delivery_area": "JLT", "otp_code": "5555",
        }
    ]
}


def test_ingest_requires_auth(client):
    assert client.post("/orders/sync", json=PAYLOAD).status_code == 401


def test_ingest_upserts_orders(client):
    r = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert r.status_code == 200
    assert r.json()["upserted"] == 1
    # second push is an update, not a duplicate
    r2 = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert r2.json()["upserted"] == 1


def test_ingest_response_excludes_otp(client):
    r = client.post("/orders/sync", headers=HEADERS, json=PAYLOAD)
    assert "otp_code" not in r.text
    assert "5555" not in r.text


def test_ingest_accepts_coordinates(client):
    payload = {"orders": [{**PAYLOAD["orders"][0], "twin_order_ref": "TWIN-2002",
                           "delivery_lat": 25.08, "delivery_lng": 55.14}]}
    assert client.post("/orders/sync", headers=HEADERS, json=payload).status_code == 200
    pts = client.get("/insights", headers={"X-API-Key": "dev-dashboard-key-change-me"}).json()["map_points"]
    assert any(p["delivery_lat"] == 25.08 for p in pts)
