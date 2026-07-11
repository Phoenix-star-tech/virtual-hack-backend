import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
import razorpay

from app.schemas.payment_schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services.supabase_service import supabase, supabase_admin

logger = logging.getLogger("payment")
router = APIRouter()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None


def _get_module_1_fee() -> int:
    if not supabase_admin:
        return 900
    try:
        mod = (
            supabase_admin.table("modules")
            .select("registration_fee")
            .eq("status", "open")
            .order("order_index")
            .limit(1)
            .execute()
        )
        if mod.data:
            fee = mod.data[0].get("registration_fee", 9)
            return int(round(float(fee) * 100))
    except Exception as e:
        logger.warning("Failed to fetch module fee, using default: %s", e)
    return 900


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(request: CreateOrderRequest):
    if not razorpay_client:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env",
        )
    if not supabase_admin:
        raise HTTPException(
            status_code=503,
            detail="Supabase admin client is not configured.",
        )

    amount_paise = _get_module_1_fee()
    receipt_id = f"reg_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    try:
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "payment_capture": 1,
        })
    except razorpay.errors.BadRequestError as e:
        logger.error("Razorpay order creation rejected (BadRequest): %s", e)
        raise HTTPException(status_code=400, detail=f"Razorpay rejected order: {e}")
    except Exception as e:
        logger.error("Razorpay order creation failed: type=%s detail=%s", type(e).__name__, e)
        raise HTTPException(status_code=502, detail="Failed to create payment order")

    order_id = order.get("id")

    try:
        supabase_admin.table("pending_registrations").insert({
            "order_id": order_id,
            "form_data": {
                "full_name": request.full_name,
                "email": request.email,
                "phone": request.phone,
                "college": request.college,
                "password": request.password,
            },
            "amount": amount_paise,
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error("Failed to stash pending registration: %s", e)
        try:
            razorpay_client.order.delete(order_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to prepare registration")

    return CreateOrderResponse(
        order_id=order_id,
        amount=amount_paise,
        currency="INR",
        key_id=RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(request: VerifyPaymentRequest):
    if not razorpay_client:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured.",
        )
    if not supabase_admin:
        raise HTTPException(
            status_code=503,
            detail="Supabase admin client is not configured.",
        )

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": request.razorpay_order_id,
            "razorpay_payment_id": request.razorpay_payment_id,
            "razorpay_signature": request.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        logger.warning(
            "Signature verification FAILED for order=%s payment=%s",
            request.razorpay_order_id,
            request.razorpay_payment_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed. Invalid signature. Your registration was not saved.",
        )

    pending = None
    try:
        result = (
            supabase_admin.table("pending_registrations")
            .select("*")
            .eq("order_id", request.razorpay_order_id)
            .limit(1)
            .execute()
        )
        pending = result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to fetch pending registration: %s", e)

    if not pending:
        raise HTTPException(
            status_code=400,
            detail="Pending registration not found or expired. Please register again.",
        )

    form_data = pending["form_data"]
    email = form_data["email"]
    password = form_data["password"]
    full_name = form_data["full_name"]
    phone = form_data["phone"]
    college = form_data["college"]

    # --- Handle duplicate user gracefully ---
    user_id = None
    try:
        user_resp = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "phone": phone,
                "college": college,
            },
        })
        user_id = str(user_resp.user.id)
    except Exception as e:
        err_msg = str(e).lower()
        if "already" in err_msg or "duplicate" in err_msg or "exists" in err_msg:
            # User already registered — look up existing user by email
            logger.info("User %s already exists, looking up existing account.", email)
            try:
                existing = supabase_admin.auth.admin.list_users()
                for u in existing:
                    if u.email == email:
                        user_id = str(u.id)
                        break
            except Exception as lookup_err:
                logger.error("Failed to look up existing user %s: %s", email, lookup_err)

        if not user_id:
            logger.critical(
                "PAYMENT CAPTURED but ACCOUNT CREATION FAILED for order %s, payment %s: %s",
                request.razorpay_order_id,
                request.razorpay_payment_id,
                e,
            )
            try:
                supabase_admin.table("pending_registrations").delete().eq(
                    "order_id", request.razorpay_order_id
                ).execute()
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail="Account creation failed after payment. Our team has been notified and will resolve this shortly.",
            )

    try:
        supabase_admin.table("profiles").upsert({
            "id": user_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "college": college,
        }).execute()
    except Exception as e:
        logger.warning("Profile upsert failed (non-critical): %s", e)

    try:
        supabase_admin.table("payments").insert({
            "razorpay_order_id": request.razorpay_order_id,
            "razorpay_payment_id": request.razorpay_payment_id,
            "razorpay_signature": request.razorpay_signature,
            "amount": pending["amount"],
            "currency": "INR",
            "status": "captured",
            "user_id": user_id,
            "email": email,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error("Failed to record payment (non-critical): %s", e)

    try:
        supabase_admin.table("pending_registrations").delete().eq(
            "order_id", request.razorpay_order_id
        ).execute()
    except Exception as e:
        logger.warning("Failed to delete pending registration (non-critical): %s", e)

    access_token = None
    try:
        auth_session = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        access_token = auth_session.session.access_token if auth_session.session else None
    except Exception as e:
        logger.warning("Auto-login after registration failed: %s", e)

    return VerifyPaymentResponse(
        success=True,
        user_id=user_id,
        email=email,
        full_name=full_name,
        access_token=access_token,
        message="Payment successful! Your account has been created.",
    )
