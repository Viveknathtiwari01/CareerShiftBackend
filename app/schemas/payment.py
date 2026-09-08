from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class PaymentStatusResponse(BaseModel):
    has_paid: bool
    paid_at: Optional[datetime] = None


class ConfirmSessionRequest(BaseModel):
    session_id: str
