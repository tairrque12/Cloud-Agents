# api/artist_onboard_routes.py
# New-artist application onboarding only — does not modify Miguel's /api/miguel/* flow.
# Public artist directory: GET /api/artists (active artists for landing page).

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from api.artist_helpers import (
    allocate_unique_slug,
    generate_admin_secret,
    generate_referral_code,
    get_artist_by_slug,
    slug_from_name,
)
from api.onboard_email import send_application_notification
from db.database import get_db
from db.models import Artist

router = APIRouter(prefix="/api/artists", tags=["artist-onboard"])


def _artist_bio(artist: Artist) -> str | None:
    if artist.bio and str(artist.bio).strip():
        return str(artist.bio).strip()
    return None


def _artist_specialties(artist: Artist) -> list[str]:
    if artist.specialties:
        return list(artist.specialties)
    return []


@router.get("")
async def list_active_artists(db: AsyncSession = Depends(get_db)):
    """Public list of active artists for the landing page."""
    try:
        result = await db.execute(
            select(Artist)
            .options(
                load_only(
                    Artist.id,
                    Artist.slug,
                    Artist.name,
                    Artist.instagram_handle,
                    Artist.city,
                    Artist.state,
                    Artist.specialties,
                    Artist.bio,
                    Artist.status,
                )
            )
            .where(Artist.status == "active")
            .order_by(Artist.name)
        )
        artists = result.scalars().all()
    except SQLAlchemyError:
        logging.exception("list_active_artists database error")
        raise HTTPException(
            status_code=503,
            detail="Artist directory is temporarily unavailable.",
        )

    return {
        "artists": [
            {
                "id": str(artist.id),
                "name": artist.name,
                "slug": artist.slug,
                "city": artist.city,
                "state": artist.state,
                "instagram_handle": artist.instagram_handle,
                "specialties": _artist_specialties(artist),
                "bio": _artist_bio(artist),
            }
            for artist in artists
        ]
    }


PRICING_API_TO_DB = {
    "small_piece": "small",
    "half_day": "half_day",
    "full_day": "full_day",
    "full_sleeve": "full_sleeve",
}

PRICING_DB_TO_API = {v: k for k, v in PRICING_API_TO_DB.items()}

MAX_PROFILE_PHOTO_URL_LEN = 500_000


class PricingTierInput(BaseModel):
    min: int = Field(ge=0)
    max: int = Field(ge=0)
    deposit: int = Field(ge=0)


class PricingTiersInput(BaseModel):
    small_piece: PricingTierInput
    half_day: PricingTierInput
    full_day: PricingTierInput
    full_sleeve: PricingTierInput


class CreateArtistRequest(BaseModel):
    name: str
    profile_photo_url: Optional[str] = None
    studio_name: Optional[str] = None
    city: str
    state: str
    bio: str = Field(max_length=300)
    specialties: list[str] = []
    pricing_tiers: PricingTiersInput
    phone_number: str
    scheduling_tool: str
    scheduling_tool_other: Optional[str] = None
    email: str
    instagram_handle: Optional[str] = None
    notes: Optional[str] = None


def pricing_tiers_to_db(pricing: PricingTiersInput) -> dict[str, dict[str, int]]:
    raw = pricing.model_dump()
    return {
        PRICING_API_TO_DB[key]: {
            "min": int(raw[key]["min"]),
            "max": int(raw[key]["max"]),
            "deposit": int(raw[key]["deposit"]),
        }
        for key in PRICING_API_TO_DB
    }


def pricing_tiers_from_db(pricing_config: dict[str, Any] | None) -> dict[str, dict[str, int]]:
    if not pricing_config:
        return {}
    result: dict[str, dict[str, int]] = {}
    for db_key, api_key in PRICING_DB_TO_API.items():
        tier = pricing_config.get(db_key)
        if tier:
            result[api_key] = {
                "min": int(tier.get("min", 0)),
                "max": int(tier.get("max", 0)),
                "deposit": int(tier.get("deposit", 0)),
            }
    return result


def normalize_instagram(handle: str | None) -> str | None:
    if not handle:
        return None
    cleaned = handle.strip().lstrip("@")
    return cleaned or None


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone.strip())
    if len(digits) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid phone number.")
    return phone.strip()


async def _unique_referral_code(db: AsyncSession, name: str) -> str:
    for _ in range(20):
        code = generate_referral_code(name)
        taken = await db.execute(select(Artist).where(Artist.referral_code == code))
        if taken.scalar_one_or_none() is None:
            return code
    raise HTTPException(status_code=409, detail="Could not create application. Please try again.")


def artist_full_config(artist: Artist) -> dict[str, Any]:
    """Full artist config for new-artist booking pages."""
    location_parts = [p for p in (artist.city, artist.state) if p]
    return {
        "id": str(artist.id),
        "slug": artist.slug,
        "name": artist.name,
        "studio_name": artist.studio_name,
        "bio": artist.bio,
        "specialties": artist.specialties or [],
        "pricing_tiers": pricing_tiers_from_db(artist.pricing_config),
        "pricing_config": artist.pricing_config or {},
        "availability": artist.availability_config or {},
        "city": artist.city,
        "state": artist.state,
        "location": ", ".join(location_parts) if location_parts else None,
        "profile_photo_url": artist.profile_photo_url,
        "phone_number": artist.phone,
        "scheduling_tool": artist.scheduling_tool,
        "scheduling_tool_other": artist.scheduling_tool_other,
        "email": artist.email,
        "instagram_handle": artist.instagram_handle,
        "notes": artist.application_notes,
        "booking_url": f"/{artist.slug}",
        "status": artist.status,
    }


@router.post("")
async def create_artist(
    request: CreateArtistRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Artist name is required.")

    city = request.city.strip()
    state = request.state.strip()
    if not city or not state:
        raise HTTPException(status_code=400, detail="City and state are required.")

    bio = request.bio.strip()
    if not bio:
        raise HTTPException(status_code=400, detail="Bio is required.")

    slug = await allocate_unique_slug(db, slug_from_name(name))

    email = request.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    existing_email = await db.execute(select(Artist).where(Artist.email == email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An application with this email already exists.",
        )

    profile_photo_url = request.profile_photo_url
    if profile_photo_url and len(profile_photo_url) > MAX_PROFILE_PHOTO_URL_LEN:
        raise HTTPException(
            status_code=400,
            detail="Profile photo is too large. Please use a smaller image.",
        )

    phone = normalize_phone(request.phone_number)
    scheduling_tool = request.scheduling_tool.strip()
    if not scheduling_tool:
        raise HTTPException(status_code=400, detail="Select how you track appointments.")

    referral_code = await _unique_referral_code(db, name)

    artist = Artist(
        slug=slug,
        name=name,
        email=email,
        phone=phone,
        city=city,
        state=state,
        studio_name=(request.studio_name or "").strip() or None,
        bio=bio,
        specialties=[s.strip().lower() for s in request.specialties if s.strip()],
        pricing_config=pricing_tiers_to_db(request.pricing_tiers),
        profile_photo_url=profile_photo_url,
        scheduling_tool=scheduling_tool,
        scheduling_tool_other=(request.scheduling_tool_other or "").strip() or None,
        application_notes=(request.notes or "").strip() or None,
        instagram_handle=normalize_instagram(request.instagram_handle),
        admin_secret=generate_admin_secret(),
        referral_code=referral_code,
        status="pending",
        plan="starter",
        onboarded_at=None,
    )
    db.add(artist)
    try:
        await db.commit()
        await db.refresh(artist)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An application with this email or referral code already exists.",
        )
    except SQLAlchemyError:
        await db.rollback()
        logging.exception("create_artist database error")
        raise HTTPException(
            status_code=503,
            detail=(
                "Applications are temporarily unavailable while the database is "
                "being updated. Please try again in a few minutes."
            ),
        )

    notification_payload = {
        "id": str(artist.id),
        "name": artist.name,
        "slug": artist.slug,
        "email": artist.email,
        "phone_number": artist.phone,
        "city": artist.city,
        "state": artist.state,
        "studio_name": artist.studio_name,
        "instagram_handle": artist.instagram_handle,
        "scheduling_tool": artist.scheduling_tool,
        "scheduling_tool_other": artist.scheduling_tool_other,
        "bio": artist.bio,
        "specialties": artist.specialties or [],
        "pricing_tiers": pricing_tiers_from_db(artist.pricing_config),
        "notes": artist.application_notes,
        "profile_photo_url": artist.profile_photo_url,
    }
    background_tasks.add_task(send_application_notification, notification_payload)

    return {"id": str(artist.id), "slug": artist.slug}


async def fetch_artist_config(slug: str, db: AsyncSession) -> dict[str, Any]:
    from api.artist_helpers import get_miguel, normalize_slug

    normalized = normalize_slug(slug)
    if normalized == "miguel":
        from api.artist_helpers import get_miguel

        artist = await get_miguel(db)
        config = artist_full_config(artist)
        config["booking_url"] = "/book"
        return config

    artist = await get_artist_by_slug(db, slug)
    return artist_full_config(artist)
