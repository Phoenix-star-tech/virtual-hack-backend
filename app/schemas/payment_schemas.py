from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    full_name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    phone: str = Field(..., description="User phone number")
    college: str = Field(..., description="User college or organization")
    password: str = Field(..., min_length=6, description="User password")


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str = "INR"
    key_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    access_token: str | None = None
    message: str = ""
