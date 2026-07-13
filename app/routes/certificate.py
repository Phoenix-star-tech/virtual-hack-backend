import io
import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.supabase_service import supabase, supabase_admin

logger = logging.getLogger("certificate")
router = APIRouter()


def _generate_certificate_pdf(full_name: str) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph

    buf = io.BytesIO()
    width, height = landscape(A4)

    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Colors
    gold = HexColor("#C9A84C")
    dark = HexColor("#1a1a2e")
    accent = HexColor("#e94560")

    # Background
    c.setFillColor(HexColor("#FAF8F5"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Outer decorative border
    c.setStrokeColor(gold)
    c.setLineWidth(3)
    c.rect(20, 20, width - 40, height - 40, fill=0, stroke=1)

    # Inner border
    c.setStrokeColor(gold)
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60, fill=0, stroke=1)

    # Corner decorations
    corner_size = 30
    for cx, cy in [(30, 30), (width - 30, 30), (30, height - 30), (width - 30, height - 30)]:
        c.setStrokeColor(gold)
        c.setLineWidth(2)
        c.line(cx, cy, cx + corner_size, cy)
        c.line(cx, cy, cx, cy + corner_size)

    # Top accent line
    c.setStrokeColor(accent)
    c.setLineWidth(4)
    c.line(100, height - 80, width - 100, height - 80)

    # Header
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2, height - 130, "Certificate of Participation")

    # Sub-header line
    c.setStrokeColor(gold)
    c.setLineWidth(1)
    c.line(width / 2 - 120, height - 150, width / 2 + 120, height - 150)

    # Awarded text
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 190, "This certificate is proudly awarded to")

    # Recipient name
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(width / 2, height - 250, full_name)

    # Underline
    name_width = c.stringWidth(full_name, "Helvetica-Bold", 42)
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.line(width / 2 - name_width / 2 - 10, height - 260, width / 2 + name_width / 2 + 10, height - 260)

    # Description
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 305, "for their active participation and contribution in")

    # Event name
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 340, "Virtual Hackathon 2K26")

    # Date
    c.setFillColor(HexColor("#777777"))
    c.setFont("Helvetica", 11)
    today = datetime.now().strftime("%B %d, %Y")
    c.drawCentredString(width / 2, height - 390, f"Date: {today}")

    # Bottom accent line
    c.setStrokeColor(accent)
    c.setLineWidth(4)
    c.line(100, 100, width - 100, 100)

    # Footer
    c.setFillColor(HexColor("#999999"))
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2, 60, "VASHIK Platform  •  www.virtualhack2k26.tech")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


@router.get("/download")
async def download_certificate(
    user_id: str = Query(..., description="User ID"),
    full_name: str | None = Query(None, description="Name to appear on certificate (for team members)"),
):
    if not supabase or not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    # Check platform setting
    try:
        plat = supabase_admin.table("platform_settings").select("certificate_download_enabled").limit(1).execute()
        enabled = plat.data[0].get("certificate_download_enabled", False) if plat.data else False
    except Exception as e:
        logger.error("Failed to check platform settings: %s", e)
        enabled = False

    if not enabled:
        raise HTTPException(status_code=403, detail="Certificate download is not enabled yet. Still not qualified.")

    # If full_name explicitly provided, use it (team member cert)
    if full_name:
        name_for_cert = full_name
    else:
        # Try registrations table first
        name_for_cert = "Participant"
        try:
            reg_resp = supabase_admin.table("registrations").select("full_name").eq("id", user_id).single().execute()
            if reg_resp.data:
                name_for_cert = reg_resp.data.get("full_name", "Participant")
        except Exception:
            pass

        if name_for_cert == "Participant":
            try:
                profile_resp = supabase.from_("profiles").select("full_name").eq("id", user_id).single().execute()
                if profile_resp.data:
                    name_for_cert = profile_resp.data.get("full_name", "Participant")
            except Exception as e:
                logger.error("Failed to fetch user profile: %s", e)

    try:
        pdf_buf = _generate_certificate_pdf(name_for_cert)
    except Exception as e:
        logger.error("Certificate generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate certificate")

    safe_name = name_for_cert.replace(" ", "_") if name_for_cert else "Participant"
    filename = f"certificate_{safe_name}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )
