# tools/telegram_notifier.py
# Inkbook — Telegram Notification Tool
# Sends Miguel his approval card for every intake
# Last updated: April 30, 2026

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
# CORE SEND FUNCTION
# Uses Telegram HTTP API directly
# No async — works inside FastAPI cleanly
# ─────────────────────────────────────────

def send_telegram_message(
    message: str,
    chat_id: str = None
):
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")

    target_chat_id = chat_id or MIGUEL_CHAT_ID

    if not target_chat_id:
        raise ValueError("MIGUEL_CHAT_ID not found in .env")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(url, json={
        "chat_id": target_chat_id,
        "text": message
    })

    if not response.ok:
        raise ValueError(f"Telegram API error: {response.text}")

    return response.json()


# ─────────────────────────────────────────
# MIGUEL NOTIFICATION
# ─────────────────────────────────────────

def notify_miguel(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str
):
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
# CLIENT NOTIFICATION FUNCTIONS
# Called after Miguel approves/declines
# ─────────────────────────────────────────

def send_client_confirmation(
    client_contact: str,
    client_name: str,
    client_message: str,
    intake_id: str
):
    """
    Sends confirmation to client after Miguel approves.
    Uses Twilio SMS if configured.
    Falls back to terminal print for MVP.
    """
    confirmation = f"""Hey {client_name}!

Miguel reviewed your request and you're confirmed.

{client_message}

Reply to this message with any questions.
Your deposit link will follow shortly to lock in your date."""

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if twilio_sid and twilio_token and twilio_number:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=confirmation,
                from_=twilio_number,
                to=client_contact
            )
            print(f"SMS confirmation sent to {client_name} at {client_contact}")
        except Exception as e:
            print(f"Twilio error: {str(e)}")
    else:
        print(f"\n{'='*50}")
        print(f"CLIENT CONFIRMATION — {client_name}")
        print(f"Contact: {client_contact}")
        print(f"{'='*50}")
        print(confirmation)
        print(f"{'='*50}\n")


def send_client_decline(
    client_contact: str,
    client_name: str
):
    """
    Sends polite decline to client.
    """
    decline_message = f"""Hey {client_name}

Thanks for reaching out. Unfortunately Miguel
isn't able to take this booking at this time.

Feel free to reach back out in the future —
he'd love to work with you when the timing is right."""

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if twilio_sid and twilio_token and twilio_number:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=decline_message,
                from_=twilio_number,
                to=client_contact
            )
        except Exception as e:
            print(f"Twilio error: {str(e)}")
    else:
        print(f"\n{'='*50}")
        print(f"CLIENT DECLINE — {client_name}")
        print(f"Contact: {client_contact}")
        print(f"{'='*50}")
        print(decline_message)
        print(f"{'='*50}\n")


def send_client_custom_message(
    client_contact: str,
    client_name: str,
    custom_message: str
):
    """
    Sends Miguel's adjusted message to client.
    """
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if twilio_sid and twilio_token and twilio_number:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=custom_message,
                from_=twilio_number,
                to=client_contact
            )
        except Exception as e:
            print(f"Twilio error: {str(e)}")
    else:
        print(f"\n{'='*50}")
        print(f"ADJUSTED MESSAGE — {client_name}")
        print(f"Contact: {client_contact}")
        print(f"{'='*50}")
        print(custom_message)
        print(f"{'='*50}\n")


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Sending test notification to Miguel...")
    notify_miguel(
        classification="STRONG",
        client_name="Marcus",
        client_contact="+15125551234",
        client_message="""What's up Marcus

That wolf piece on the outer arm sounds clean.
You're looking at $800-1,000 for that —
full day session. That's an estimate though,
I always check everything personally before
locking in the final price.

I've got Saturday May 17, Thursday May 29,
or Saturday June 7 open.

$100 deposit locks your spot. Let me know
which date works.""",
        session_summary="""Full day session — realistic black and gray wolf,
full outer arm, Native American inspired.
6+ hours. No other bookings this day.
Strong client, clear vision, no flags.""",
        intake_id="TEST-001"
    )
    print("Done. Check Telegram.")