# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: April 30, 2026

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import uuid
import re

# Add project root to path so crews and tools import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crews.tattoo_intake_crew import run_tattoo_intake_crew
from tools.telegram_notifier import (
    notify_miguel,
    send_telegram_message,
    send_client_confirmation,
    send_client_decline,
    send_client_custom_message
)

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
# IN-MEMORY INTAKE STORE
# Temporary for MVP — replace with DB later
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
        session_summary = "Session summary not generated. Review full output manually."

    return client_message, session_summary


def detect_classification(result: str) -> str:
    """
    Detects STRONG or SOFT classification from crew output.
    STRONG takes priority if both appear and STRONG comes first.
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
async def intake(request: IntakeRequest):
    """
    Main intake endpoint.
    Receives chatbot data from React frontend.
    Fires four-agent CrewAI crew.
    Splits output — client message vs session summary.
    Sends Miguel his full card via Telegram.
    Returns only client message to frontend.
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

        # Generate unique intake ID
        intake_id = str(uuid.uuid4())[:8].upper()

        # Fire the crew
        result = run_tattoo_intake_crew(form_data)

        # Detect classification
        classification = detect_classification(result)

        # Split into client message and session summary
        client_message, session_summary = parse_crew_output(result)

        # Send Miguel his full card via Telegram
        notify_miguel(
            classification=classification,
            client_name=request.client_name,
            client_contact=request.contact,
            client_message=client_message,
            session_summary=session_summary,
            intake_id=intake_id
        )

        # Store intake for webhook approval flow
        intake_store[intake_id] = {
            "client_name": request.client_name,
            "client_contact": request.contact,
            "client_message": client_message,
            "intake_id": intake_id,
            "status": "pending"
        }

        # Track Miguel's most recent intake ID
        miguel_last_intake_id["current"] = intake_id

        # Return only client-appropriate data
        return {
            "status": "success",
            "message": "Request submitted to Miguel for review",
            "intake_id": intake_id,
            "client_message": client_message
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Crew execution failed: {str(e)}"
        )


@app.post("/api/miguel/approve")
async def approve(request: ApprovalRequest):
    """
    Manual approval endpoint.
    Backup to the Telegram webhook flow.
    """
    try:
        if request.decision == "approved":
            return {
                "status": "success",
                "decision": "approved",
                "message": "Client confirmation will be sent",
                "intake_id": request.intake_id
            }

        elif request.decision == "adjusted":
            return {
                "status": "success",
                "decision": "adjusted",
                "message": "Adjusted confirmation will be sent",
                "intake_id": request.intake_id,
                "adjustments": {
                    "price": request.adjusted_price,
                    "dates": request.adjusted_dates,
                    "message": request.adjusted_message
                }
            }

        elif request.decision == "declined":
            return {
                "status": "success",
                "decision": "declined",
                "message": "Client decline message will be sent",
                "intake_id": request.intake_id
            }

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid decision. Must be approved/adjusted/declined"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Approval processing failed: {str(e)}"
        )


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    Telegram calls this every time Miguel
    sends a message to the Inkbook bot.
    Reads his reply and takes the right action.
    """
    try:
        body = await request.json()

        # Extract message from Telegram payload
        message = body.get("message", {})
        text = message.get("text", "").strip().upper()
        chat_id = str(message.get("chat", {}).get("id", ""))

        # Verify this message is from Miguel
        if chat_id != os.getenv("MIGUEL_CHAT_ID"):
            return {"status": "ignored"}

        # Get the most recent intake ID
        intake_id = miguel_last_intake_id.get("current")

        if not intake_id or intake_id not in intake_store:
            send_telegram_message(
                "No active intake found. "
                "A new booking request needs to come in first."
            )
            return {"status": "no_active_intake"}

        intake = intake_store[intake_id]

        if "APPROVE" in text or "✅" in text:
            send_client_confirmation(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"],
                client_message=intake["client_message"],
                intake_id=intake_id
            )
            intake_store[intake_id]["status"] = "approved"
            send_telegram_message(
                f"✅ Confirmed. Message sent to {intake['client_name']}."
            )

        elif "DECLINE" in text or "❌" in text:
            send_client_decline(
                client_contact=intake["client_contact"],
                client_name=intake["client_name"]
            )
            intake_store[intake_id]["status"] = "declined"
            send_telegram_message(
                f"❌ Decline sent to {intake['client_name']}."
            )

        elif "ADJUST" in text or "✏️" in text:
            send_telegram_message(
                f"✏️ What would you like to change for {intake['client_name']}?\n\n"
                f"Type your updated message and I will send it to them."
            )
            intake_store[intake_id]["status"] = "adjusting"

        else:
            # Check if Miguel is in adjust mode
            if intake_store[intake_id].get("status") == "adjusting":
                send_client_custom_message(
                    client_contact=intake["client_contact"],
                    client_name=intake["client_name"],
                    custom_message=message.get("text", "")
                )
                intake_store[intake_id]["status"] = "approved"
                send_telegram_message(
                    f"✅ Your updated message was sent to "
                    f"{intake['client_name']}."
                )

        return {"status": "ok"}

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "detail": str(e)}