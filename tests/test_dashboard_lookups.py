import datetime as dt

from app.models import Call, Escalation, Investigation, Order
from app.routers.dashboard import list_escalations, list_investigations
from app.schemas.dashboard import EscalationSummary, InvestigationSummary
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_escalation_summary_exposes_reason():
    assert "reason" in EscalationSummary.model_fields


def test_investigation_summary_exposes_twin_order_ref():
    assert "twin_order_ref" in InvestigationSummary.model_fields


def test_list_investigations_resolves_twin_ref(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    # call_id is NOT NULL on Investigation, so create a real Call first.
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add(call)
    db.flush()
    db.add(Investigation(call_id=call.call_id, order_id=order.order_id, type="missing_item",
                         status="open", opened_at=dt.datetime.now()))
    db.flush()
    rows = list_investigations(db)
    assert rows[0].twin_order_ref == "TWIN-1001"


def test_escalation_summary_exposes_order_link():
    assert "order_id" in EscalationSummary.model_fields
    assert "twin_order_ref" in EscalationSummary.model_fields


def test_list_escalations_resolves_twin_ref(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add(call)
    db.flush()
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="refund",
                      reason="late", status="open", created_at=dt.datetime.now()))
    db.flush()
    rows = list_escalations(db)
    assert rows[0].order_id == order.order_id
    assert rows[0].twin_order_ref == "TWIN-1001"
