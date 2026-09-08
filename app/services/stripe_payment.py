from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import Payment
from app.models.user import User


def _stripe_get(obj, key: str, default=None):
    """Read a field from a StripeObject or plain dict (stripe-python v15+)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "to_dict"):
        return obj.to_dict().get(key, default)
    try:
        return obj[key]
    except Exception:
        return default


class StripePaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured. Set STRIPE_SECRET_KEY.",
            )
        if not settings.STRIPE_PRICE_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured. Set STRIPE_PRICE_ID.",
            )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def _frontend_url(self) -> str:
        return settings.effective_app_public_url.rstrip("/")

    async def create_checkout_session(self, user: User) -> dict:
        if user.has_paid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already completed",
            )

        params: dict = {
            "mode": "payment",
            "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            "success_url": (
                f"{self._frontend_url()}/payment/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            "cancel_url": f"{self._frontend_url()}/payment/cancel",
            "client_reference_id": str(user.id),
            "metadata": {"user_id": str(user.id)},
        }

        if user.stripe_customer_id:
            params["customer"] = user.stripe_customer_id
        else:
            params["customer_email"] = user.email
            params["customer_creation"] = "always"

        try:
            session = stripe.checkout.Session.create(**params)
        except stripe.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe checkout failed: {exc.user_message or str(exc)}",
            ) from exc

        payment = Payment(
            user_id=user.id,
            stripe_checkout_session_id=session.id,
            status="pending",
            amount_cents=session.amount_total,
            currency=session.currency,
        )
        self.db.add(payment)
        await self.db.commit()

        return {"url": session.url, "session_id": session.id}

    async def get_status(self, user: User) -> dict:
        return {"has_paid": bool(user.has_paid), "paid_at": user.paid_at}

    async def confirm_checkout_session(self, user: User, session_id: str) -> dict:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not verify Stripe session: {exc.user_message or str(exc)}",
            ) from exc

        metadata = _stripe_get(session, "metadata") or {}
        metadata_user_id = _stripe_get(metadata, "user_id")
        ref_id = _stripe_get(session, "client_reference_id")
        if str(user.id) not in {str(metadata_user_id) if metadata_user_id else None, str(ref_id) if ref_id else None}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Checkout session does not belong to this user",
            )

        payment_status = _stripe_get(session, "payment_status")
        session_status = _stripe_get(session, "status")
        if payment_status != "paid" and session_status != "complete":
            return {"has_paid": bool(user.has_paid), "paid_at": user.paid_at}

        await self._mark_paid_from_session(session)
        await self.db.refresh(user)
        return {"has_paid": bool(user.has_paid), "paid_at": user.paid_at}

    async def handle_webhook_event(self, payload: bytes, sig_header: str | None) -> dict:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe webhook secret is not configured",
            )
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe-Signature header",
            )

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
        except stripe.SignatureVerificationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await self._mark_paid_from_session(session)

        return {"received": True}

    async def _mark_paid_from_session(self, session) -> None:
        session_id = _stripe_get(session, "id")
        metadata = _stripe_get(session, "metadata") or {}
        client_ref = _stripe_get(session, "client_reference_id")
        customer_id = _stripe_get(session, "customer")
        payment_intent = _stripe_get(session, "payment_intent")
        amount_total = _stripe_get(session, "amount_total")
        currency = _stripe_get(session, "currency")

        user_id_raw = _stripe_get(metadata, "user_id") or client_ref
        if not user_id_raw or not session_id:
            return

        try:
            user_id = UUID(str(user_id_raw))
        except ValueError:
            return

        user = await self.db.get(User, user_id)
        if not user or user.is_deleted:
            return

        now = datetime.now(timezone.utc)
        if not user.has_paid:
            user.has_paid = True
            user.paid_at = now
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = str(customer_id)

        result = await self.db.execute(
            select(Payment).where(Payment.stripe_checkout_session_id == session_id)
        )
        payment = result.scalars().first()
        if payment:
            payment.status = "succeeded"
            payment.paid_at = now
            payment.stripe_payment_intent_id = (
                str(payment_intent) if payment_intent else payment.stripe_payment_intent_id
            )
            payment.amount_cents = amount_total if amount_total is not None else payment.amount_cents
            payment.currency = currency or payment.currency
        else:
            self.db.add(
                Payment(
                    user_id=user.id,
                    stripe_checkout_session_id=session_id,
                    stripe_payment_intent_id=str(payment_intent) if payment_intent else None,
                    amount_cents=amount_total,
                    currency=currency,
                    status="succeeded",
                    paid_at=now,
                )
            )

        await self.db.commit()
