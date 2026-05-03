# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: May 2, 2026
#
# TELEGRAM ARCHITECTURE:
# Telegram does NOT fire on intake submission.
# It fires once — on /api/miguel/confirm-date —
# after the client selects a date and taps Send to Miguel.
# One complete card. No partial notifications. No race conditions.

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
# FIELD MAPPINGS
# Frontend labels → DB constraint values
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


def parse_available_dates(text: str) -> list:
    """
    Extract all day + date strings from any text block.
    Matches: "Saturday May 10", "Thursday, May 15", "Saturday · May 24"
    Returns deduplicated list capped at 5.
    """
    DAY_NAMES = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
    MONTH_NAMES = (
        r'(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December)'
    )
    pattern = re.compile(
        rf'({DAY_NAMES})[,\s·]+({MONTH_NAMES}\s+\d{{1,2}})',
        re.IGNORECASE
    )
    dates = []
    seen = set()
    for match in pattern.finditer(text):
        day = match.group(1).capitalize()
        month_day = match.group(2).strip()
        parts = month_day.split()
        if len(parts) == 2:
            month_day = f"{parts[0].capitalize()} {parts[1]}"
        formatted = f"{day} · {month_day}"
        if formatted not in seen:
            seen.add(formatted)
            dates.append(formatted)
    return dates[:5]


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
    size_db: str
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
        reference_image_url=request.reference_image,
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
    Does NOT send Telegram. Telegram fires only after the client
    selects a date and hits confirm via /api/miguel/confirm-date.
    """
    try:
        budget_db = BUDGET_MAP.get(request.budget_range, "under_200")
        timing_db = TIMING_MAP.get(request.preferred_timing, "flexible")
        size_db = SIZE_MAP.get(request.size_selection, "medium")

        print(f">>> Mapped budget: {request.budget_range} → {budget_db}")
        print(f">>> Mapped timing: {request.preferred_timing} → {timing_db}")
        print(f">>> Mapped size: {request.size_selection} → {size_db}")

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
            "reference_image": request.reference_image,
            "idea_readiness": request.idea_readiness,
            "guided_discovery": request.guided_discovery.dict()
                if request.guided_discovery else None
        }

        short_id = str(uuid.uuid4())[:8].upper()

        print(">>> Firing crew...")
        result, classification = run_tattoo_intake_crew(form_data)
        print(">>> Crew complete")
        print(f">>> Classification: {classification}")

        client_message, session_summary = parse_crew_output(result)

        # Extract available dates from client_message prose
        available_dates = parse_available_dates(client_message)
        if not available_dates:
            available_dates = parse_available_dates(result)
        print(f">>> Available dates extracted: {available_dates}")

        # ── Database ──────────────────────────
        print(">>> Writing to database...")
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
            size_db=size_db
        )
        print(f">>> Stored intake: {short_id}")

        client.total_intakes = (client.total_intakes or 0) + 1
        await db.commit()

        # ── Memory store ──────────────────────
        # Store everything needed for Telegram card at confirm-date time.
        # No Telegram fired here — client hasn't chosen a date yet.
        intake_store[short_id] = {
            "client_name": request.client_name,
            "client_contact": request.contact,
            "client_message": client_message,
            "session_summary": session_summary,
            "classification": classification,
            "available_dates": available_dates,
            "selected_date": None,
            "intake_id": short_id,
            "intake_db_id": str(intake_record.id),
            "artist_db_id": str(artist.id),
            "status": "pending"
        }

        print(">>> Intake stored. Waiting for client to select date.")
        return {
            "status": "success",
            "message": "Estimate ready",
            "intake_id": short_id,
            "client_message": client_message,
            "available_dates": available_dates
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Intake failed: {str(e)}"
        )


@app.post("/api/miguel/confirm-date")
async def confirm_date(
    request: DateConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Called when the client selects a date and taps Send to Miguel.
    This is the ONLY place Telegram fires.
    Sends one complete card with everything: estimate, message,
    session summary, classification, and selected date.
    """
    try:
        short_id = request.intake_id
        selected_date = request.selected_date

        if short_id not in intake_store:
            raise HTTPException(status_code=404, detail="Intake not found.")

        intake = intake_store[short_id]

        # Store the selected date
        intake_store[short_id]["selected_date"] = selected_date
        print(f">>> Date confirmed: {short_id} → {selected_date}")

        # ── Fire single complete Telegram card ────────────────
        # This is the only Telegram notification in the system.
        # Miguel gets one card with everything he needs to decide.
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
            "selected_date": selected_date
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
    """
    Handles Miguel's replies from Telegram.
    Parses the intake ID directly from his message text.
    Format: APPROVE C7D3828A / DECLINE C7D3828A / ADJUST C7D3828A
    No global pointer — each reply is self-contained and concurrent-safe.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        text = message.get("text", "").strip()
        text_upper = text.upper()
        chat_id = str(message.get("chat", {}).get("id", ""))

        if chat_id != os.getenv("MIGUEL_CHAT_ID"):
            return {"status": "ignored"}

        # ── Parse intake ID from message ──────────────────────
        # Miguel replies: "APPROVE C7D3828A"
        # Extract the ID by checking each word against intake_store
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
            result = await db.execute(
                select(Intake).where(Intake.short_id == short_id)
            )
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
            result = await db.execute(
                select(Intake).where(Intake.short_id == short_id)
            )
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
                result = await db.execute(
                    select(Intake).where(Intake.short_id == short_id)
                )
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