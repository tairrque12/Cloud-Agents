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

# Add project root to path so crews and tools import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crews.tattoo_intake_crew import run_tattoo_intake_crew

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
# These define exactly what the chatbot
# sends to this endpoint
# ─────────────────────────────────────────

class GuidedDiscovery(BaseModel):
    meaning: Optional[str] = None
    imagery: Optional[str] = None
    style_notes: Optional[str] = None

class IntakeRequest(BaseModel):
    client_name: str
    contact: str
    size_selection: str          # small/medium/large/full_sleeve
    description: str
    placement: str
    styles: Optional[List[str]] = []
    is_cover_up: bool = False
    cover_up_description: Optional[str] = None
    budget_range: str            # under_200/200_500/500_1000/1000_plus
    preferred_timing: str        # within_2_weeks/within_1_month/etc
    reference_image: Optional[str] = None
    idea_readiness: str          # knows_exactly/needs_help
    guided_discovery: Optional[GuidedDiscovery] = None

class ApprovalRequest(BaseModel):
    intake_id: str
    decision: str                # approved/adjusted/declined
    adjusted_price: Optional[str] = None
    adjusted_dates: Optional[str] = None
    adjusted_message: Optional[str] = None

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
def health_check():
    """Health check — confirms API is running"""
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
    Receives chatbot form data from the React frontend.
    Fires the four-agent CrewAI crew.
    Returns the crew output for display and
    sends Telegram notification to Miguel.
    """
    try:
        # Convert request to dict for crew
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

        # Fire the crew
        result = run_tattoo_intake_crew(form_data)

        return {
            "status": "success",
            "message": "Request submitted to Miguel for review",
            "crew_output": result
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
    Triggers client confirmation SMS.
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