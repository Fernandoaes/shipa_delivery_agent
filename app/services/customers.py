import uuid

from sqlalchemy.orm import Session

from app.models import Call, Customer
from app.schemas.dashboard import CustomerDetail, CustomerListItem
from app.services.calls import _call_summary
from app.services.orders import _order_list_item


def list_customers(db: Session) -> list[CustomerListItem]:
    customers = db.query(Customer).order_by(Customer.full_name).all()
    return [
        CustomerListItem(
            customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
            language_pref=c.language_pref, order_count=len(c.orders),
        )
        for c in customers
    ]


def get_customer_detail(db: Session, customer_id: uuid.UUID) -> CustomerDetail | None:
    c = db.get(Customer, customer_id)
    if c is None:
        return None
    ref_by_order = {o.order_id: o.twin_order_ref for o in c.orders}
    calls = (
        db.query(Call)
        .filter(Call.customer_id == customer_id)
        .order_by(Call.started_at.desc())
        .all()
    )
    call_summaries = [_call_summary(x, c.full_name, ref_by_order.get(x.order_id)) for x in calls]
    csats = [float(x.csat_score) for x in calls if x.csat_score is not None]
    avg_csat = round(sum(csats) / len(csats), 2) if csats else None
    last_contact_at = max((x.started_at for x in calls), default=None)
    has_failed_order = any(o.status in ("failed", "returned") for o in c.orders)
    needs_follow_up = (avg_csat is not None and avg_csat < 3.0) or has_failed_order
    return CustomerDetail(
        customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
        language_pref=c.language_pref,
        orders=[_order_list_item(o) for o in sorted(c.orders, key=lambda o: o.twin_order_ref)],
        calls=call_summaries, avg_csat=avg_csat, last_contact_at=last_contact_at,
        needs_follow_up=needs_follow_up,
    )
