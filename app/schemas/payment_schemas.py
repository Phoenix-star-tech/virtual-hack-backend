from pydantic import BaseModel, Field


class QRConfigResponse(BaseModel):
    qr_image_url: str | None = None
    upi_id: str | None = None
    amount: int = 9


class QRConfigUpdate(BaseModel):
    upi_id: str | None = None
    amount: int | None = None
