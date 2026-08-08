from __future__ import annotations

import re
from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

AREA_SYNONYMS = {
    "window": "window",
    "private": "private",
    "cabinet": "private",
    "cabin": "private",
    "couch": "private",
    "sofa": "private",
    "lounge": "private",
    "patio": "patio",
    "terrace": "patio",
    "outside": "patio",
    "outdoor": "patio",
    "regular": "regular",
    "normal": "regular",
    "center": "regular",
    "centre": "regular",
    "middle": "regular",
    "corner": "regular",
}

FLOOR_ORDINALS = {
    "first": "1", "1st": "1",
    "second": "2", "2nd": "2",
    "third": "3", "3rd": "3",
    "fourth": "4", "4th": "4",
}

FLOOR_KEYWORDS = (
    "ground", "downstairs", "bottom",
    "upper", "upstairs", "top", "roof", "rooftop",
    "main", "terrace",
)

FLOOR_ORDINAL_RE = re.compile(
    r"\b(first|1st|second|2nd|third|3rd|fourth|4th)\s+floor\b", re.IGNORECASE
)

NAME_PATTERNS = [
    re.compile(r"\bmy name is ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)", re.IGNORECASE),
    re.compile(r"\bname'?s ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)", re.IGNORECASE),
    re.compile(r"\bname is ([a-z][a-z'-]*(?:\s[a-z][a-z'-]*)?)", re.IGNORECASE),
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

TIME_WORDS = {
    "noon": "12:00",
    "midnight": "00:00",
    "morning": "10:00",
    "afternoon": "14:00",
    "evening": "19:00",
    "tonight": "19:00",
    "night": "20:00",
}

DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_NUMERIC = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b")
DATE_MONTH_DAY = re.compile(
    r"\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|"
    r"aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE
)
DATE_DAY_MONTH = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?"
    r"(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|"
    r"aug|august|sep|sept|september|oct|october|nov|november|dec|december)\b", re.IGNORECASE
)


def _next_weekday(ref: date, weekday_index: int) -> date:
    days_ahead = (weekday_index - ref.weekday()) % 7
    days_ahead = days_ahead or 7
    return ref + timedelta(days=days_ahead)


def _extract_date(text: str, ref: date) -> str | None:
    lowered = text.lower()

    m = DATE_ISO.search(text)
    if m:
        return m.group(0)

    if "day after tomorrow" in lowered or "after tomorrow" in lowered:
        return (ref + timedelta(days=2)).isoformat()
    if "today" in lowered or "tonight" in lowered:
        return ref.isoformat()
    if "tomorrow" in lowered:
        return (ref + timedelta(days=1)).isoformat()

    for i, day_name in enumerate(WEEKDAYS):
        if day_name in lowered:
            return _next_weekday(ref, i).isoformat()

    m = DATE_MONTH_DAY.search(lowered)
    if m:
        month = MONTHS.get(m.group(1))
        day = int(m.group(2))
        if month:
            year = ref.year
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None
            if candidate < ref:
                candidate = date(year + 1, month, day)
            return candidate.isoformat()

    m = DATE_DAY_MONTH.search(lowered)
    if m:
        day = int(m.group(1))
        month = MONTHS.get(m.group(2))
        if month:
            year = ref.year
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None
            if candidate < ref:
                candidate = date(year + 1, month, day)
            return candidate.isoformat()

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

    lowered = text.lower()
    for word, hhmm in TIME_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            return hhmm

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
        if re.search(rf"\b{word}\b", lowered):
            return area
    return None


def _extract_floor(text: str) -> str | None:
    lowered = text.lower()
    m = FLOOR_ORDINAL_RE.search(lowered)
    if m:
        return FLOOR_ORDINALS[m.group(1)]
    for word in FLOOR_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            return word
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

    floor = _extract_floor(text)
    if floor:
        slots["floor_hint"] = floor

    name = _extract_name(text)
    if name:
        slots["name"] = name

    return slots
