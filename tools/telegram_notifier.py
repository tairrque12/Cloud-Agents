# tools/telegram_notifier.py
# Inkbook — Telegram Notification Tool
# Last updated: May 3, 2026
#
# Fires only from /api/miguel/confirm-date — after the client either
# selects a date or signals that none of the offered dates work.
# When selected_date == "NEEDS_ALTERNATE", the card flags this
# prominently so Miguel knows to reach out personally.
#
# NEW: Phone numbers are now tappable.
#   - Uses Telegram's HTML parse_mode with <a href="tel:..."> wrapper
#   - Numbers are normalized to E.164 format (+1 prefix for US)
#   - Tapping the number on Miguel's phone opens his dialer
#
# NEW: Reference images are sent to Telegram.
#   - Each base64 image is decoded and sent via sendPhoto BEFORE the card
#   - Miguel sees the photos first, then reads the card with all details
#   - Up to 3 images per intake (matches frontend MAX_IMAGES)

import os
import re
import base64
import requests
from typing import Optional, List
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MIGUEL_CHAT_ID = os.getenv("MIGUEL_CHAT_ID")

NEEDS_ALTERNATE_DATES = "NEEDS_ALTERNATE"

# ─────────────────────────────────────────
# PHONE NUMBER FORMATTING
# ─────────────────────────────────────────

def format_phone_for_tel_link(raw_contact: str) -> tuple[str, str]:
    """
    Returns (display_format, tel_link_format) for phone numbers.

    Examples:
        "334-820-9553"      → ("(334) 820-9553", "+13348209553")
        "3348209553"        → ("(334) 820-9553", "+13348209553")
        "(334) 820-9553"    → ("(334) 820-9553", "+13348209553")
        "+13348209553"      → ("(334) 820-9553", "+13348209553")
        "user@email.com"    → ("user@email.com", "")  — no tel link

    For non-phone contacts (emails) returns the original and empty tel string.
    """
    # If it's an email, return as-is, no tel link
    if "@" in raw_contact:
        return raw_contact, ""

    # Strip everything except digits and leading +
    digits_only = re.sub(r"[^\d]", "", raw_contact)

    # If we have 10 digits assume US, prepend 1
    if len(digits_only) == 10:
        digits_only = "1" + digits_only

    # If we don't have a recognizable phone, return raw
    if len(digits_only) < 10:
        return raw_contact, ""

    # Build E.164 tel link (e.g. +13348209553)
    tel_link = f"+{digits_only}"

    # Build pretty display: (334) 820-9553 for US, fallback for international
    if len(digits_only) == 11 and digits_only.startswith("1"):
        area = digits_only[1:4]
        prefix = digits_only[4:7]
        line = digits_only[7:11]
        display = f"({area}) {prefix}-{line}"
    else:
        # International or unusual — just show with + prefix
        display = f"+{digits_only}"

    return display, tel_link


# ─────────────────────────────────────────
# HTML ESCAPING (for parse_mode=HTML)
# ─────────────────────────────────────────

def html_escape(text: str) -> str:
    """
    Escape HTML special chars so Telegram parses our HTML correctly.
    Telegram's HTML mode requires escaping <, >, and & in any text
    that isn't part of a tag.
    """
    if not text:
        return ""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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
    selected_date: Optional[str] = None,
    image_count: int = 0
) -> str:
    """
    Build the Miguel notification card as HTML for Telegram parse_mode=HTML.
    Phone numbers are wrapped in <a href="tel:..."> so they're tappable.
    All other content is escaped to prevent HTML injection.
    """

    # ── Header ────────────────────────────────────────────────
    if selected_date == NEEDS_ALTERNATE_DATES:
        header = "🟠 NEEDS ALTERNATE DATES — Reach out personally"
    elif "STRONG" in classification.upper():
        header = "🟢 STRONG CLIENT — Ready to book"
    else:
        header = "🟡 SOFT CLIENT — Exploring, not ready yet"

    # ── Date line ─────────────────────────────────────────────
    if selected_date == NEEDS_ALTERNATE_DATES:
        date_line = (
            "📅 ⚠️ NONE OF THE OFFERED DATES WORK\n"
            "    Client is waiting for you to reach out and "
            "coordinate a date that fits their schedule."
        )
    elif selected_date:
        date_line = f"📅 Selected Date: {html_escape(selected_date)}"
    else:
        date_line = "📅 Date: Not selected"

    # ── Contact line — tappable phone ─────────────────────────
    display, tel_link = format_phone_for_tel_link(client_contact)
    if tel_link:
        # Wrap in <a href="tel:..."> for one-tap dial
        contact_line = f'Contact: <a href="tel:{tel_link}">{html_escape(display)}</a>'
    else:
        contact_line = f"Contact: {html_escape(display)}"

    # ── Reference images note ─────────────────────────────────
    if image_count > 0:
        image_note = (
            f"\n📎 {image_count} reference image"
            f"{'s' if image_count > 1 else ''} attached above ↑\n"
        )
    else:
        image_note = ""

    # ── Build card ────────────────────────────────────────────
    # Note: client_message and session_summary may contain text that
    # looks like HTML to Telegram — must escape it.
    card = f"""
{header}

👤 CLIENT
Name: {html_escape(client_name)}
{contact_line}
{image_note}
{date_line}

─────────────────────────
📝 DRAFTED RESPONSE
─────────────────────────

{html_escape(client_message)}

─────────────────────────
📋 SESSION SUMMARY
─────────────────────────

{html_escape(session_summary)}

─────────────────────────

🔖 INTAKE ID: {html_escape(intake_id)}

Reply with your decision + intake ID:
✅ APPROVE {html_escape(intake_id)}
✏️ ADJUST {html_escape(intake_id)}
❌ DECLINE {html_escape(intake_id)}
    """.strip()

    return card


# ─────────────────────────────────────────
# CORE SEND FUNCTIONS
# ─────────────────────────────────────────

def send_telegram_message(
    message: str,
    chat_id: str = None,
    parse_mode: str = "HTML"
):
    """
    Send a text message to Telegram.
    Defaults to HTML parse mode so <a href="tel:..."> links work.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")

    target_chat_id = chat_id or MIGUEL_CHAT_ID

    if not target_chat_id:
        raise ValueError("MIGUEL_CHAT_ID not found in .env")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    MAX_LENGTH = 4000
    chunks = [message[i:i+MAX_LENGTH] for i in range(0, len(message), MAX_LENGTH)]

    for chunk in chunks:
        payload = {
            "chat_id": target_chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        response = requests.post(url, json=payload)

        if not response.ok:
            # If HTML parsing failed for some reason, retry as plain text
            # so the message still gets through.
            if parse_mode == "HTML":
                print(f">>> HTML send failed, retrying as plain text: {response.text}")
                payload.pop("parse_mode", None)
                # Strip HTML tags for plain text fallback
                plain = re.sub(r"<[^>]+>", "", chunk)
                payload["text"] = plain
                response = requests.post(url, json=payload)
                if not response.ok:
                    raise ValueError(f"Telegram API error: {response.text}")
            else:
                raise ValueError(f"Telegram API error: {response.text}")

    return True


def send_telegram_photo(
    base64_image: str,
    caption: str = "",
    chat_id: str = None
) -> bool:
    """
    Send a base64-encoded image to Telegram via sendPhoto.

    Accepts either a raw base64 string or a data URL like
    "data:image/jpeg;base64,/9j/4AAQ...". Strips the data URL prefix
    if present, then decodes to bytes for the multipart upload.

    Returns True on success, False on failure (non-fatal — caller
    should still send the text card).
    """
    if not TELEGRAM_BOT_TOKEN:
        print(">>> Photo skipped: TELEGRAM_BOT_TOKEN not set")
        return False

    target_chat_id = chat_id or MIGUEL_CHAT_ID
    if not target_chat_id:
        print(">>> Photo skipped: MIGUEL_CHAT_ID not set")
        return False

    if not base64_image:
        return False

    # Strip data URL prefix if present
    # e.g. "data:image/jpeg;base64,/9j/4AAQ..." → "/9j/4AAQ..."
    if base64_image.startswith("data:"):
        try:
            base64_image = base64_image.split(",", 1)[1]
        except IndexError:
            print(">>> Photo skipped: malformed data URL")
            return False

    # Decode base64 to raw bytes
    try:
        image_bytes = base64.b64decode(base64_image)
    except Exception as e:
        print(f">>> Photo skipped: base64 decode failed — {e}")
        return False

    # Telegram has a 10MB limit for sendPhoto
    if len(image_bytes) > 10 * 1024 * 1024:
        print(f">>> Photo skipped: too large ({len(image_bytes)} bytes)")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    files = {
        "photo": ("reference.jpg", BytesIO(image_bytes), "image/jpeg")
    }
    data = {
        "chat_id": target_chat_id,
    }
    if caption:
        data["caption"] = caption

    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        if not response.ok:
            print(f">>> sendPhoto failed: {response.text}")
            return False
        return True
    except Exception as e:
        print(f">>> sendPhoto exception: {e}")
        return False


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
    selected_date: Optional[str] = None,
    reference_images: Optional[List[str]] = None
):
    """
    Notify Miguel on Telegram with:
      1. Reference images (sent first as photos, if any)
      2. Text card (with tappable phone, all client details)

    Sending images first means when Miguel opens the chat, he scrolls
    through the photos and lands on the card with all the details
    underneath. Photos as a "preview" before the prose.
    """
    client_message_trimmed = client_message[:1500] if len(client_message) > 1500 else client_message
    session_summary_trimmed = session_summary[:1000] if len(session_summary) > 1000 else session_summary

    images = reference_images or []
    image_count = len(images)

    # ── STEP 1: Send reference images first ──────────────────
    if image_count > 0:
        print(f">>> Sending {image_count} reference image(s) to Telegram...")
        for idx, img in enumerate(images, start=1):
            caption = f"Reference {idx}/{image_count} — {client_name}"
            success = send_telegram_photo(img, caption=caption)
            if success:
                print(f">>>   Image {idx}/{image_count} sent")
            else:
                print(f">>>   Image {idx}/{image_count} failed (continuing)")

    # ── STEP 2: Send the text card ───────────────────────────
    card = format_miguel_card(
        classification=classification,
        client_name=client_name,
        client_contact=client_contact,
        client_message=client_message_trimmed,
        session_summary=session_summary_trimmed,
        intake_id=intake_id,
        selected_date=selected_date,
        image_count=image_count
    )

    send_telegram_message(card, parse_mode="HTML")

    if selected_date == NEEDS_ALTERNATE_DATES:
        print(f"Telegram sent: {client_name} — NEEDS ALTERNATE DATES — {image_count} images")
    else:
        print(f"Telegram sent: {client_name} — date: {selected_date} — {image_count} images")


# ─────────────────────────────────────────
# CLIENT NOTIFICATION FUNCTIONS (unchanged)
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
        client_contact="334-820-9553",  # Test tappable phone formatting
        client_message="""What's up Marcus

That wolf piece on the outer arm sounds clean.
You're looking at $800-1,000 for that.

$100 deposit locks your spot.""",
        session_summary="""Full day session — realistic black and gray wolf,
full outer arm. 6+ hours.""",
        intake_id="TEST-001",
        selected_date="Saturday · June 6",
        reference_images=[]  # No test images for plain run
    )
    print("Done. Check Telegram.")