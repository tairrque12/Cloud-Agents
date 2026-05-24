# api/main.py
# Inkbook — FastAPI Backend
# Configured for: Miguel
# Last updated: May 3, 2026
#
# CALENDAR ARCHITECTURE:
# get_available_dates() is called in main.py BEFORE the crew fires.
# Raw dates returned directly to frontend as available_dates.
#
# TELEGRAM ARCHITECTURE:
# Telegram fires once — on /api/miguel/confirm-date (background task).
# Webhook now has DB fallback — if intake_store is empty after a Render
# restart, it reconstructs the intake from PostgreSQL so APPROVE/DECLINE
# still works even after the server restarted between submission and reply.
#
# PRICING ARCHITECTURE:
# Prices anchored to PRICING_TIERS by session type. Never scraped from prose.
#
# IMAGE ARCHITECTURE:
# reference_images accepts up to 3 base64 images. Stored in intake_store,
# sent to Miguel's Telegram as photos when client confirms date.
# Note: images are NOT stored in DB (too large). If Render restarts before
# date confirmation, images are lost. Acceptable MVP limitation.
#
# COVERAGE ARCHITECTURE:
# coverage field replaces ambiguous size (small/medium/large).
#
# ADMIN DASHBOARD ARCHITECTURE:
# /api/miguel/intakes reads from PostgreSQL — persistent across restarts.

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
import sys
import os
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
from db.models import Artist, Client, Intake, Estimate, Approval, BetaApplication
from api.artist_onboard_routes import router as artist_onboard_router, fetch_artist_config
from api.artist_helpers import (
    allocate_unique_slug,
    artist_public_profile,
    generate_admin_secret,
    generate_referral_code,
    get_artist_by_slug,
    get_miguel,
    get_pricing_tiers,
    normalize_pricing_config,
    normalize_slug,
    resolve_artist,
    slug_from_name,
    validate_slug,
)

app = FastAPI(
    title="Inkbook API",
    description="AI-native tattoo booking platform — Miguel",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chic-cuchufli-32d55a.netlify.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://([a-z0-9-]+\.)*netlify\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(artist_onboard_router)

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
    coverage: Optional[str] = None
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

class BetaApplicationRequest(BaseModel):
    name: str
    instagram: str
    email: str


class ArtistOnboardRequest(BaseModel):
    name: str
    email: str
    city: str
    slug: Optional[str] = None
    instagram_handle: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    studio_name: Optional[str] = None
    bio_short: Optional[str] = None
    specialties: Optional[List[str]] = []
    telegram_chat_id: Optional[str] = None
    booking_min_days: int = 14
    booking_max_days: int = 60
    pricing: Optional[dict] = None
    plan: str = "starter"

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
    placement: str = "",
    pricing_tiers: dict | None = None,
) -> dict:
    tiers = pricing_tiers or PRICING_TIERS
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

    tier = tiers[session_type]
    print(f">>> Pricing: session_type={session_type}, "
          f"min={tier['min']}, max={tier['max']}, deposit={tier['deposit']}")

    return {
        "price_min": tier["min"],
        "price_max": tier["max"],
        "deposit": tier["deposit"],
        "session_type": session_type,
    }


def format_dates_for_frontend(raw_dates: list[str]) -> list[str]:
    formatted = []
    for d in raw_dates:
        if '·' in d:
            formatted.append(d.strip())
        else:
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


async def reconstruct_intake_from_db(
    short_id: str,
    db: AsyncSession
) -> Optional[dict]:
    """
    Rebuilds an intake dict from PostgreSQL when intake_store is empty
    after a Render restart. This is the DB fallback for the Telegram webhook.

    Reconstructs everything needed to process APPROVE/DECLINE/ADJUST:
    - client_name, client_contact from clients table
    - client_message, session_summary from raw_crew_output
    - classification, placement from intakes table
    - artist_db_id, intake_db_id for approval storage

    Images are NOT reconstructed (not stored in DB — MVP limitation).
    """
    try:
        result = await db.execute(
            select(Intake)
            .options(
                selectinload(Intake.client),
                selectinload(Intake.artist),
            )
            .where(Intake.short_id == short_id)
        )
        intake_record = result.scalar_one_or_none()

        if not intake_record:
            return None

        client = intake_record.client
        artist = intake_record.artist

        # Re-parse client_message and session_summary from raw crew output
        client_message = ""
        session_summary = ""
        if intake_record.raw_crew_output:
            client_message, session_summary = parse_crew_output(
                intake_record.raw_crew_output
            )

        # Reconstruct pricing from size_selection
        size_to_tier = {
            "small": "small",
            "medium": "half_day",
            "large": "full_day",
            "full_sleeve": "full_sleeve",
        }
        session_type = size_to_tier.get(intake_record.size_selection or "medium", "half_day")
        artist_tiers = get_pricing_tiers(artist) if artist else PRICING_TIERS
        tier = artist_tiers.get(session_type, artist_tiers["half_day"])

        reconstructed = {
            "client_name": client.name if client else "Unknown",
            "client_contact": client.contact if client else "",
            "client_message": client_message,
            "session_summary": session_summary,
            "classification": intake_record.classification or "STRONG",
            "placement": intake_record.placement or "",
            "coverage": "not specified",
            "selected_date": intake_record.selected_date,
            "pricing": {
                "price_min": tier["min"],
                "price_max": tier["max"],
                "deposit": tier["deposit"],
                "session_type": session_type,
            },
            "preferred_timing": intake_record.preferred_timing or "",
            "image_count": 0,
            "reference_images": [],  # Not stored in DB
            "intake_id": short_id,
            "intake_db_id": str(intake_record.id),
            "artist_db_id": str(artist.id) if artist else "",
            "status": intake_record.status or "pending",
        }

        # Cache back into memory so subsequent calls don't hit DB
        intake_store[short_id] = reconstructed
        print(f">>> Reconstructed intake {short_id} from DB after restart")
        return reconstructed

    except Exception as e:
        print(f">>> DB reconstruction failed for {short_id}: {e}")
        return None


# ─────────────────────────────────────────
# BACKGROUND TASK WRAPPER
# ─────────────────────────────────────────

def send_telegram_in_background(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str,
    selected_date: Optional[str],
    reference_images: List[str],
):
    try:
        print(f">>> [Background] Starting Telegram delivery for {intake_id}")
        notify_miguel(
            classification=classification,
            client_name=client_name,
            client_contact=client_contact,
            client_message=client_message,
            session_summary=session_summary,
            intake_id=intake_id,
            selected_date=selected_date,
            reference_images=reference_images,
        )
        print(f">>> [Background] Telegram delivery complete for {intake_id}")
    except Exception as e:
        print(f">>> [Background] Telegram delivery failed for {intake_id}: {e}")
        traceback.print_exc()


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status": "running",
        "product": "Inkbook",
        "multi_artist": True,
        "version": "0.2.0"
    }


@app.get("/api/artists/check-slug/{slug}")
async def check_artist_slug(slug: str, db: AsyncSession = Depends(get_db)):
    normalized = normalize_slug(slug)
    try:
        validate_slug(normalized)
    except HTTPException as exc:
        return {"available": False, "slug": normalized, "reason": exc.detail}

    result = await db.execute(select(Artist).where(Artist.slug == normalized))
    taken = result.scalar_one_or_none() is not None
    return {"available": not taken, "slug": normalized}


@app.get("/api/artists/{slug}")
async def get_artist_profile(slug: str, db: AsyncSession = Depends(get_db)):
    return await fetch_artist_config(slug, db)


@app.post("/api/artists/onboard")
async def onboard_artist(
    request: ArtistOnboardRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        email = request.email.strip().lower()
        base_slug = request.slug.strip() if request.slug else slug_from_name(request.name)
        slug = await allocate_unique_slug(db, base_slug)

        instagram = None
        if request.instagram_handle and request.instagram_handle.strip():
            instagram = request.instagram_handle.strip().lstrip("@")

        existing_email = await db.execute(select(Artist).where(Artist.email == email))
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

        pricing_config = normalize_pricing_config(request.pricing)
        admin_secret = generate_admin_secret()
        referral_code = generate_referral_code(request.name)

        bio = (request.bio_short or "").strip()
        if not bio and request.specialties:
            specialty_text = ", ".join(request.specialties[:3])
            location = request.city
            if request.state:
                location = f"{request.city}, {request.state}"
            bio = f"Tattoo artist in {location} — {specialty_text}."
        elif not bio:
            location = request.city
            if request.state:
                location = f"{request.city}, {request.state}"
            bio = f"Tattoo artist based in {location}."

        from datetime import datetime, timezone
        artist = Artist(
            slug=slug,
            name=request.name.strip(),
            email=email,
            phone=request.phone,
            instagram_handle=instagram,
            city=request.city.strip(),
            state=(request.state or "").strip() or None,
            studio_name=(request.studio_name or "").strip() or None,
            bio_short=bio,
            specialties=request.specialties or [],
            pricing_config=pricing_config,
            admin_secret=admin_secret,
            status="active",
            plan=request.plan if request.plan in ("starter", "pro", "elite") else "starter",
            telegram_chat_id=(request.telegram_chat_id or "").strip() or None,
            referral_code=referral_code,
            booking_min_days=max(1, request.booking_min_days),
            booking_max_days=max(request.booking_min_days + 1, request.booking_max_days),
            onboarded_at=datetime.now(timezone.utc),
        )
        db.add(artist)
        await db.commit()
        await db.refresh(artist)

        print(f">>> Onboarded artist: {artist.name} · slug={artist.slug}")

        return {
            "status": "success",
            "artist": artist_public_profile(artist),
            "admin_url": f"/admin/{artist.slug}/{artist.admin_secret}",
            "booking_url": f"/book/{artist.slug}",
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")


@app.post("/api/beta/apply")
async def beta_apply(
    request: BetaApplicationRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        application = BetaApplication(
            name=request.name.strip(),
            instagram=request.instagram.strip(),
            email=request.email.strip().lower(),
        )
        db.add(application)
        await db.commit()
        print(f">>> Beta application: {request.name} · {request.instagram} · {request.email}")
        return {
            "status": "success",
            "message": "Application received"
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Application failed: {str(e)}"
        )


async def fetch_intakes_payload(db: AsyncSession, artist_id: uuid.UUID | None = None) -> list:
    query = (
        select(Intake)
        .options(
            selectinload(Intake.client),
            selectinload(Intake.approval),
            selectinload(Intake.estimate),
        )
        .order_by(desc(Intake.created_at))
        .limit(100)
    )
    if artist_id is not None:
        query = query.where(Intake.artist_id == artist_id)

    result = await db.execute(query)
    intakes = result.scalars().all()

    output = []
    for intake in intakes:
        client = intake.client
        approval = intake.approval
        estimate = intake.estimate

        selected_date = None
        if intake.short_id in intake_store:
            selected_date = intake_store[intake.short_id].get("selected_date")
        if selected_date is None:
            selected_date = intake.selected_date

        client_message = ""
        session_summary = ""
        coverage = ""
        image_count = 0
        if intake.short_id in intake_store:
            mem = intake_store[intake.short_id]
            client_message = mem.get("client_message", "")
            session_summary = mem.get("session_summary", "")
            coverage = mem.get("coverage", "")
            image_count = mem.get("image_count", 0)
        elif intake.raw_crew_output:
            if "---SESSION SUMMARY---" in intake.raw_crew_output:
                parts = intake.raw_crew_output.split("---SESSION SUMMARY---")
                client_message = parts[0].replace("---CLIENT MESSAGE---", "").strip()
                session_summary = parts[1].strip()
            else:
                client_message = intake.raw_crew_output.strip()

        status = intake.status
        if approval:
            status = approval.decision

        price_min = 0
        price_max = 0
        deposit = 0
        session_type = intake.size_selection or ""
        if estimate:
            price_min = float(estimate.price_min or 0)
            price_max = float(estimate.price_max or 0)
            deposit = float(estimate.deposit_amount or 0)
            session_type = estimate.session_type or session_type
        elif intake.short_id in intake_store:
            pricing = intake_store[intake.short_id].get("pricing", {})
            price_min = pricing.get("price_min", 0)
            price_max = pricing.get("price_max", 0)
            deposit = pricing.get("deposit", 0)
            session_type = pricing.get("session_type", session_type)

        output.append({
            "intake_id": intake.short_id,
            "created_at": intake.created_at.isoformat() if intake.created_at else None,
            "client_name": client.name if client else "Unknown",
            "client_contact": client.contact if client else "",
            "placement": intake.placement or "",
            "coverage": coverage,
            "description": intake.description or "",
            "styles": intake.styles or [],
            "is_cover_up": intake.is_cover_up,
            "budget_range": intake.budget_range or "",
            "preferred_timing": intake.preferred_timing or "",
            "selected_date": selected_date,
            "status": status,
            "classification": intake.classification or "",
            "price_min": price_min,
            "price_max": price_max,
            "deposit": deposit,
            "session_type": session_type,
            "client_message": client_message,
            "session_summary": session_summary,
            "image_count": image_count,
        })

    return output


@app.get("/api/artists/{slug}/intakes")
async def get_artist_intakes(slug: str, db: AsyncSession = Depends(get_db)):
    try:
        artist = await resolve_artist(db, slug)
        intakes = await fetch_intakes_payload(db, artist.id)
        return {"intakes": intakes, "artist": artist_public_profile(artist)}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load intakes: {str(e)}")


@app.get("/api/miguel/intakes")
async def get_intakes(db: AsyncSession = Depends(get_db)):
    """
    Returns Miguel's intakes for the admin dashboard (legacy route).
    """
    try:
        artist = await get_miguel(db)
        intakes = await fetch_intakes_payload(db, artist.id)
        return {"intakes": intakes}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f">>> DB query failed, falling back to memory store: {e}")
        result = []
        for short_id, intake in intake_store.items():
            result.append({
                "intake_id": short_id,
                "created_at": None,
                "client_name": intake.get("client_name", ""),
                "client_contact": intake.get("client_contact", ""),
                "placement": intake.get("placement", ""),
                "coverage": intake.get("coverage", ""),
                "description": "",
                "styles": [],
                "is_cover_up": False,
                "budget_range": "",
                "preferred_timing": intake.get("preferred_timing", ""),
                "selected_date": intake.get("selected_date"),
                "status": intake.get("status", "pending"),
                "classification": intake.get("classification", ""),
                "price_min": intake.get("pricing", {}).get("price_min", 0),
                "price_max": intake.get("pricing", {}).get("price_max", 0),
                "deposit": intake.get("pricing", {}).get("deposit", 0),
                "session_type": intake.get("pricing", {}).get("session_type", ""),
                "client_message": intake.get("client_message", ""),
                "session_summary": intake.get("session_summary", ""),
                "image_count": intake.get("image_count", 0),
            })
        return {"intakes": list(reversed(result))}


async def process_intake_request(
    request: IntakeRequest,
    artist: Artist,
    db: AsyncSession,
):
    try:
        budget_db = BUDGET_MAP.get(request.budget_range, "under_200")
        timing_db = TIMING_MAP.get(request.preferred_timing, "flexible")
        size_db = SIZE_MAP.get(request.size_selection, "medium")

        print(f">>> Mapped budget: {request.budget_range} → {budget_db}")
        print(f">>> Mapped timing: {request.preferred_timing} → {timing_db}")
        print(f">>> Mapped size: {request.size_selection} → {size_db}")
        print(f">>> Placement: {request.placement}")
        print(f">>> Coverage: {request.coverage}")

        print(">>> Fetching calendar dates...")
        raw_calendar_dates = get_available_dates(size_db)
        print(f">>> Raw calendar dates: {raw_calendar_dates}")
        available_dates = format_dates_for_frontend(raw_calendar_dates)
        print(f">>> Formatted dates for frontend: {available_dates}")

        all_images = resolve_reference_images(request)
        image_count = len(all_images)
        primary_image = all_images[0] if all_images else None
        print(f">>> Reference images: {image_count} uploaded")

        form_data = {
            "client_name": request.client_name,
            "contact": request.contact,
            "size_selection": size_db,
            "description": request.description,
            "placement": request.placement,
            "coverage": request.coverage or "not specified",
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
            "calendar_dates": raw_calendar_dates,
        }

        short_id = str(uuid.uuid4())[:8].upper()

        print(">>> Firing crew...")
        result, classification = run_tattoo_intake_crew(form_data)
        print(">>> Crew complete")
        print(f">>> Classification: {classification}")

        client_message, session_summary = parse_crew_output(result)
        pricing_tiers = get_pricing_tiers(artist)
        pricing = extract_pricing(
            result, size_db, request.placement, pricing_tiers=pricing_tiers
        )

        print(f">>> Pricing: ${pricing['price_min']}-${pricing['price_max']}, "
              f"deposit ${pricing['deposit']}, type {pricing['session_type']}")

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
            # Do not persist base64 in Postgres — images live in intake_store only
            # (Neon/console queries fail when reference_image_url holds multi-MB data URLs)
            primary_image_url="uploaded" if primary_image else None
        )
        print(f">>> Stored intake: {short_id}")

        client.total_intakes = (client.total_intakes or 0) + 1
        await db.commit()

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
            "reference_images": all_images,
            "placement": request.placement,
            "coverage": request.coverage or "not specified",
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
            "available_dates": available_dates,
            "preferred_timing": timing_db,
            "price_min": pricing["price_min"],
            "price_max": pricing["price_max"],
            "deposit": pricing["deposit"],
            "session_type": pricing["session_type"]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Intake failed: {str(e)}")


@app.post("/api/artists/{slug}/intake")
async def artist_intake(
    slug: str,
    request: IntakeRequest,
    db: AsyncSession = Depends(get_db)
):
    artist = await resolve_artist(db, slug)
    return await process_intake_request(request, artist, db)


@app.post("/api/miguel/intake")
async def intake(
    request: IntakeRequest,
    db: AsyncSession = Depends(get_db)
):
    artist = await get_miguel(db)
    return await process_intake_request(request, artist, db)


async def process_confirm_date(
    request: DateConfirmRequest,
    artist: Artist,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
):
    try:
        short_id = request.intake_id
        selected_date = request.selected_date

        if short_id not in intake_store:
            print(f">>> {short_id} not in memory — checking DB...")
            reconstructed = await reconstruct_intake_from_db(short_id, db)
            if not reconstructed:
                raise HTTPException(status_code=404, detail="Intake not found.")

        intake = intake_store[short_id]
        intake_store[short_id]["selected_date"] = selected_date

        # Persist selected_date to its dedicated DB column
        try:
            result = await db.execute(
                select(Intake).where(Intake.short_id == short_id)
            )
            intake_record = result.scalar_one_or_none()
            if intake_record:
                intake_record.selected_date = selected_date
                await db.commit()
        except Exception as e:
            print(f">>> Could not persist selected_date to DB: {e}")

        if selected_date == NEEDS_ALTERNATE_DATES:
            print(f">>> Client signaled NONE OF THE DATES WORK: {short_id}")
        else:
            print(f">>> Date confirmed: {short_id} → {selected_date}")

        placement = intake.get("placement", "not specified")
        coverage = intake.get("coverage", "not specified")
        coverage_line = f"Placement: {placement} — {coverage}\n\n"
        enriched_summary = coverage_line + intake["session_summary"]

        print(">>> Scheduling Telegram notification (background)...")
        background_tasks.add_task(
            send_telegram_in_background,
            classification=intake["classification"],
            client_name=intake["client_name"],
            client_contact=intake["client_contact"],
            client_message=intake["client_message"],
            session_summary=enriched_summary,
            intake_id=short_id,
            selected_date=selected_date,
            reference_images=intake.get("reference_images", []),
        )
        print(">>> Telegram task queued — returning to client")

        return {
            "status": "success",
            "message": f"Request sent to {artist.name}",
            "intake_id": short_id,
            "selected_date": selected_date,
            "needs_alternate": selected_date == NEEDS_ALTERNATE_DATES
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Date confirmation failed: {str(e)}")


@app.post("/api/artists/{slug}/confirm-date")
async def artist_confirm_date(
    slug: str,
    request: DateConfirmRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    artist = await resolve_artist(db, slug)
    return await process_confirm_date(request, artist, background_tasks, db)


@app.post("/api/miguel/confirm-date")
async def confirm_date(
    request: DateConfirmRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    artist = await get_miguel(db)
    return await process_confirm_date(request, artist, background_tasks, db)


async def process_approve(
    request: ApprovalRequest,
    artist: Artist,
    db: AsyncSession,
):
    try:
        short_id = request.intake_id

        if request.decision not in ("approved", "declined", "adjusted"):
            raise HTTPException(status_code=400, detail="Invalid decision.")

        result = await db.execute(
            select(Intake).where(Intake.short_id == short_id)
        )
        intake_record = result.scalar_one_or_none()

        if not intake_record:
            raise HTTPException(status_code=404, detail="Intake not found.")

        if intake_record.artist_id != artist.id:
            raise HTTPException(status_code=403, detail="Intake does not belong to this artist.")

        client_message = ""
        if short_id in intake_store:
            client_message = intake_store[short_id].get("client_message", "")
        elif intake_record.raw_crew_output:
            if "---SESSION SUMMARY---" in intake_record.raw_crew_output:
                parts = intake_record.raw_crew_output.split("---SESSION SUMMARY---")
                client_message = parts[0].replace("---CLIENT MESSAGE---", "").strip()
            else:
                client_message = intake_record.raw_crew_output.strip()

        existing = await db.execute(
            select(Approval).where(Approval.intake_id == intake_record.id)
        )
        existing_approval = existing.scalar_one_or_none()

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        if existing_approval:
            existing_approval.decision = request.decision
            existing_approval.client_message_sent = client_message
            existing_approval.message_sent_at = now
            if request.adjusted_message:
                existing_approval.adjusted_message = request.adjusted_message
        else:
            await store_approval(
                db=db,
                intake_id=intake_record.id,
                artist_id=artist.id,
                decision=request.decision,
                client_message_sent=client_message,
                adjusted_message=request.adjusted_message,
            )

        intake_record.status = request.decision
        await db.commit()

        if short_id in intake_store:
            intake_store[short_id]["status"] = request.decision

        print(f">>> Dashboard decision: {request.decision} → {short_id}")

        return {
            "status": "success",
            "decision": request.decision,
            "intake_id": short_id
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/api/artists/{slug}/approve")
async def artist_approve(
    slug: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    artist = await resolve_artist(db, slug)
    return await process_approve(request, artist, db)


@app.post("/api/miguel/approve")
async def approve(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Called by the admin dashboard when an artist approves or declines."""
    artist = await get_miguel(db)
    return await process_approve(request, artist, db)


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles Miguel's APPROVE/DECLINE/ADJUST replies on Telegram.

    DB FALLBACK: If intake_store is empty after a Render restart,
    reconstruct_intake_from_db() rebuilds the intake from PostgreSQL
    so the approval flow still works. This is the core restart-safety fix.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        text = message.get("text", "").strip()
        text_upper = text.upper()
        chat_id = str(message.get("chat", {}).get("id", ""))

        if chat_id != os.getenv("MIGUEL_CHAT_ID"):
            return {"status": "ignored"}

        # Find the intake ID in the message
        short_id = None
        for word in text.split():
            candidate = word.upper().strip()
            # Check memory first
            if candidate in intake_store:
                short_id = candidate
                break
            # If not in memory, check if it looks like an intake ID (8 hex chars)
            if len(candidate) == 8 and all(c in "0123456789ABCDEF" for c in candidate):
                short_id = candidate
                break

        if not short_id:
            send_telegram_message(
                "No intake ID found in your message.\n\n"
                "Reply with your decision and the intake ID:\n"
                "✅ APPROVE C7D3828A\n"
                "✏️ ADJUST C7D3828A\n"
                "❌ DECLINE C7D3828A"
            )
            return {"status": "no_id_found"}

        # ── DB FALLBACK: reconstruct if not in memory ─────────────
        if short_id not in intake_store:
            print(f">>> {short_id} not in memory after restart — reconstructing from DB...")
            reconstructed = await reconstruct_intake_from_db(short_id, db)
            if not reconstructed:
                send_telegram_message(
                    f"No intake found for ID: {short_id}\n\n"
                    "Double-check the ID and try again."
                )
                return {"status": "no_matching_intake"}
            print(f">>> Successfully reconstructed {short_id} from DB")

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