from __future__ import annotations

import re
from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

AREA_SYNONYMS = {
    "window": "window",
    "private": "private",
    "cabinet": "private",
    "cabin": "private",
    "patio": "patio",
    "terrace": "patio",
    "outside": "patio",
    "outdoor": "patio",
    "regular": "regular",
    "normal": "regular",
}

NAME_PATTERNS = [
    re.compile(r"\bmy name is ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)", re.IGNORECASE),
    re.compile(r"\bunder the name ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)", re.IGNORECASE),
    re.compile(r"\bit'?s ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)$", re.IGNORECASE),
    re.compile(r"\bthis is ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)$", re.IGNORECASE),
]

NAME_STOPWORDS = {
    "today", "tomorrow", "and", "at", "on", "for", "please", "thanks",
    *WEEKDAYS,
}

PARTY_PATTERNS = [
    re.compile(r"table for (\d+)", re.IGNORECASE),
    re.compile(r"party of (\d+)", re.IGNORECASE),
    re.compile(r"(\d+)\s*(?:people|persons|of us|guests)", re.IGNORECASE),
    re.compile(r"for (\d+)\b", re.IGNORECASE),
]

TIME_12H = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)\b", re.IGNORECASE)
TIME_24H = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_NUMERIC = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b")


def _next_weekday(ref: date, weekday_index: int) -> date:
    days_ahead = (weekday_index - ref.weekday()) % 7
    days_ahead = days_ahead or 7
    return ref + timedelta(days=days_ahead)


def _extract_date(text: str, ref: date) -> str | None:
    lowered = text.lower()

    m = DATE_ISO.search(text)
    if m:
        return m.group(0)

    if "today" in lowered:
        return ref.isoformat()
    if "tomorrow" in lowered:
        return (ref + timedelta(days=1)).isoformat()

    for i, day_name in enumerate(WEEKDAYS):
        if day_name in lowered:
            return _next_weekday(ref, i).isoformat()

    m = DATE_NUMERIC.search(text)
    if m:
        day, month, year = m.groups()
        year = int(year) if year else ref.year
        try:
            return date(year, int(month), int(day)).isoformat()
        except ValueError:
            return None

    return None


def _extract_time(text: str) -> str | None:
    m = TIME_12H.search(text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = m.group(3).lower().replace(".", "")
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    m = TIME_24H.search(text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    return None


def _extract_party_size(text: str) -> int | None:
    for pattern in PARTY_PATTERNS:
        m = pattern.search(text)
        if m:
            return int(m.group(1))
    return None


def _extract_area(text: str) -> str | None:
    lowered = text.lower()
    for word, area in AREA_SYNONYMS.items():
        if word in lowered:
            return area
    return None


def _extract_name(text: str) -> str | None:
    for pattern in NAME_PATTERNS:
        m = pattern.search(text.strip())
        if not m:
            continue
        words = m.group(1).split()
        kept = []
        for w in words:
            if w.lower() in NAME_STOPWORDS:
                break
            kept.append(w)
        if kept:
            return " ".join(kept).title()
    return None


def extract_slots(text: str, reference_date: date | None = None) -> dict:
    ref = reference_date or date.today()
    slots = {}

    d = _extract_date(text, ref)
    if d:
        slots["date"] = d

    t = _extract_time(text)
    if t:
        slots["time"] = t

    party = _extract_party_size(text)
    if party:
        slots["party_size"] = party

    area = _extract_area(text)
    if area:
        slots["area"] = area

    name = _extract_name(text)
    if name:
        slots["name"] = name

    return slots
