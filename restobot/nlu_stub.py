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

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "couple": "2",
}
NUMBER_WORDS_RE = re.compile(r"\b(" + "|".join(NUMBER_WORDS.keys()) + r")\b", re.IGNORECASE)

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

NEGATION_RE = re.compile(r"\b(?:not|no|n't want|anything but|except|besides)\b", re.IGNORECASE)

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
    re.compile(r"we are (\d+)", re.IGNORECASE),
    re.compile(r"(\d+)\s*(?:people|persons|of us|guests|ppl)", re.IGNORECASE),
    re.compile(r"for (\d+)\b", re.IGNORECASE),
]

TIME_12H = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)\b", re.IGNORECASE)
TIME_24H = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

HALF_PAST_RE = re.compile(r"\bhalf past (\d{1,2})\b", re.IGNORECASE)
QUARTER_PAST_RE = re.compile(r"\bquarter past (\d{1,2})\b", re.IGNORECASE)
QUARTER_TO_RE = re.compile(r"\bquarter to (\d{1,2})\b", re.IGNORECASE)
OCLOCK_RE = re.compile(r"\b(\d{1,2})\s*o'?clock\b", re.IGNORECASE)
ISH_RE = re.compile(r"\b(\d{1,2})\s*ish\b", re.IGNORECASE)
AROUND_RE = re.compile(r"\baround\s+(\d{1,2})\b(?!\s*(?::|am|pm))", re.IGNORECASE)

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
DATE_DAY_ONLY = re.compile(r"\bthe (\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)
IN_DAYS_RE = re.compile(r"\bin (\d{1,2}) days?\b", re.IGNORECASE)
IN_WEEK_RE = re.compile(r"\bin (?:a|one) week\b", re.IGNORECASE)
IN_WEEKS_RE = re.compile(r"\bin (\d{1,2}) weeks?\b", re.IGNORECASE)

TOMORROW_WORDS = ("tomorrow", "tmrw", "tmr", "2moro", "2mrw")
TODAY_WORDS = ("today", "2day", "tonight")


def _words_to_digits(text: str) -> str:
    return NUMBER_WORDS_RE.sub(lambda m: NUMBER_WORDS[m.group(0).lower()], text)


def _pm_hour(hour: int) -> int:
    if 1 <= hour <= 11:
        return hour + 12
    return hour


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

    m = IN_DAYS_RE.search(lowered)
    if m:
        return (ref + timedelta(days=int(m.group(1)))).isoformat()
    if IN_WEEK_RE.search(lowered):
        return (ref + timedelta(days=7)).isoformat()
    m = IN_WEEKS_RE.search(lowered)
    if m:
        return (ref + timedelta(weeks=int(m.group(1)))).isoformat()

    if any(re.search(rf"\b{w}\b", lowered) for w in TODAY_WORDS):
        return ref.isoformat()
    if any(re.search(rf"\b{w}\b", lowered) for w in TOMORROW_WORDS):
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

    m = DATE_DAY_ONLY.search(lowered)
    if m:
        day = int(m.group(1))
        year, month = ref.year, ref.month
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate < ref:
            month += 1
            if month > 12:
                month = 1
                year += 1
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None
        return candidate.isoformat()

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

    converted = _words_to_digits(text)

    m = HALF_PAST_RE.search(converted)
    if m:
        return f"{_pm_hour(int(m.group(1))):02d}:30"

    m = QUARTER_PAST_RE.search(converted)
    if m:
        return f"{_pm_hour(int(m.group(1))):02d}:15"

    m = QUARTER_TO_RE.search(converted)
    if m:
        base = _pm_hour(int(m.group(1)))
        hour = base - 1 if base > 0 else 23
        return f"{hour:02d}:45"

    m = OCLOCK_RE.search(converted)
    if m:
        return f"{_pm_hour(int(m.group(1))):02d}:00"

    m = ISH_RE.search(converted)
    if m:
        return f"{_pm_hour(int(m.group(1))):02d}:00"

    m = AROUND_RE.search(converted)
    if m:
        return f"{_pm_hour(int(m.group(1))):02d}:00"

    lowered = text.lower()
    for word, hhmm in TIME_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            return hhmm

    return None


def _extract_party_size(text: str) -> int | None:
    converted = _words_to_digits(text)
    for pattern in PARTY_PATTERNS:
        m = pattern.search(converted)
        if m:
            return int(m.group(1))
    return None


def extract_party_size(text: str) -> int | None:
    return _extract_party_size(text)


def _extract_area(text: str) -> str | None:
    lowered = text.lower()
    for word, area in AREA_SYNONYMS.items():
        m = re.search(rf"\b{word}\b", lowered)
        if not m:
            continue
        before = lowered[max(0, m.start() - 20):m.start()]
        if NEGATION_RE.search(before):
            continue
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
