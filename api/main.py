# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: April 30, 2026

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import os
import uuid
import re

# Add project root to path
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

# ─────────────────────────────────────────
# CORS
# ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    adjusted_price: Optional[str] = None
    adjusted_dates: Optional[str] = None
    adjusted_message: Optional[str] = None

# ─────────────────────────────────────────
# IN-MEMORY STORE
# Used for webhook approval flow
# Maps short_id to intake data
# ─────────────────────────────────────────

intake_store = {}
miguel_last_intake_id = {}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def parse_crew_output(result: str) -> tuple:
    """
    Splits crew output into client message
    and session summary using delimiters.
    """
    if "---SESSION SUMMARY---" in result:
        parts = result.split("---SESSION SUMMARY---")
        client_message = parts[0].replace(
            "---CLIENT MESSAGE---", ""
        ).strip()
        session_summary = parts[1].strip()
    else:
        client_message = result.strip()
        session_summary = "Session summary not generated."

    return client_message, session_summary


def detect_classification(result: str) -> str:
    """
    Detects STRONG or SOFT from crew output.
    STRONG wins if it appears before SOFT.
    """
    result_upper = result.upper()
    strong_present = "STRONG" in result_upper
    soft_present = "SOFT" in result_upper

    if strong_present and not soft_present:
        return "STRONG"
    elif strong_present and soft_present:
        if result_upper.index("STRONG") < result_upper.index("SOFT"):
            return "STRONG"
        else:
            return "SOFT"
    elif soft_present:
        return "SOFT"
    else:
        return "SOFT"


async def get_or_create_client(
    db: AsyncSession,
    name: str,
    contact: str
) -> Client:
    """
    Upserts a client record.
    Same contact = same client.
    Updates name if it changed.
    """
    result = await db.execute(
        select(Client).where(Client.contact == contact)
    )
    client = result.scalar_one_or_none()

    if client:
        # Update name in case it changed
        client.name = name
        return client

    # Create new client
    client = Client(
        name=name,
        contact=contact,
        contact_type="phone" if contact.startswith("+") else "email"
    )
    db.add(client)
    await db.flush()  # Get the ID without committing
    return client


async def get_miguel(db: AsyncSession) -> Artist:
    """
    Fetches Miguel's artist record.
    For MVP this is the only artist.
    """
    result = await db.execute(
        select(Artist).where(Artist.name == "Miguel")
    )
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(
            status_code=500,
            detail="Artist record not found. Check database seed."
        )

    return artist


async def store_intake(
    db: AsyncSession,
    short_id: str,
    artist_id: uuid.UUID,
    client_id: uuid.UUID,
    request: IntakeRequest,
    classification: str,
    raw_crew_output: str
) -> Intake:
    """
    Stores the full intake record in the database.
    Called after crew runs successfully.
    """
    guided = request.guided_discovery

    intake = Intake(
        short_id=short_id,
        artist_id=artist_id,
        client_id=client_id,
        classification=classification,
        size_selection=request.size_selection,
        description=request.description,
        placement=request.placement,
        styles=request.styles or [],
        is_cover_up=request.is_cover_up,
        cover_up_description=request.cover_up_description,
        budget_range=request.budget_range,
        preferred_timing=request.preferred_timing,
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
    """
    Stores Miguel's approval decision in the database.
    Called when Miguel replies on Telegram.
    """
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
    Main intake endpoint.
    Receives chatbot data from React frontend.
    Fires four-agent CrewAI crew.
    Stores everything in PostgreSQL.
    Sends Miguel his Telegram approval card.
    Returns only client-appropriate data.
    """
    try:
        form_data = {
            "client_name": request.client_name,
            "contact": request.contact,
            "size_selection": request.size_selection,
            "description": request.description,
            "placement": request.placement,
            "styles": request.styles,
            "is_cover_up": request.is_cover_up,
            "cover_up_description": request.cover_up_description,
            "budget_range": request.budget_range,
            "preferred_timing": request.preferred_timing,
            "reference_image": request.reference_image,
            "idea_readiness": request.idea_readiness,
            "guided_discovery": request.guided_discovery.dict()
                if request.guided_discovery else None
        }

        # Generate unique short ID for Telegram card
        short_id = str(uuid.uuid4())[:8].upper()

        # Fire the crew
        result = run_tattoo_intake_crew(form_data)

        # Detect classification
        classification = detect_classification(result)

        # Split into client message and session summary
        client_message, session_summary = parse_crew_output(result)

        # ─────────────────────────────────────
        # DATABASE WRITES
        # ─────────────────────────────────────

        # Get Miguel's artist record
        artist = await get_miguel(db)

        # Upsert client record
        client = await get_or_create_client(
            db=db,
            name=request.client_name,
            contact=request.contact
        )

        # Store the intake
        intake_record = await store_intake(
            db=db,
            short_id=short_id,
            artist_id=artist.id,
            client_id=client.id,
            request=request,
            classification=classification,
            raw_crew_output=result
        )

        # Update client intake count
        client.total_intakes = (client.total_intakes or 0) + 1

        # ─────────────────────────────────────
        # TELEGRAM NOTIFICATION
        # ─────────────────────────────────────

        notify_miguel(
            classification=classification,
            client_name=request.client_name,
            client_contact=request.contact,
            client_message=client_message,
            session_summary=session_summary,
            intake_id=short_id
        )

        # Store in memory for webhook approval flow
        intake_store[short_id] = {
            "client_name": request.client_name,
            "client_contact": request.contact,
            "client_message": client_message,
            "intake_id": short_id,
            "intake_db_id": str(intake_record.id),
            "artist_db_id": str(artist.id),
            "status": "pending"
        }

        # Track most recent intake for webhook
        miguel_last_intake_id["current"] = short_id

        return {
            "status": "success",
            "message": "Request submitted to Miguel for review",
            "intake_id": short_id,
            "client_message": client_message
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Crew execution failed: {str(e)}"
        )


@app.post("/api/miguel/approve")
async def approve(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manual approval endpoint.
    Backup to the Telegram webhook flow.
    """
    try:
        if request.decision == "approved":
            return {
                "status": "success",
                "decision": "approved",
                "intake_id": request.intake_id
            }
        elif request.decision == "adjusted":
            return {
                "status": "success",
                "decision": "adjusted",
                "intake_id": request.intake_id
            }
        elif request.decision == "declined":
            return {
                "status": "success",
                "decision": "declined",
                "intake_id": request.intake_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid decision."
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Approval failed: {str(e)}"
        )


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Telegram webhook endpoint.
    Receives Miguel's replies.
    Stores approval decisions in database.
    Triggers client notifications.
    """
    try:
        body = await request.json()

        message = body.get("message", {})
        text = message.get("text", "").strip().upper()
        chat_id = str(message.get("chat", {}).get("id", ""))

        # Verify this is from Miguel
        if chat_id != os.getenv("MIGUEL_CHAT_ID"):
            return {"status": "ignored"}

        # Get most recent intake
        short_id = miguel_last_intake_id.get("current")

        if not short_id or short_id not in intake_store:
            send_telegram_message(
                "No active intake found. "
                "A new booking request needs to come in first."
            )
            return {"status": "no_active_intake"}

        intake = intake_store[short_id]

        if "APPROVE" in text or "✅" in text:

            # Send client confirmation
            send_client_confirmation(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"],
                client_message=intake["client_message"],
                intake_id=short_id
            )

            # Store approval in database
            async with get_db() as db_session:
                await store_approval(
                    db=db_session,
                    intake_id=uuid.UUID(intake["intake_db_id"]),
                    artist_id=uuid.UUID(intake["artist_db_id"]),
                    decision="approved",
                    client_message_sent=intake["client_message"]
                )

                # Update intake status
                result = await db_session.execute(
                    select(Intake).where(
                        Intake.short_id == short_id
                    )
                )
                intake_record = result.scalar_one_or_none()
                if intake_record:
                    intake_record.status = "approved"

                await db_session.commit()

            intake_store[short_id]["status"] = "approved"
            send_telegram_message(
                f"✅ Confirmed. Message sent to {intake['client_name']}."
            )

        elif "DECLINE" in text or "❌" in text:

            send_client_decline(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"]
            )

            # Store decline in database
            async with get_db() as db_session:
                await store_approval(
                    db=db_session,
                    intake_id=uuid.UUID(intake["intake_db_id"]),
                    artist_id=uuid.UUID(intake["artist_db_id"]),
                    decision="declined",
                    client_message_sent="Decline message sent."
                )

                result = await db_session.execute(
                    select(Intake).where(
                        Intake.short_id == short_id
                    )
                )
                intake_record = result.scalar_one_or_none()
                if intake_record:
                    intake_record.status = "declined"

                await db_session.commit()

            intake_store[short_id]["status"] = "declined"
            send_telegram_message(
                f"❌ Decline sent to {intake['client_name']}."
            )

        elif "ADJUST" in text or "✏️" in text:

            send_telegram_message(
                f"✏️ What would you like to change for "
                f"{intake['client_name']}?\n\n"
                f"Type your updated message and I will send it."
            )
            intake_store[short_id]["status"] = "adjusting"

        else:
            # Check if Miguel is in adjust mode
            if intake_store[short_id].get("status") == "adjusting":
                custom_msg = message.get("text", "")

                send_client_custom_message(
                    client_contact=intake["client_contact"],
                    client_name=intake["client_name"],
                    custom_message=custom_msg
                )

                # Store adjusted approval in database
                async with get_db() as db_session:
                    await store_approval(
                        db=db_session,
                        intake_id=uuid.UUID(intake["intake_db_id"]),
                        artist_id=uuid.UUID(intake["artist_db_id"]),
                        decision="adjusted",
                        client_message_sent=custom_msg,
                        adjusted_message=custom_msg
                    )

                    result = await db_session.execute(
                        select(Intake).where(
                            Intake.short_id == short_id
                        )
                    )
                    intake_record = result.scalar_one_or_none()
                    if intake_record:
                        intake_record.status = "adjusted"

                    await db_session.commit()

                intake_store[short_id]["status"] = "approved"
                send_telegram_message(
                    f"✅ Your updated message was sent to "
                    f"{intake['client_name']}."
                )

        return {"status": "ok"}

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "detail": str(e)}