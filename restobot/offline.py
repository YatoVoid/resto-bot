from __future__ import annotations

import re

from restobot.config import Location, Restaurant
from restobot.engine import UnderstandFn
from restobot.nlu_stub import extract_slots

BOOKING_WORDS = ("book", "table", "reserve", "reservation", "party")
EXTEND_WORDS = ("extend", "longer", "more time", "push back")
HOURS_WORDS = ("hour", "hours", "open", "close", "when do you")
ADDRESS_WORDS = ("address", "where are you", "located", "location")
CUISINE_WORDS = ("cuisine", "what food", "kind of food", "menu")
PRICE_WORDS = ("price", "cost", "how much", "minimum spend", "fee")

NAME_ONLY_RE = re.compile(r"^[a-zA-Z][a-zA-Z'-]*(?:\s[a-zA-Z][a-zA-Z'-]*){0,2}$")


def _matches(lowered: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words)


def _looks_like_bare_name(text: str) -> bool:
    return bool(NAME_ONLY_RE.match(text.strip()))


def build_offline_understander(restaurant: Restaurant, location: Location) -> UnderstandFn:
    def understand(history: list[str], text: str, known_slots: dict) -> dict:
        slots = extract_slots(text)
        lowered = text.lower()
        merged = {**known_slots, **slots}

        if not slots and "party_size" not in merged and text.strip().isdigit():
            slots = {"party_size": int(text.strip())}
            merged = {**known_slots, **slots}

        expecting_name_only = (
            "party_size" in merged and "date" in merged and "time" in merged
            and "table_id" in merged and "name" not in merged
        )
        if not slots and expecting_name_only and _looks_like_bare_name(text):
            slots = {"name": text.strip().title()}
            merged = {**known_slots, **slots}

        if _matches(lowered, EXTEND_WORDS):
            if "name" not in merged:
                reply = "Who's the reservation under?"
            elif "date" not in merged:
                reply = "What date was it for?"
            else:
                reply = ""
            return {"intent": "extend", "reply": reply, "slots": slots}

        if _matches(lowered, HOURS_WORDS):
            return {"intent": "question", "reply": f"We're open {location.hours}.", "slots": slots}

        if _matches(lowered, ADDRESS_WORDS):
            return {"intent": "question", "reply": f"We're at {location.address}.", "slots": slots}

        if _matches(lowered, CUISINE_WORDS):
            return {"intent": "question", "reply": f"We serve {restaurant.cuisine} food.", "slots": slots}

        if _matches(lowered, PRICE_WORDS):
            priced = [t for t in location.all_tables() if t.price_note]
            if slots.get("area"):
                priced = [t for t in priced if t.area == slots["area"]]
            if not priced:
                reply = "No special pricing, standard menu prices apply."
            else:
                seen_notes = dict.fromkeys((t.area, t.price_note) for t in priced)
                reply = " ".join(f"{area}: {note}." for area, note in seen_notes)
            return {"intent": "question", "reply": reply, "slots": slots}

        mid_booking = any(
            k in merged for k in ("party_size", "date", "time", "table_id", "name")
        )
        if slots or _matches(lowered, BOOKING_WORDS) or mid_booking:
            if "party_size" not in merged:
                reply = "How many people?"
            elif "date" not in merged:
                reply = "What date?"
            elif "time" not in merged:
                reply = "What time?"
            else:
                reply = ""
            return {"intent": "booking", "reply": reply, "slots": slots}

        return {"intent": "irrelevant", "reply": "", "slots": slots}

    return understand
