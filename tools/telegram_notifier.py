# tools/telegram_notifier.py
# Inkbook — Telegram Notification Tool
# Last updated: May 2, 2026
#
# Fires only from /api/miguel/confirm-date — after the client either
# selects a date or signals that none of the offered dates work.
# When selected_date == "NEEDS_ALTERNATE", the card flags this
# prominently so Miguel knows to reach out personally.

import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MIGUEL_CHAT_ID = os.getenv("MIGUEL_CHAT_ID")

NEEDS_ALTERNATE_DATES = "NEEDS_ALTERNATE"

# ─────────────────────────────────────────
# MESSAGE FORMATTER
# ─────────────────────────────────────────

def format_miguel_card(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str,
    selected_date: Optional[str] = None
) -> str:

    # ── Header — flag alternate-date requests at the very top ──
    # Override the standard STRONG/SOFT header when client signals
    # none of the offered dates work. Miguel sees this first.
    if selected_date == NEEDS_ALTERNATE_DATES:
        header = "🟠 NEEDS ALTERNATE DATES — Reach out personally"
    elif "STRONG" in classification.upper():
        header = "🟢 STRONG CLIENT — Ready to book"
    else:
        header = "🟡 SOFT CLIENT — Exploring, not ready yet"

    # ── Date line ──────────────────────────────────────────────
    if selected_date == NEEDS_ALTERNATE_DATES:
        date_line = (
            "📅 ⚠️ NONE OF THE OFFERED DATES WORK\n"
            "    Client is waiting for you to reach out and "
            "coordinate a date that fits their schedule."
        )
    elif selected_date:
        date_line = f"📅 Selected Date: {selected_date}"
    else:
        date_line = "📅 Date: Not selected"

    card = f"""
{header}

👤 CLIENT
Name: {client_name}
Contact: {client_contact}

{date_line}

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

Reply with your decision + intake ID:
✅ APPROVE {intake_id}
✏️ ADJUST {intake_id}
❌ DECLINE {intake_id}
    """.strip()

    return card


# ─────────────────────────────────────────
# CORE SEND FUNCTION
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

    MAX_LENGTH = 4000
    chunks = [message[i:i+MAX_LENGTH] for i in range(0, len(message), MAX_LENGTH)]

    for chunk in chunks:
        response = requests.post(url, json={
            "chat_id": target_chat_id,
            "text": chunk
        })

        if not response.ok:
            raise ValueError(f"Telegram API error: {response.text}")

    return True


# ─────────────────────────────────────────
# MIGUEL NOTIFICATION
# ─────────────────────────────────────────

def notify_miguel(
    classification: str,
    client_name: str,
    client_contact: str,
    client_message: str,
    session_summary: str,
    intake_id: str,
    selected_date: Optional[str] = None
):
    client_message_trimmed = client_message[:1500] if len(client_message) > 1500 else client_message
    session_summary_trimmed = session_summary[:1000] if len(session_summary) > 1000 else session_summary

    card = format_miguel_card(
        classification=classification,
        client_name=client_name,
        client_contact=client_contact,
        client_message=client_message_trimmed,
        session_summary=session_summary_trimmed,
        intake_id=intake_id,
        selected_date=selected_date
    )

    send_telegram_message(card)

    if selected_date == NEEDS_ALTERNATE_DATES:
        print(f"Telegram sent: {client_name} — NEEDS ALTERNATE DATES")
    else:
        print(f"Telegram sent: {client_name} — date: {selected_date}")


# ─────────────────────────────────────────
# CLIENT NOTIFICATION FUNCTIONS
# ─────────────────────────────────────────

def send_client_confirmation(
    client_contact: str,
    client_name: str,
    client_message: str,
    intake_id: str
):
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
You're looking at $800-1,000 for that.

$100 deposit locks your spot.""",
        session_summary="""Full day session — realistic black and gray wolf,
full outer arm. 6+ hours.""",
        intake_id="TEST-001",
        selected_date="NEEDS_ALTERNATE"
    )
    print("Done. Check Telegram.")