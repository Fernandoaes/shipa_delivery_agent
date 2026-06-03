import uuid

from sqlalchemy.orm import Session

from app.models import Customer
from app.schemas.dashboard import CustomerDetail, CustomerListItem
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
    return CustomerDetail(
        customer_id=c.customer_id, full_name=c.full_name, primary_phone=c.primary_phone,
        language_pref=c.language_pref,
        orders=[_order_list_item(o) for o in sorted(c.orders, key=lambda o: o.twin_order_ref)],
    )
