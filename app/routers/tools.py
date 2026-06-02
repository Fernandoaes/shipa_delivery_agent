import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.calls import DispositionRequest, DispositionResponse
from app.schemas.actions import (
    AddressFlagRequest,
    AddressFlagResponse,
    EscalateRequest,
    EscalateResponse,
    FallbackMessageRequest,
    FallbackMessageResponse,
    InvestigationRequest,
    InvestigationResponse,
    MerchantReferralRequest,
    MerchantReferralResponse,
    RescheduleRequest,
    RescheduleResponse,
)
from app.schemas.orders import OrderStatusResponse
from app.schemas.verify import OrderPublic, VerifyRequest, VerifyResponse
from app.services import actions
from app.services.calls import get_call, get_or_create_call, set_disposition
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


def _require_order(db: Session, order_id: uuid.UUID):
    order = get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="order not found")
    return order


@router.post("/orders/{order_id}/reschedule", response_model=RescheduleResponse)
def reschedule(order_id: uuid.UUID, payload: RescheduleRequest,
               call=Depends(load_verified_call), db: Session = Depends(get_db)) -> RescheduleResponse:
    _require_order(db, order_id)
    row = actions.create_reschedule(db, call.call_id, order_id, payload.requested_date,
                                    payload.requested_window, payload.reason)
    db.commit()
    return RescheduleResponse(reschedule_id=row.reschedule_id, status=row.status, requested_date=row.requested_date)


@router.post("/orders/{order_id}/investigation", response_model=InvestigationResponse)
def investigation(order_id: uuid.UUID, payload: InvestigationRequest,
                  call=Depends(load_verified_call), db: Session = Depends(get_db)) -> InvestigationResponse:
    _require_order(db, order_id)
    row = actions.create_investigation(db, call.call_id, order_id, payload.type)
    db.commit()
    return InvestigationResponse(investigation_id=row.investigation_id, status=row.status, callback_due_at=row.callback_due_at)


@router.post("/orders/{order_id}/merchant-referral", response_model=MerchantReferralResponse)
def merchant_referral(order_id: uuid.UUID, payload: MerchantReferralRequest,
                      call=Depends(load_verified_call), db: Session = Depends(get_db)) -> MerchantReferralResponse:
    _require_order(db, order_id)
    row = actions.create_merchant_referral(db, call.call_id, order_id, payload.reason)
    db.commit()
    return MerchantReferralResponse(referral_id=row.referral_id, status=row.status)


@router.post("/orders/{order_id}/address-flag", response_model=AddressFlagResponse)
def address_flag(order_id: uuid.UUID, payload: AddressFlagRequest,
                 call=Depends(load_verified_call), db: Session = Depends(get_db)) -> AddressFlagResponse:
    order = _require_order(db, order_id)
    row = actions.create_address_flag(db, call.call_id, order, payload.correction_text)
    db.commit()
    return AddressFlagResponse(flag_id=row.flag_id, status=row.status)


@router.post("/orders/{order_id}/escalate", response_model=EscalateResponse)
def escalate(order_id: uuid.UUID, payload: EscalateRequest,
             call=Depends(load_verified_call), db: Session = Depends(get_db)) -> EscalateResponse:
    _require_order(db, order_id)
    row = actions.create_escalation(db, call.call_id, order_id, payload.category, payload.reason)
    db.commit()
    return EscalateResponse(escalation_id=row.escalation_id, status=row.status)


@router.post("/orders/{order_id}/fallback-message", response_model=FallbackMessageResponse)
def fallback_message(order_id: uuid.UUID, payload: FallbackMessageRequest,
                     call=Depends(load_verified_call), db: Session = Depends(get_db)) -> FallbackMessageResponse:
    _require_order(db, order_id)
    row = actions.create_fallback_message(db, call.call_id, order_id, payload.channel, payload.content_type)
    db.commit()
    return FallbackMessageResponse(message_id=row.message_id, status=row.status)


@router.post("/calls/{call_id}/disposition", response_model=DispositionResponse)
def disposition(call_id: uuid.UUID, payload: DispositionRequest, db: Session = Depends(get_db)) -> DispositionResponse:
    call = get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="call not found")
    set_disposition(db, call, disposition=payload.disposition, intent=payload.intent,
                    csat_score=payload.csat_score, transcript=payload.transcript,
                    notes=payload.notes, recording_url=payload.recording_url)
    db.commit()
    return DispositionResponse(
        call_id=call.call_id, disposition=call.disposition, intent=call.intent,
        csat_score=call.csat_score, transcript=call.transcript, ended_at=call.ended_at,
    )
