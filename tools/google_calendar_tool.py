# tools/google_calendar_tool.py
# Inkbook — Google Calendar Tool
# Reads Miguel's real calendar to find available dates
# Last updated: May 3, 2026
#
# FIX 1: Multi-day TIMED events (Valley appointments, Out of shop, etc.)
# now correctly mark ALL days in the range as busy, not just the start.
# Miguel creates his blocks as timed events (e.g. May 18 2pm → May 22 3pm),
# not all-day events. The old code treated all timed events as single-day.
#
# FIX 2: All-day events still handled correctly — end date is exclusive
# in Google Calendar API so we loop start <= current < end.
#
# FIX 3: Calendar ID is migueltattooappts@gmail.com — confirmed correct
# from the "Integrate calendar" section in Google Calendar settings.

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

    Google Calendar has two event types:

    1. TIMED events — use "dateTime" field
       e.g. "2026-05-18T14:00:00-05:00" to "2026-05-22T15:00:00-05:00"
       Miguel uses these for multi-day blocks like "Valley appointments".
       End date is INCLUSIVE — loop while current <= end_date.

    2. ALL-DAY events — use "date" field
       e.g. start="2026-05-18", end="2026-05-23"
       End date is EXCLUSIVE in Google's API — loop while current < end_date.

    The original bug: timed events were treated as single-day by only
    slicing start[:10]. Valley appointments May 18 to May 22 only marked
    May 18 as busy. This fix expands the full range for both event types.
    """
    busy = set()

    start_field = event.get("start", {})
    end_field = event.get("end", {})

    if "dateTime" in start_field:
        # Timed event — extract date from both start and end dateTime,
        # then expand the full inclusive range day by day
        try:
            start_date = date.fromisoformat(start_field["dateTime"][:10])
            end_date = date.fromisoformat(end_field["dateTime"][:10])
            current = start_date
            while current <= end_date:  # inclusive
                busy.add(current.isoformat())
                current += timedelta(days=1)
        except (ValueError, KeyError):
            pass

    elif "date" in start_field:
        # All-day event — end date is exclusive per Google Calendar API
        try:
            start_date = date.fromisoformat(start_field["date"])
            end_date = date.fromisoformat(end_field["date"])
            current = start_date
            while current < end_date:  # exclusive
                busy.add(current.isoformat())
                current += timedelta(days=1)
        except (ValueError, KeyError):
            pass

    return busy


def get_available_dates(session_type: str) -> list[str]:
    """
    Query Miguel's Google Calendar and return up to 5 available dates
    within the booking window (14 to 60 days from today).

    Returns formatted strings like "Saturday May 10".
    Falls back to real upcoming Saturdays/Thursdays if the API call fails.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        window_start = now + timedelta(days=14)
        window_end = now + timedelta(days=60)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=window_start.isoformat() + "Z",
            timeMax=window_end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        # Build busy set — expand ALL event ranges
        busy_dates: set = set()
        for event in events_result.get("items", []):
            busy_dates |= _expand_event_dates(event)

        print(f">>> Calendar: {len(busy_dates)} busy dates found")
        if busy_dates:
            sorted_busy = sorted(busy_dates)
            print(f">>> Busy dates sample: {sorted_busy[:10]}")

        # Find available dates in the booking window
        available = []
        current = window_start

        while current <= window_end and len(available) < 5:
            date_str = current.strftime("%Y-%m-%d")
            day_name = current.strftime("%A")

            is_working_day = day_name in WORKING_DAYS
            is_free = date_str not in busy_dates

            if is_working_day and is_free:
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
    Generate 3 fallback dates when the calendar API call fails.
    Uses real upcoming Saturdays/Thursdays.
    """
    fallbacks = []
    current = from_date
    while len(fallbacks) < 3:
        if current.strftime("%A") in {"Saturday", "Thursday"}:
            fallbacks.append(current.strftime("%A %B %-d"))
        current += timedelta(days=1)
    print(f">>> Fallback dates: {fallbacks}")
    return fallbacks