import uuid

from sqlalchemy.orm import Session

from app.models import Order


def get_order(db: Session, order_id: uuid.UUID) -> Order | None:
    return db.get(Order, order_id)
