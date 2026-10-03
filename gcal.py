"""Google Calendar: read the day, flag clashes, add events with reminders."""
from datetime import datetime
from . import gcreds


def _svc(email):
    from googleapiclient.discovery import build
    return build("calendar", "v3", credentials=gcreds.credentials(email, "calendar"), cache_discovery=False).events()


def _iso(x):
    d = datetime.fromisoformat(str(x))
    return d.astimezone() if d.tzinfo is None else d  # naive = your local time zone


def list_events(email, start, end):
    r = _svc(email).list(calendarId="primary", timeMin=_iso(start).isoformat(), timeMax=_iso(end).isoformat(),
                         singleEvents=True, orderBy="startTime", maxResults=100).execute()
    out = []
    for e in r.get("items", []):
        s, en = e["start"].get("dateTime") or e["start"].get("date"), e["end"].get("dateTime") or e["end"].get("date")
        out.append({"id": e.get("id"), "title": e.get("summary", "(no title)"), "start": s, "end": en,
                    "all_day": "date" in e["start"], "location": e.get("location", "")})
    return out


def clashes(events):
    """Pairs of timed events that overlap."""
    t = sorted((e for e in events if not e.get("all_day") and "T" in str(e["start"])), key=lambda e: _iso(e["start"]))
    out = []
    for i, a in enumerate(t):
        for b in t[i + 1:]:
            if _iso(b["start"]) >= _iso(a["end"]):
                break
            out.append((a, b))
    return out


def create(email, title, start, end, description="", reminder_minutes=10):
    body = {"summary": title[:200], "description": description[:2000],
            "start": {"dateTime": _iso(start).isoformat()}, "end": {"dateTime": _iso(end).isoformat()},
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": int(reminder_minutes)}]}}
    return _svc(email).insert(calendarId="primary", body=body).execute().get("htmlLink", "")
