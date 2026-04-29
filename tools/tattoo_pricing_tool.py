# tools/tattoo_pricing_tool.py
# Inkbook — Tattoo Pricing Tool
# Configured for: Miguel
# Last updated: April 28, 2026

# ─────────────────────────────────────────
# ARTIST RATE CONFIGURATION — MIGUEL
# All prices are ESTIMATES only.
# Miguel reviews every request and confirms
# final pricing before anything is locked in.
# ─────────────────────────────────────────

ARTIST_RATES = {
    "small": {
        "label": "Small piece",
        "price_range": "$100 minimum",
        "price_min": 100,
        "deposit": 50,
        "estimated_time": "1-2 hours",
    },
    "half_day": {
        "label": "Half day session",
        "price_range": "$300 - $500",
        "price_min": 300,
        "price_max": 500,
        "deposit": 100,
        "estimated_time": "3-5 hours",
    },
    "full_day": {
        "label": "Full day session",
        "price_range": "$800 - $1,000",
        "price_min": 800,
        "price_max": 1000,
        "deposit": 100,
        "estimated_time": "6+ hours",
    },
    "full_sleeve": {
        "label": "Full sleeve — multiple sessions",
        "sessions_needed": "4-5 sessions",
        "price_range": "$800 - $1,000 per session",
        "price_note": "Discounts may be available for full sleeves — Miguel will discuss this with you directly.",
        "deposit": 100,
        "estimated_time": "4-5 full day sessions",
    }
}

DISCLAIMER = (
    "⚠️ This is an estimate only. Miguel reviews "
    "every request personally and confirms the final "
    "price before your appointment is locked in. "
    "Final pricing may vary based on design complexity, "
    "detail level, and placement."
)


def calculate_tattoo_price(
    session_type: str,
    num_sessions: int = 1,
    is_multi_session: bool = False
) -> str:
    """
    Calculates a tattoo price estimate based on session type.
    Never returns a final price — always an estimate.
    Miguel confirms all final pricing personally.
    """
    valid_types = ["small", "half_day", "full_day", "full_sleeve"]
    if session_type not in valid_types:
        return (
            f"Session type '{session_type}' not recognized. "
            f"Valid types: {', '.join(valid_types)}"
        )

    rates = ARTIST_RATES[session_type].copy()

    if session_type == "full_sleeve":
        output = f"""
📋 PRICE ESTIMATE — {rates['label'].upper()}

Sessions needed: {rates['sessions_needed']}
Rate per session: {rates['price_range']}
Deposit per session: ${rates['deposit']}
Estimated time: {rates['estimated_time']}

💡 {rates['price_note']}

{DISCLAIMER}
        """.strip()

    else:
        output = f"""
📋 PRICE ESTIMATE — {rates['label'].upper()}

Estimated range: {rates['price_range']}
Deposit to hold your slot: ${rates['deposit']}
Estimated session time: {rates['estimated_time']}

{DISCLAIMER}
        """.strip()

    return output


def get_deposit_amount(session_type: str) -> str:
    """Returns deposit amount for a given session type."""
    valid_types = ["small", "half_day", "full_day", "full_sleeve"]
    if session_type not in valid_types:
        return (
            f"Session type not recognized. "
            f"Valid types: {', '.join(valid_types)}"
        )

    deposit = ARTIST_RATES[session_type]["deposit"]
    return (
        f"Deposit required: ${deposit}\n"
        f"Applied toward your final tattoo price.\n"
        f"Deposit link sent once Miguel approves your request."
    )


def classify_session_type(tattoo_description: str) -> str:
    """
    Classifies a tattoo description into a session type
    based on keywords and scope indicators.
    Confidence score helps Miguel prioritize his review.
    """
    description_lower = tattoo_description.lower()

    # Full sleeve detection
    sleeve_keywords = [
        "sleeve", "full arm", "arm sleeve",
        "full sleeve", "half sleeve"
    ]
    if any(k in description_lower for k in sleeve_keywords):
        return (
            "SESSION TYPE: full_sleeve\n"
            "REASON: Client described a sleeve — "
            "typically 4-5 full day sessions.\n"
            "CONFIDENCE: High\n"
            "NOTE: Miguel will confirm session count "
            "and discuss sleeve discount directly."
        )

    # Full day detection — 6+ hours
    full_day_keywords = [
        "full inner arm", "full outer arm", "upper arm",
        "back piece", "large", "detailed", "realistic",
        "portrait", "chest piece", "thigh", "ribs",
        "full back", "large scale", "big", "cover up"
    ]
    if any(k in description_lower for k in full_day_keywords):
        return (
            "SESSION TYPE: full_day\n"
            "REASON: Large or complex piece — "
            "estimated 6+ hours.\n"
            "CONFIDENCE: Medium-High\n"
            "NOTE: Miguel confirms final scope and timing."
        )

    # Half day detection — 3-5 hours
    half_day_keywords = [
        "medium", "forearm", "calf", "shoulder",
        "script", "lettering", "flowers", "animal",
        "geometric", "detailed", "color"
    ]
    if any(k in description_lower for k in half_day_keywords):
        return (
            "SESSION TYPE: half_day\n"
            "REASON: Medium piece — estimated 3-5 hours.\n"
            "CONFIDENCE: Medium\n"
            "NOTE: Miguel confirms final scope."
        )

    # Small detection — 1-2 hours
    small_keywords = [
        "small", "tiny", "mini", "simple", "minimal",
        "symbol", "word", "date", "initials", "little",
        "quick", "fine line", "single needle"
    ]
    if any(k in description_lower for k in small_keywords):
        return (
            "SESSION TYPE: small\n"
            "REASON: Small simple piece — estimated 1-2 hours.\n"
            "CONFIDENCE: Medium\n"
            "NOTE: Miguel confirms final scope."
        )

    # Default — not enough info
    return (
        "SESSION TYPE: half_day\n"
        "REASON: Not enough detail to classify precisely. "
        "Defaulting to mid-range estimate.\n"
        "CONFIDENCE: Low — Miguel should clarify scope "
        "before confirming price."
    )