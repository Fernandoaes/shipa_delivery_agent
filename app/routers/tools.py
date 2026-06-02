from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.verify import OrderPublic, VerifyRequest, VerifyResponse
from app.services.calls import get_or_create_call
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
