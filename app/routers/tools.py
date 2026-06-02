import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.orders import OrderStatusResponse
from app.schemas.verify import OrderPublic, VerifyRequest, VerifyResponse
from app.services.calls import get_call, get_or_create_call
from app.services.guard import VerificationRequired, require_verified_call
from app.services.orders import get_order
from app.services.verification import VerifyInput, verify_caller

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    call = get_or_create_call(
        db, happyrobot_call_id=payload.happyrobot_call_id,
        caller_number=payload.caller_number, language=payload.language,
    )
    res = verify_caller(db, call, VerifyInput(
        name=payload.name, order_ref=payload.order_ref, registered_phone=payload.registered_phone,
        delivery_area=payload.delivery_area, item=payload.item,
    ))
    db.commit()
    order_public = OrderPublic.model_validate(res.order, from_attributes=True) if res.order else None
    return VerifyResponse(
        call_id=call.call_id, result=res.result, attempt_no=res.attempt_no,
        escalated=res.escalated, order=order_public,
    )


def load_verified_call(
    x_call_id: uuid.UUID = Header(...),
    db: Session = Depends(get_db),
):
    call = get_call(db, x_call_id)
    if call is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="call not found")
    try:
        require_verified_call(call)
    except VerificationRequired:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="caller not verified")
    return call


@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
def order_status(order_id: uuid.UUID, call=Depends(load_verified_call), db: Session = Depends(get_db)) -> OrderStatusResponse:
    order = get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="order not found")
    return OrderStatusResponse(
        order_id=order.order_id, status=order.status,
        delivery_window=order.delivery_window, assigned_driver=order.assigned_driver,
    )
