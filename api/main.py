# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: May 3, 2026
#
# CALENDAR ARCHITECTURE — FIXED:
# get_available_dates() is called in main.py BEFORE the crew fires.
# The raw calendar dates are stored as a structured list and returned
# directly in the API response as available_dates.
# The frontend uses this list directly for the date picker — no parsing,
# no agent interpretation, no drift.
# The crew still receives the dates as context for prose generation
# but the date picker is always anchored to the raw calendar output.
#
# TELEGRAM ARCHITECTURE:
# Telegram fires once — on /api/miguel/confirm-date.
#
# PRICING ARCHITECTURE:
# Prices anchored to PRICING_TIERS by session type. Never scraped from prose.
#
# IMAGE ARCHITECTURE:
# reference_images accepts up to 3 base64 images.

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import os
import re
import uuid
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crews.tattoo_intake_crew import run_tattoo_intake_crew
from tools.google_calendar_tool import get_available_dates
from tools.telegram_notifier import (
    notify_miguel,
    send_telegram_message,
    send_client_confirmation,
    send_client_decline,
    send_client_custom_message
)
from db.database import get_db
from db.models import Artist, Client, Intake, Estimate, Approval

app = FastAPI(
    title="Inkbook API",
    description="AI-native tattoo booking platform — Miguel",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# SENTINEL VALUES
# ─────────────────────────────────────────

NEEDS_ALTERNATE_DATES = "NEEDS_ALTERNATE"

# ─────────────────────────────────────────
# FIELD MAPPINGS
# ─────────────────────────────────────────

BUDGET_MAP = {
    "Under $200": "under_200",
    "$200–$500": "200_500",
    "$500–$1,000": "500_1000",
    "$1,000+": "1000_plus",
    "under_200": "under_200",
    "200_500": "200_500",
    "500_1000": "500_1000",
    "1000_plus": "1000_plus",
}

TIMING_MAP = {
    "Within 2 weeks": "within_2_weeks",
    "Within 1 month": "within_1_month",
    "Within 2 months": "within_2_months",
    "Flexible": "flexible",
    "within_2_weeks": "within_2_weeks",
    "within_1_month": "within_1_month",
    "within_2_months": "within_2_months",
    "flexible": "flexible",
}

SIZE_MAP = {
    "Small": "small",
    "Medium": "medium",
    "Large": "large",
    "Full Sleeve": "full_sleeve",
    "small": "small",
    "medium": "medium",
    "large": "large",
    "full_sleeve": "full_sleeve",
    "full sleeve": "full_sleeve",
}

# ─────────────────────────────────────────
# MIGUEL'S PRICING TIERS — SOURCE OF TRUTH
# ─────────────────────────────────────────

PRICING_TIERS = {
    "small":       {"min": 100, "max": 300,   "deposit": 50},
    "half_day":    {"min": 400, "max": 600,   "deposit": 100},
    "full_day":    {"min": 800, "max": 1000,  "deposit": 100},
    "full_sleeve": {"min": 800, "max": 1000,  "deposit": 100},
}

# ─────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────

class GuidedDiscovery(BaseModel):
    meaning: Optional[str] = None
    imagery: Optional[str] = None
    style_notes: Optional[str] = None

class IntakeRequest(BaseModel):
    client_name: str
    contact: str
    size_selection: str
    description: str
    placement: str
    styles: Optional[List[str]] = []
    is_cover_up: bool = False
    cover_up_description: Optional[str] = None
    budget_range: str
    preferred_timing: str
    reference_images: Optional[List[str]] = []
    reference_image: Optional[str] = None
    idea_readiness: str
    guided_discovery: Optional[GuidedDiscovery] = None

class ApprovalRequest(BaseModel):
    intake_id: str
    decision: str
    selected_date: Optional[str] = None
    adjusted_price: Optional[str] = None
    adjusted_dates: Optional[str] = None
    adjusted_message: Optional[str] = None

class DateConfirmRequest(BaseModel):
    intake_id: str
    selected_date: str

# ─────────────────────────────────────────
# IN-MEMORY STORE
# ─────────────────────────────────────────

intake_store = {}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def parse_crew_output(result: str) -> tuple:
    if "---SESSION SUMMARY---" in result:
        parts = result.split("---SESSION SUMMARY---")
        client_message = parts[0].replace("---CLIENT MESSAGE---", "").strip()
        session_summary = parts[1].strip()
    else:
        client_message = result.strip()
        session_summary = "Session summary not generated."
    return client_message, session_summary


def resolve_reference_images(request: IntakeRequest) -> list:
    if request.reference_images:
        return [img for img in request.reference_images if img]
    if request.reference_image:
        return [request.reference_image]
    return []


def extract_pricing(
    pricing_agent_output: str,
    size_selection: str,
    placement: str = ""
) -> dict:
    text = pricing_agent_output.lower()
    placement_lower = (placement or "").lower()

    session_type = None

    if "full sleeve" in text:
        session_type = "full_sleeve"
    elif "full day" in text:
        session_type = "full_day"
    elif "half day" in text:
        session_type = "half_day"
    elif "small" in text:
        session_type = "small"

    if not session_type and "sleeve" in placement_lower:
        session_type = "full_sleeve"
        print(f">>> Sleeve placement detected ('{placement}') — upgraded to full_sleeve")
    elif session_type == "small" and "sleeve" in placement_lower:
        session_type = "full_sleeve"
        print(f">>> Sleeve placement override — placement is '{placement}'")

    if not session_type:
        size_to_tier = {
            "small": "small",
            "medium": "half_day",
            "large": "full_day",
            "full_sleeve": "full_sleeve",
        }
        session_type = size_to_tier.get(size_selection, "small")

    tier = PRICING_TIERS[session_type]
    print(f">>> Pricing: session_type={session_type}, "
          f"min={tier['min']}, max={tier['max']}, deposit={tier['deposit']}")

    return {
        "price_min": tier["min"],
        "price_max": tier["max"],
        "deposit": tier["deposit"],
        "session_type": session_type,
    }


def format_dates_for_frontend(raw_dates: list[str]) -> list[str]:
    """
    Converts calendar tool output ("Saturday May 10") to the
    frontend's expected format ("Saturday · May 10").
    Also normalizes any already-formatted strings.
    """
    formatted = []
    for d in raw_dates:
        if '·' in d:
            formatted.append(d.strip())
        else:
            # Insert · between day name and month
            # "Saturday May 10" → "Saturday · May 10"
            parts = d.strip().split(' ', 1)
            if len(parts) == 2:
                formatted.append(f"{parts[0]} · {parts[1]}")
            else:
                formatted.append(d.strip())
    return formatted


async def get_or_create_client(db: AsyncSession, name: str, contact: str) -> Client:
    result = await db.execute(select(Client).where(Client.contact == contact))
    client = result.scalar_one_or_none()
    if client:
        client.name = name
        return client
    client = Client(
        name=name,
        contact=contact,
        contact_type="phone" if contact.startswith("+") else "email"
    )
    db.add(client)
    await db.flush()
    return client


async def get_miguel(db: AsyncSession) -> Artist:
    result = await db.execute(select(Artist).where(Artist.name == "Miguel"))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=500, detail="Artist record not found.")
    return artist


async def store_intake(
    db: AsyncSession,
    short_id: str,
    artist_id: uuid.UUID,
    client_id: uuid.UUID,
    request: IntakeRequest,
    classification: str,
    raw_crew_output: str,
    budget_db: str,
    timing_db: str,
    size_db: str,
    primary_image_url: Optional[str] = None
) -> Intake:
    guided = request.guided_discovery
    intake = Intake(
        short_id=short_id,
        artist_id=artist_id,
        client_id=client_id,
        classification=classification,
        size_selection=size_db,
        description=request.description,
        placement=request.placement,
        styles=request.styles or [],
        is_cover_up=request.is_cover_up,
        cover_up_description=request.cover_up_description,
        budget_range=budget_db,
        preferred_timing=timing_db,
        idea_readiness=request.idea_readiness,
        reference_image_url=primary_image_url,
        guided_meaning=guided.meaning if guided else None,
        guided_imagery=guided.imagery if guided else None,
        guided_style_notes=guided.style_notes if guided else None,
        raw_crew_output=raw_crew_output,
        status="pending"
    )
    db.add(intake)
    await db.flush()
    return intake


async def store_approval(
    db: AsyncSession,
    intake_id: uuid.UUID,
    artist_id: uuid.UUID,
    decision: str,
    client_message_sent: str,
    adjusted_message: Optional[str] = None
) -> Approval:
    from datetime import datetime, timezone
    approval = Approval(
        intake_id=intake_id,
        artist_id=artist_id,
        decision=decision,
        client_message_sent=client_message_sent,
        message_sent_at=datetime.now(timezone.utc),
        adjusted_message=adjusted_message,
        notification_channel="sms"
    )
    db.add(approval)
    await db.flush()
    return approval


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status": "running",
        "product": "Inkbook",
        "artist": "Miguel",
        "version": "0.1.0"
    }


@app.post("/api/miguel/intake")
async def intake(
    request: IntakeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Runs the crew and returns the estimate to the frontend.

    CALENDAR FIX: get_available_dates() is called HERE in main.py
    before the crew fires. The raw dates are returned directly to
    the frontend as available_dates. The crew also receives them
    as context strings for prose generation, but the date picker
    always uses the structured list — never agent-parsed prose.
    """
    try:
        budget_db = BUDGET_MAP.get(request.budget_range, "under_200")
        timing_db = TIMING_MAP.get(request.preferred_timing, "flexible")
        size_db = SIZE_MAP.get(request.size_selection, "medium")

        print(f">>> Mapped budget: {request.budget_range} → {budget_db}")
        print(f">>> Mapped timing: {request.preferred_timing} → {timing_db}")
        print(f">>> Mapped size: {request.size_selection} → {size_db}")
        print(f">>> Placement: {request.placement}")

        # ── STEP 1: Fetch real calendar dates BEFORE crew fires ──
        # This is the source of truth for the date picker.
        # Raw format: ["Saturday May 10", "Thursday May 22", ...]
        # These strings come directly from Miguel's Google Calendar.
        # No agent touches them before they reach the frontend.
        print(">>> Fetching calendar dates...")
        raw_calendar_dates = get_available_dates(size_db)
        print(f">>> Raw calendar dates: {raw_calendar_dates}")

        # Format for frontend: "Saturday May 10" → "Saturday · May 10"
        available_dates = format_dates_for_frontend(raw_calendar_dates)
        print(f">>> Formatted dates for frontend: {available_dates}")

        # ── STEP 2: Resolve images ───────────────────────────────
        all_images = resolve_reference_images(request)
        image_count = len(all_images)
        primary_image = all_images[0] if all_images else None
        print(f">>> Reference images: {image_count} uploaded")

        # ── STEP 3: Build form data for crew ─────────────────────
        # Pass the raw calendar dates as a comma-separated string
        # so the scheduling agent can use them for prose generation.
        # The agent's prose may rephrase them — that's fine because
        # the date picker uses available_dates, not the prose.
        form_data = {
            "client_name": request.client_name,
            "contact": request.contact,
            "size_selection": size_db,
            "description": request.description,
            "placement": request.placement,
            "styles": request.styles,
            "is_cover_up": request.is_cover_up,
            "cover_up_description": request.cover_up_description,
            "budget_range": budget_db,
            "preferred_timing": timing_db,
            "reference_image": "reference_image_uploaded" if image_count > 0 else None,
            "reference_image_count": image_count,
            "idea_readiness": request.idea_readiness,
            "guided_discovery": request.guided_discovery.dict()
                if request.guided_discovery else None,
            # Pass calendar dates to crew for prose context
            "calendar_dates": raw_calendar_dates,
        }

        short_id = str(uuid.uuid4())[:8].upper()

        # ── STEP 4: Fire crew ────────────────────────────────────
        print(">>> Firing crew...")
        result, classification = run_tattoo_intake_crew(form_data)
        print(">>> Crew complete")
        print(f">>> Classification: {classification}")

        client_message, session_summary = parse_crew_output(result)
        pricing = extract_pricing(result, size_db, request.placement)

        print(f">>> Pricing: ${pricing['price_min']}-${pricing['price_max']}, "
              f"deposit ${pricing['deposit']}, type {pricing['session_type']}")

        # ── STEP 5: Database ─────────────────────────────────────
        artist = await get_miguel(db)
        client = await get_or_create_client(
            db=db,
            name=request.client_name,
            contact=request.contact
        )

        intake_record = await store_intake(
            db=db,
            short_id=short_id,
            artist_id=artist.id,
            client_id=client.id,
            request=request,
            classification=classification,
            raw_crew_output=result,
            budget_db=budget_db,
            timing_db=timing_db,
            size_db=size_db,
            primary_image_url=primary_image
        )
        print(f">>> Stored intake: {short_id}")

        client.total_intakes = (client.total_intakes or 0) + 1
        await db.commit()

        # ── STEP 6: Memory store ─────────────────────────────────
        intake_store[short_id] = {
            "client_name": request.client_name,
            "client_contact": request.contact,
            "client_message": client_message,
            "session_summary": session_summary,
            "classification": classification,
            "available_dates": available_dates,
            "selected_date": None,
            "pricing": pricing,
            "preferred_timing": timing_db,
            "image_count": image_count,
            "intake_id": short_id,
            "intake_db_id": str(intake_record.id),
            "artist_db_id": str(artist.id),
            "status": "pending"
        }

        print(">>> Intake stored. Waiting for client to select date.")

        # ── STEP 7: Return — available_dates is the structured ───
        # calendar output, NOT parsed from agent prose.
        return {
            "status": "success",
            "message": "Estimate ready",
            "intake_id": short_id,
            "client_message": client_message,
            "available_dates": available_dates,   # ← direct from calendar
            "preferred_timing": timing_db,
            "price_min": pricing["price_min"],
            "price_max": pricing["price_max"],
            "deposit": pricing["deposit"],
            "session_type": pricing["session_type"]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Intake failed: {str(e)}")


@app.post("/api/miguel/confirm-date")
async def confirm_date(
    request: DateConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        short_id = request.intake_id
        selected_date = request.selected_date

        if short_id not in intake_store:
            raise HTTPException(status_code=404, detail="Intake not found.")

        intake = intake_store[short_id]
        intake_store[short_id]["selected_date"] = selected_date

        if selected_date == NEEDS_ALTERNATE_DATES:
            print(f">>> Client signaled NONE OF THE DATES WORK: {short_id}")
        else:
            print(f">>> Date confirmed: {short_id} → {selected_date}")

        print(">>> Sending Telegram notification...")
        try:
            notify_miguel(
                classification=intake["classification"],
                client_name=intake["client_name"],
                client_contact=intake["client_contact"],
                client_message=intake["client_message"],
                session_summary=intake["session_summary"],
                intake_id=short_id,
                selected_date=selected_date
            )
            print(">>> Telegram sent")
        except Exception as telegram_error:
            print(f">>> Telegram failed (non-fatal): {str(telegram_error)}")

        return {
            "status": "success",
            "message": "Request sent to Miguel",
            "intake_id": short_id,
            "selected_date": selected_date,
            "needs_alternate": selected_date == NEEDS_ALTERNATE_DATES
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Date confirmation failed: {str(e)}")


@app.post("/api/miguel/approve")
async def approve(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        if request.decision == "approved":
            return {"status": "success", "decision": "approved", "intake_id": request.intake_id}
        elif request.decision == "adjusted":
            return {"status": "success", "decision": "adjusted", "intake_id": request.intake_id}
        elif request.decision == "declined":
            return {"status": "success", "decision": "declined", "intake_id": request.intake_id}
        else:
            raise HTTPException(status_code=400, detail="Invalid decision.")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()
        message = body.get("message", {})
        text = message.get("text", "").strip()
        text_upper = text.upper()
        chat_id = str(message.get("chat", {}).get("id", ""))

        if chat_id != os.getenv("MIGUEL_CHAT_ID"):
            return {"status": "ignored"}

        short_id = None
        for word in text.split():
            candidate = word.upper().strip()
            if candidate in intake_store:
                short_id = candidate
                break

        if not short_id or short_id not in intake_store:
            send_telegram_message(
                "No matching intake found.\n\n"
                "Reply with your decision and the intake ID:\n"
                "✅ APPROVE C7D3828A\n"
                "✏️ ADJUST C7D3828A\n"
                "❌ DECLINE C7D3828A"
            )
            return {"status": "no_matching_intake"}

        intake = intake_store[short_id]

        if "APPROVE" in text_upper:
            send_client_confirmation(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"],
                client_message=intake["client_message"],
                intake_id=short_id
            )
            await store_approval(
                db=db,
                intake_id=uuid.UUID(intake["intake_db_id"]),
                artist_id=uuid.UUID(intake["artist_db_id"]),
                decision="approved",
                client_message_sent=intake["client_message"]
            )
            result = await db.execute(select(Intake).where(Intake.short_id == short_id))
            intake_record = result.scalar_one_or_none()
            if intake_record:
                intake_record.status = "approved"
            await db.commit()
            intake_store[short_id]["status"] = "approved"
            send_telegram_message(f"✅ Confirmed. Message sent to {intake['client_name']}.")

        elif "DECLINE" in text_upper:
            send_client_decline(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"]
            )
            await store_approval(
                db=db,
                intake_id=uuid.UUID(intake["intake_db_id"]),
                artist_id=uuid.UUID(intake["artist_db_id"]),
                decision="declined",
                client_message_sent="Decline message sent."
            )
            result = await db.execute(select(Intake).where(Intake.short_id == short_id))
            intake_record = result.scalar_one_or_none()
            if intake_record:
                intake_record.status = "declined"
            await db.commit()
            intake_store[short_id]["status"] = "declined"
            send_telegram_message(f"❌ Decline sent to {intake['client_name']}.")

        elif "ADJUST" in text_upper:
            send_telegram_message(
                f"✏️ What would you like to change for {intake['client_name']}?\n\n"
                f"Type your updated message and I will send it.\n"
                f"Include the intake ID: {short_id}"
            )
            intake_store[short_id]["status"] = "adjusting"

        else:
            if intake_store[short_id].get("status") == "adjusting":
                custom_msg = message.get("text", "")
                send_client_custom_message(
                    client_contact=intake["client_contact"],
                    client_name=intake["client_name"],
                    custom_message=custom_msg
                )
                await store_approval(
                    db=db,
                    intake_id=uuid.UUID(intake["intake_db_id"]),
                    artist_id=uuid.UUID(intake["artist_db_id"]),
                    decision="adjusted",
                    client_message_sent=custom_msg,
                    adjusted_message=custom_msg
                )
                result = await db.execute(select(Intake).where(Intake.short_id == short_id))
                intake_record = result.scalar_one_or_none()
                if intake_record:
                    intake_record.status = "adjusted"
                await db.commit()
                intake_store[short_id]["status"] = "approved"
                send_telegram_message(
                    f"✅ Your updated message was sent to {intake['client_name']}."
                )

        return {"status": "ok"}

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}