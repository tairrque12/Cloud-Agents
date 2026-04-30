# tools/telegram_notifier.py
# Inkbook — Telegram Notification Tool
# Sends Miguel his approval card for every intake
# Last updated: April 29, 2026

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MIGUEL_CHAT_ID = os.getenv("MIGUEL_CHAT_ID")

# ─────────────────────────────────────────
# MESSAGE FORMATTER
# ─────────────────────────────────────────

def format_miguel_card(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str
) -> str:
    """
    Formats the full approval card Miguel receives.
    Strong clients get green header.
    Soft clients get yellow header.
    """

    if "STRONG" in classification.upper():
        header = "🟢 STRONG CLIENT — Ready to book"
    else:
        header = "🟡 SOFT CLIENT — Exploring, not ready yet"

    card = f"""
{header}

👤 CLIENT
Name: {client_name}
Contact: {client_contact}

─────────────────────────
📝 DRAFTED RESPONSE
─────────────────────────

{client_message}

─────────────────────────
📋 SESSION SUMMARY
─────────────────────────

{session_summary}

─────────────────────────

🔖 INTAKE ID: {intake_id}

Reply with:
✅ APPROVE
✏️ ADJUST
❌ DECLINE
    """.strip()

    return card


# ─────────────────────────────────────────
# SEND FUNCTION
# Uses Telegram HTTP API directly
# No async — works inside FastAPI cleanly
# ─────────────────────────────────────────

def send_telegram_message(
    message: str,
    chat_id: str = None
):
    """
    Sends a Telegram message using the HTTP API directly.
    No async required — works inside any context.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not found in .env"
        )

    target_chat_id = chat_id or MIGUEL_CHAT_ID

    if not target_chat_id:
        raise ValueError(
            "MIGUEL_CHAT_ID not found in .env"
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(url, json={
        "chat_id": target_chat_id,
        "text": message
    })

    if not response.ok:
        raise ValueError(
            f"Telegram API error: {response.text}"
        )

    return response.json()


def notify_miguel(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str
):
    """
    Main function called by FastAPI after crew runs.
    Formats and sends Miguel's full approval card.
    Client message and session summary are separate.
    Miguel sees both. Client never sees session summary.
    """
    card = format_miguel_card(
        classification=classification,
        client_name=client_name,
        client_contact=client_contact,
        client_message=client_message,
        session_summary=session_summary,
        intake_id=intake_id
    )

    send_telegram_message(card)
    print(f"Telegram notification sent to Miguel for {client_name}")


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Sending test notification to Miguel...")

    notify_miguel(
        classification="STRONG",
        client_name="Marcus",
        client_contact="+15125551234",
        client_message="""Hey Marcus!

I got your idea for the realistic black and gray wolf
on your full outer arm with that Native American vibe.
That's a solid concept, and a piece like that usually
runs between $800 and $1,000. That's an estimate though,
I always look everything over personally before locking
in the final price.

I've got Saturday the 17th, Thursday the 29th, or
Saturday the 31st open. Those are full day sessions.

A $100 deposit will lock your spot in.
Just let me know which day works.""",
        session_summary="""Full day session — realistic black and gray wolf,
full outer arm, Native American inspired.
6+ hours. No other bookings this day.
Realism and blackwork — expect heavy shading
and detail work across the full session.
Strong client, clear vision, no flags.""",
        intake_id="TEST-001"
    )

    print("Done. Check Telegram.")