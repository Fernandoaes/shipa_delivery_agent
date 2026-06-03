import datetime as dt

from app.models import Call, Escalation, Order, Reschedule
from app.services.insights import compute_insights
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    now = dt.datetime.now()
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                intent="reschedule", disposition="rescheduled", csat_score=5,
                order_id=order.order_id, customer_id=order.customer_id, started_at=now))
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="failed",
                intent="not_received", disposition=None, csat_score=None,
                order_id=order.order_id, customer_id=order.customer_id,
                started_at=now - dt.timedelta(days=3)))
    db.flush()
    return order


def test_calls_per_day_is_zero_filled_14_days(db):
    _seed(db)
    out = compute_insights(db)
    assert len(out["calls_per_day"]) == 14
    assert sum(d["count"] for d in out["calls_per_day"]) == 2
    dates = [d["date"] for d in out["calls_per_day"]]
    assert dates == sorted(dates)


def test_intent_and_disposition_mix(db):
    _seed(db)
    out = compute_insights(db)
    intents = {d["intent"]: d["count"] for d in out["intent_mix"]}
    assert intents["reschedule"] == 1 and intents["not_received"] == 1
    dispositions = {d["disposition"]: d["count"] for d in out["disposition_mix"]}
    assert dispositions["unknown"] == 1  # the None disposition is labeled "unknown"


def test_needs_attention_counts(db):
    order = _seed(db)
    call = db.query(Call).order_by(Call.started_at.desc()).first()
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=call.call_id, order_id=order.order_id,
                      requested_date=dt.date.today(), status="requested",
                      synced_to_twin_at=None, created_at=dt.datetime.now()))
    order.status = "failed"
    db.flush()
    out = compute_insights(db)
    assert out["needs_attention"]["open_escalations"] == 1
    assert out["needs_attention"]["pending_reschedules"] == 1
    assert out["needs_attention"]["failed_orders"] == 2  # TWIN-1001 set to failed + TWIN-1002 already failed in mock


def test_map_points_only_active_with_coords(db):
    _seed(db)
    order_with_coords = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    order_no_coords = db.query(Order).filter_by(twin_order_ref="TWIN-1003").one()

    order_with_coords.status = "out_for_delivery"
    order_with_coords.delivery_lat, order_with_coords.delivery_lng = 25.1, 55.2

    order_no_coords.status = "out_for_delivery"
    order_no_coords.delivery_lat, order_no_coords.delivery_lng = None, None

    db.flush()
    out = compute_insights(db)

    refs = {p["twin_order_ref"] for p in out["map_points"]}
    assert order_with_coords.twin_order_ref in refs     # coords present -> included
    assert order_no_coords.twin_order_ref not in refs   # coords absent -> excluded
    assert all(p["status"] in ("out_for_delivery", "pending", "failed", "rescheduled")
               for p in out["map_points"])
