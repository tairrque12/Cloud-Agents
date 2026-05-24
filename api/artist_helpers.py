# api/artist_helpers.py
# Shared helpers for multi-artist routing and onboarding

import re
import secrets
import string
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Artist

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])?$")
RESERVED_SLUGS = frozenset({
    "admin", "api", "book", "onboard", "beta", "www", "app", "miguel",
})

DEFAULT_PRICING_CONFIG: dict[str, dict[str, int]] = {
    "small": {"min": 100, "max": 300, "deposit": 50},
    "half_day": {"min": 400, "max": 600, "deposit": 100},
    "full_day": {"min": 800, "max": 1000, "deposit": 100},
    "full_sleeve": {"min": 800, "max": 1000, "deposit": 100},
}

MIGUEL_PRICING_CONFIG = DEFAULT_PRICING_CONFIG.copy()


def normalize_slug(raw: str) -> str:
    slug = raw.strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def validate_slug(slug: str) -> None:
    if len(slug) < 3 or len(slug) > 50:
        raise HTTPException(
            status_code=400,
            detail="Booking link must be 3–50 characters.",
        )
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=400, detail="That booking link is reserved.")
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Use lowercase letters, numbers, and hyphens only.",
        )


def slug_from_instagram(handle: str) -> str:
    cleaned = handle.strip().lstrip("@").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned[:50] or "artist"


def slug_from_name(name: str) -> str:
    return normalize_slug(name) or "artist"


async def allocate_unique_slug(db: AsyncSession, base: str) -> str:
    """Pick a unique, valid slug from a base string (usually the artist name)."""
    root = normalize_slug(base)
    if len(root) < 3:
        root = f"artist-{secrets.token_hex(2)}"

    for attempt in range(100):
        candidate = root if attempt == 0 else f"{root}-{attempt + 1}"
        if candidate in RESERVED_SLUGS:
            continue
        try:
            validate_slug(candidate)
        except HTTPException:
            continue

        result = await db.execute(select(Artist).where(Artist.slug == candidate))
        if result.scalar_one_or_none() is None:
            return candidate

    raise HTTPException(
        status_code=409,
        detail="Could not generate a unique booking link. Try a different name.",
    )


def normalize_pricing_config(pricing: dict[str, Any] | None) -> dict[str, dict[str, int]]:
    if not pricing:
        return {k: v.copy() for k, v in DEFAULT_PRICING_CONFIG.items()}

    normalized: dict[str, dict[str, int]] = {}
    for tier, defaults in DEFAULT_PRICING_CONFIG.items():
        incoming = pricing.get(tier) or {}
        normalized[tier] = {
            "min": int(incoming.get("min", defaults["min"])),
            "max": int(incoming.get("max", defaults["max"])),
            "deposit": int(incoming.get("deposit", defaults["deposit"])),
        }
    return normalized


def get_pricing_tiers(artist: Artist) -> dict[str, dict[str, int]]:
    if artist.pricing_config:
        return normalize_pricing_config(artist.pricing_config)
    return {k: v.copy() for k, v in DEFAULT_PRICING_CONFIG.items()}


def generate_referral_code(name: str) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "", name.upper())[:6] or "ARTIST"
    suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{prefix}{suffix}"


def generate_admin_secret() -> str:
    return secrets.token_urlsafe(9)[:12]


def artist_public_profile(artist: Artist) -> dict[str, Any]:
    location_parts = [p for p in (artist.city, artist.state) if p]
    return {
        "slug": artist.slug,
        "name": artist.name,
        "instagram_handle": artist.instagram_handle,
        "city": artist.city,
        "state": artist.state,
        "location": ", ".join(location_parts) if location_parts else None,
        "studio_name": artist.studio_name,
        "bio": artist.bio,
        "specialties": artist.specialties or [],
        "booking_url": f"/book/{artist.slug}",
        "status": artist.status,
    }


async def get_artist_by_slug(db: AsyncSession, slug: str) -> Artist:
    normalized = normalize_slug(slug)
    result = await db.execute(
        select(Artist).where(Artist.slug == normalized)
    )
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found.")
    if artist.status != "active":
        raise HTTPException(status_code=403, detail="This artist page is not active.")
    return artist


async def get_miguel(db: AsyncSession) -> Artist:
    """Backward-compatible lookup for Miguel (slug or legacy name row)."""
    result = await db.execute(select(Artist).where(Artist.slug == "miguel"))
    artist = result.scalar_one_or_none()
    if not artist:
        result = await db.execute(select(Artist).where(Artist.name == "Miguel"))
        artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found.")
    if artist.status != "active":
        raise HTTPException(status_code=403, detail="This artist page is not active.")
    return artist


async def resolve_artist(db: AsyncSession, slug: str) -> Artist:
    normalized = normalize_slug(slug)
    if normalized == "miguel":
        return await get_miguel(db)
    return await get_artist_by_slug(db, normalized)
