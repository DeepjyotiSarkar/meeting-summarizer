"""
Unique feature: one click turns action items into real calendar reminders
(.ics file, imports into Google Calendar / Outlook / Apple Calendar) so
action items don't just sit as text nobody revisits.
"""
import uuid
from datetime import datetime, date
from typing import List

from models import ActionItem


def _to_ics_date(d: str) -> str:
    """Best-effort parse of a deadline string into YYYYMMDD; falls back to today."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y%m%d")
        except (ValueError, TypeError):
            continue
    return date.today().strftime("%Y%m%d")


def build_ics(meeting_title: str, action_items: List[ActionItem]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MeetingSummarizer//EN"]

    for item in action_items:
        if not item.deadline:
            continue
        dt = _to_ics_date(item.deadline)
        summary = f"[{meeting_title}] {item.description}"
        if item.owner:
            summary = f"{summary} (Owner: {item.owner})"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@meeting-summarizer",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{dt}",
            f"DTEND;VALUE=DATE:{dt}",
            f"SUMMARY:{summary}",
            f"PRIORITY:{ {'high': 1, 'medium': 5, 'low': 9}.get(item.priority, 5) }",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
