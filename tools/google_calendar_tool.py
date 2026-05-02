import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = "migueltattooappts@gmail.com"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/google_credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_available_dates(session_type: str) -> list[str]:
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        start = now + timedelta(days=14)
        end = now + timedelta(days=60)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        busy_dates = set()
        for event in events_result.get("items", []):
            start_time = event["start"].get("dateTime", event["start"].get("date", ""))
            if start_time:
                busy_dates.add(start_time[:10])

        available = []
        current = start
        while current <= end and len(available) < 5:
            date_str = current.strftime("%Y-%m-%d")
            day_name = current.strftime("%A")
            if date_str not in busy_dates and day_name in ["Saturday", "Thursday", "Tuesday"]:
                available.append(current.strftime("%A %B %-d"))
            current += timedelta(days=1)

        return available if available else ["Saturday May 10", "Thursday May 15", "Saturday May 24"]

    except Exception as e:
        print(f"Calendar error: {e}")
        return ["Saturday May 10", "Thursday May 15", "Saturday May 24"]
