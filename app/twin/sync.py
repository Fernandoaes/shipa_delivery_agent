import datetime as dt

from sqlalchemy.orm import Session

from app.models import Customer, Order
from app.twin.base import OrderRecord


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _get_or_create_customer(db: Session, rec: OrderRecord) -> Customer:
    customer = db.query(Customer).filter_by(primary_phone=rec.customer_phone).one_or_none()
    if customer is None:
        customer = Customer(
            full_name=rec.customer_name, primary_phone=rec.customer_phone,
            language_pref=rec.language_pref, twin_customer_ref=rec.twin_customer_ref,
            last_synced_at=_now(),
        )
        db.add(customer)
        db.flush()
    else:
        customer.full_name = rec.customer_name
        customer.language_pref = rec.language_pref
        customer.last_synced_at = _now()
    return customer


def upsert_orders(db: Session, records: list[OrderRecord]) -> list[Order]:
    """Single write path for order data — fed by a Twin pull or the ingest endpoint."""
    out: list[Order] = []
    for rec in records:
        customer = _get_or_create_customer(db, rec)
        order = db.query(Order).filter_by(twin_order_ref=rec.twin_order_ref).one_or_none()
        if order is None:
            order = Order(twin_order_ref=rec.twin_order_ref, customer_id=customer.customer_id,
                          merchant=rec.merchant, status=rec.status, delivery_address=rec.delivery_address,
                          last_synced_at=_now())
            db.add(order)
        order.customer_id = customer.customer_id
        order.merchant = rec.merchant
        order.status = rec.status
        order.delivery_address = rec.delivery_address
        order.delivery_area = rec.delivery_area
        order.delivery_window = rec.delivery_window
        order.otp_code = rec.otp_code
        order.assigned_driver = rec.assigned_driver
        order.expected_pieces = rec.expected_pieces
        order.last_synced_at = _now()
        db.flush()
        out.append(order)
    return out
