# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: April 29, 2026

from fastapi import FastAPI, HTTPException
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
from tools.telegram_notifier import notify_miguel

app = FastAPI(
    title="Inkbook API",
    description="AI-native tattoo booking platform — Miguel",
    version="0.1.0"
)

# ─────────────────────────────────────────
# CORS — allows React frontend to call this
# ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
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
# HELPERS
# ─────────────────────────────────────────

def parse_crew_output(result: str) -> tuple:
    """
    Splits crew output into client message
    and session summary using delimiters.
    Client message goes to the client.
    Session summary goes to Miguel only.
    Neither audience sees the other's content.
    """
    if "---SESSION SUMMARY---" in result:
        parts = result.split("---SESSION SUMMARY---")
        client_message = parts[0].replace(
            "---CLIENT MESSAGE---", ""
        ).strip()
        session_summary = parts[1].strip()
    else:
        # Fallback if agent did not use delimiters
        client_message = result.strip()
        session_summary = "Session summary not generated. Review full output manually."

    return client_message, session_summary


def detect_classification(result: str) -> str:
    """
    Detects STRONG or SOFT classification
    from crew output using word boundary matching.
    Prevents false matches on words containing STRONG.
    """
    if re.search(r'\bSTRONG\b', result):
        return "STRONG"
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
    Session summary never leaves the server.
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
        # Miguel sees: classification, client message,
        # session summary, intake ID, approve/adjust/decline
        notify_miguel(
            classification=classification,
            client_name=request.client_name,
            client_contact=request.contact,
            client_message=client_message,
            session_summary=session_summary,
            intake_id=intake_id
        )

        # Return only client-appropriate data to frontend
        # Session summary never leaves the server
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
    Approval endpoint.
    Called when Miguel taps approve, adjust,
    or decline on his Telegram notification.
    """
    try:
        if request.decision == "approved":
            # TODO: send SMS confirmation to client
            # TODO: send Stripe deposit link
            # TODO: update database record
            return {
                "status": "success",
                "decision": "approved",
                "message": "Client confirmation will be sent",
                "intake_id": request.intake_id
            }

        elif request.decision == "adjusted":
            # TODO: send adjusted confirmation to client
            # TODO: update database record
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
            # TODO: send polite decline to client
            # TODO: update database record
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