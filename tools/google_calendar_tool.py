# tools/google_calendar_tool.py
# Inkbook — Google Calendar Tool
# Reads Miguel's real calendar to find available dates
# Last updated: May 3, 2026
#
# KEY FIX: Multi-day events (Out of shop, Valley appointments, etc.)
# now correctly mark ALL days in the range as busy, not just the start.
# Previously only start_date[:10] was added to busy_dates, meaning
# a 5-day "Out of shop" block only blocked day 1.
#
# DAY FILTER: All weekdays are now considered available (Mon-Sat).
# Sunday is excluded as Miguel typically doesn't work Sundays.
# Previously only Sat/Thu/Tue were checked — too restrictive.

import os
from datetime import datetime, timedelta, date
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = "migueltattooappts@gmail.com"
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(__file__), "../config/google_credentials.json"
)
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Days Miguel works — Sunday excluded
WORKING_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}


def _expand_event_dates(event: dict) -> set:
    """
    Returns the set of all calendar dates an event occupies.

    Handles two event formats:
      - Timed events: use "dateTime" field (e.g. "2026-05-10T14:00:00-05:00")
        → extract date portion only, mark that single day busy
      - All-day / multi-day events: use "date" field (e.g. "2026-05-18")
        → Google Calendar end date for all-day events is EXCLUSIVE
          (an event "May 18–22" has start=May 18, end=May 23)
        → Expand the full range: May 18, 19, 20, 21, 22

    This is the critical fix. The old code only added start_time[:10]
    which missed every day after the first in multi-day blocks.
    """
    busy = set()

    start_field = event.get("start", {})
    end_field = event.get("end", {})

    if "dateTime" in start_field:
        # Timed event — single day
        dt_str = start_field["dateTime"]
        # Slice to just the date portion (handles both Z and offset formats)
        day = dt_str[:10]
        busy.add(day)

    elif "date" in start_field:
        # All-day or multi-day event — expand the full range
        try:
            start_date = date.fromisoformat(start_field["date"])
            # end date is exclusive in Google Calendar API
            end_date = date.fromisoformat(end_field["date"])
            current = start_date
            while current < end_date:
                busy.add(current.isoformat())
                current += timedelta(days=1)
        except (ValueError, KeyError):
            # Malformed event — skip it
            pass

    return busy


def get_available_dates(session_type: str) -> list[str]:
    """
    Query Miguel's Google Calendar and return up to 5 available dates
    within the booking window (14–60 days from today).

    Returns formatted date strings like "Saturday May 10".
    Falls back to static placeholder dates if the calendar call fails.

    session_type is accepted for future use (e.g. Full Day blocks
    the entire day vs Small which might allow multiple bookings).
    Currently all session types use the same availability logic.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        window_start = now + timedelta(days=14)
        window_end = now + timedelta(days=60)

        # Fetch all events in the booking window
        # singleEvents=True expands recurring events into individual instances
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=window_start.isoformat() + "Z",
            timeMax=window_end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        # ── Build busy set — expand ALL event ranges ────────────
        busy_dates: set = set()
        for event in events_result.get("items", []):
            busy_dates |= _expand_event_dates(event)

        print(f">>> Calendar: {len(busy_dates)} busy dates found")
        if busy_dates:
            sorted_busy = sorted(busy_dates)
            print(f">>> Busy dates sample: {sorted_busy[:10]}")

        # ── Find available dates in the booking window ──────────
        available = []
        current = window_start

        while current <= window_end and len(available) < 5:
            date_str = current.strftime("%Y-%m-%d")
            day_name = current.strftime("%A")

            is_working_day = day_name in WORKING_DAYS
            is_free = date_str not in busy_dates

            if is_working_day and is_free:
                # Format: "Saturday May 10"
                formatted = current.strftime("%A %B %-d")
                available.append(formatted)
                print(f">>> Available: {formatted}")

            current += timedelta(days=1)

        if not available:
            print(">>> No available dates found in window — using fallback")
            return _fallback_dates(window_start)

        print(f">>> Returning {len(available)} available dates: {available}")
        return available

    except Exception as e:
        print(f">>> Calendar error: {e}")
        return _fallback_dates(datetime.utcnow() + timedelta(days=14))


def _fallback_dates(from_date: datetime) -> list[str]:
    """
    Generate 3 fallback dates when the calendar call fails.
    Uses real upcoming Saturdays/Thursdays so they at least
    look plausible. Miguel will manually adjust if needed.
    """
    fallbacks = []
    current = from_date
    while len(fallbacks) < 3:
        if current.strftime("%A") in {"Saturday", "Thursday"}:
            fallbacks.append(current.strftime("%A %B %-d"))
        current += timedelta(days=1)
    print(f">>> Fallback dates: {fallbacks}")
    return fallbacks