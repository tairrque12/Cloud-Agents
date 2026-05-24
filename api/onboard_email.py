# api/onboard_email.py
# Admin notification emails for new artist applications.

import os
import smtplib
from email.message import EmailMessage
from typing import Any


def _admin_email() -> str:
    return os.getenv("ADMIN_EMAIL", "riq@inkbook.io")


def _format_application_body(data: dict[str, Any]) -> str:
    pricing = data.get("pricing_tiers") or {}
    lines = [
        "New Inkbook artist application",
        "",
        f"Name: {data.get('name', '')}",
        f"Slug: {data.get('slug', '')}",
        f"Email: {data.get('email', '')}",
        f"Phone: {data.get('phone_number', '')}",
        f"City / State: {data.get('city', '')}, {data.get('state', '')}",
        f"Studio: {data.get('studio_name') or '—'}",
        f"Instagram: {data.get('instagram_handle') or '—'}",
        f"Scheduling tool: {data.get('scheduling_tool', '')}",
    ]
    if data.get("scheduling_tool_other"):
        lines.append(f"Scheduling tool (other): {data['scheduling_tool_other']}")
    lines.extend([
        "",
        "Bio:",
        data.get("bio", ""),
        "",
        f"Specialties: {', '.join(data.get('specialties') or []) or '—'}",
        "",
        "Pricing tiers:",
    ])
    for tier, values in pricing.items():
        if isinstance(values, dict):
            lines.append(
                f"  {tier}: ${values.get('min')}–${values.get('max')} "
                f"(deposit ${values.get('deposit')})"
            )
    if data.get("notes"):
        lines.extend(["", "Setup notes:", data["notes"]])
    if data.get("profile_photo_url"):
        lines.append("")
        lines.append("Profile photo: provided (stored in application record)")
    lines.extend(["", f"Artist ID: {data.get('id', '')}"])
    return "\n".join(lines)


def send_application_notification(data: dict[str, Any]) -> None:
    """Send application details to the founder. Logs and continues if SMTP is unavailable."""
    recipient = _admin_email()
    subject = f"New Inkbook artist application — {data.get('name', 'Unknown')}"
    body = _format_application_body(data)

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", smtp_user or "notifications@inkbook.io")

    if not smtp_host or not smtp_user or not smtp_password:
        print(f">>> [onboard email] SMTP not configured — would notify {recipient}")
        print(body)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f">>> [onboard email] Sent application notification to {recipient}")
    except Exception as exc:
        print(f">>> [onboard email] Failed to send ({exc}) — logging application:")
        print(body)
