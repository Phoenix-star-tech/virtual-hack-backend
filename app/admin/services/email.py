import os
import json
from typing import List
import httpx
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")

def send_email(to_emails: List[str], subject: str, html_body: str) -> dict:
    if not BREVO_API_KEY:
        return {"error": "Brevo API key not configured"}
    try:
        resp = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "sender": {"name": "Virtual Hackathon 2K26", "email": "noreply@vashikplatform.com"},
                "to": [{"email": e} for e in to_emails],
                "subject": subject,
                "htmlContent": html_body,
            },
            timeout=15,
        )
        return {"status": resp.status_code, "message_id": resp.json().get("messageId", "") if resp.status_code == 201 else resp.text}
    except Exception as e:
        return {"error": str(e)}
