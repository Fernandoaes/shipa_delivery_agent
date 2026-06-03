from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.twin import TwinOrderRead
from app.services.orders import list_twin_orders

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.get("/twin/orders", response_model=list[TwinOrderRead])
def twin_orders(db: Session = Depends(get_db)):
    return list_twin_orders(db)
