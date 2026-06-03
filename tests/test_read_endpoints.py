import pytest

from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders

APIKEY = {"X-API-Key": "dev-dashboard-key-change-me"}


@pytest.fixture()
def seeded(client, db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()


def test_orders_requires_api_key(client, seeded):
    assert client.get("/orders").status_code == 401


def test_orders_list(client, seeded):
    r = client.get("/orders", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    assert body[0]["customer_name"]
    assert "otp_code" not in body[0]


def test_order_detail_has_coords_no_otp(client, seeded):
    oid = client.get("/orders", headers=APIKEY).json()[0]["order_id"]
    r = client.get(f"/orders/{oid}", headers=APIKEY)
    assert r.status_code == 200
    body = r.json()
    assert "delivery_lat" in body and "merchant_lat" in body
    assert body["customer"]["full_name"]
    assert "otp_code" not in body


def test_order_detail_404(client, seeded):
    import uuid
    assert client.get(f"/orders/{uuid.uuid4()}", headers=APIKEY).status_code == 404


def test_customers_list_and_detail(client, seeded):
    lst = client.get("/customers", headers=APIKEY)
    assert lst.status_code == 200
    assert lst.json()[0]["order_count"] >= 1
    cid = lst.json()[0]["customer_id"]
    det = client.get(f"/customers/{cid}", headers=APIKEY)
    assert det.status_code == 200
    assert "orders" in det.json()


def test_customer_detail_404(client, seeded):
    import uuid
    assert client.get(f"/customers/{uuid.uuid4()}", headers=APIKEY).status_code == 404
