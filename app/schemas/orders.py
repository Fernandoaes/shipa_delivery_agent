import uuid

from pydantic import BaseModel


class OrderStatusResponse(BaseModel):
    order_id: uuid.UUID
    status: str
    delivery_window: str | None
    assigned_driver: str | None
