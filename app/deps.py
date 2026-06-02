from collections.abc import Generator

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.security import secrets_match


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    if not secrets_match(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook secret")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not secrets_match(x_api_key, settings.dashboard_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
