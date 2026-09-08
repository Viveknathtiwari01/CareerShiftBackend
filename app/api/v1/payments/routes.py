from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.payment import (
    CheckoutSessionResponse,
    ConfirmSessionRequest,
    PaymentStatusResponse,
)
from app.services.stripe_payment import StripePaymentService

router = APIRouter()


@router.post(
    "/create-checkout-session",
    response_model=APIResponse[CheckoutSessionResponse],
)
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StripePaymentService(db)
    data = await service.create_checkout_session(current_user)
    return APIResponse(
        success=True,
        message="Checkout session created",
        data=CheckoutSessionResponse(**data),
    )


@router.get("/status", response_model=APIResponse[PaymentStatusResponse])
async def payment_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StripePaymentService(db)
    data = await service.get_status(current_user)
    return APIResponse(
        success=True,
        message="Payment status retrieved",
        data=PaymentStatusResponse(**data),
    )


@router.post("/confirm-session", response_model=APIResponse[PaymentStatusResponse])
async def confirm_session(
    body: ConfirmSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StripePaymentService(db)
    data = await service.confirm_checkout_session(current_user, body.session_id)
    return APIResponse(
        success=True,
        message="Payment confirmed" if data.get("has_paid") else "Payment not completed yet",
        data=PaymentStatusResponse(**data),
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    service = StripePaymentService(db)
    try:
        result = await service.handle_webhook_event(payload, sig_header)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result
