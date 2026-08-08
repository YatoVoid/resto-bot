from __future__ import annotations

from restobot.config import Location, Restaurant
from restobot.engine import UnderstandFn
from restobot.nlu_stub import extract_slots

BOOKING_WORDS = ("book", "table", "reserve", "reservation", "party")
EXTEND_WORDS = ("extend", "longer", "more time", "push back")
HOURS_WORDS = ("hour", "open", "close", "when do you")
ADDRESS_WORDS = ("address", "where are you", "located")
CUISINE_WORDS = ("cuisine", "what food", "kind of food", "menu")


def build_offline_understander(restaurant: Restaurant, location: Location) -> UnderstandFn:
    def understand(history: list[str], text: str, known_slots: dict) -> dict:
        slots = extract_slots(text)
        lowered = text.lower()
        merged = {**known_slots, **slots}

        if any(w in lowered for w in EXTEND_WORDS):
            if "name" not in merged:
                reply = "Who's the reservation under?"
            elif "date" not in merged:
                reply = "What date was it for?"
            else:
                reply = ""
            return {"intent": "extend", "reply": reply, "slots": slots}

        if any(w in lowered for w in HOURS_WORDS):
            return {"intent": "question", "reply": f"We're open {location.hours}.", "slots": slots}

        if any(w in lowered for w in ADDRESS_WORDS):
            return {"intent": "question", "reply": f"We're at {location.address}.", "slots": slots}

        if any(w in lowered for w in CUISINE_WORDS):
            return {"intent": "question", "reply": f"We serve {restaurant.cuisine} food.", "slots": slots}

        if slots or any(w in lowered for w in BOOKING_WORDS):
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
