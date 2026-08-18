from __future__ import annotations

import re
import time
from typing import Callable

from restobot.availability import Booking, BookingError
from restobot.config import Location, Restaurant, Table
from restobot.nlu_stub import extract_party_size

FORWARD_MSG = "Forwarding to the manager"
CANT_HELP_MSG = "Can't help with that here, sorry."
TROUBLE_MSG = "Having trouble understanding that, can you try again?"
EXTEND_MINUTES = 30
SESSION_TIMEOUT_SECONDS = 5 * 60
MAX_LLM_CALLS_PER_SESSION = 40
LIMIT_REACHED_MSG = "This is taking a while, let me get a person to help you directly."

# whole-word triggers, matched with a boundary on both sides
MANAGER_FALLBACK_EXACT = (
    "can't make it", "cant make it", "parking", "wifi", "wi-fi",
    "dress code", "wheelchair", "accessible", "discount", "private event",
    "high chair", "kids menu", "child menu", "gluten", "vegan", "vegetarian",
    "pet", "dog", "allergic", "allergy",
)

# word stems, matched with a boundary only on the left so complaining,
# complaint, reschedule, rescheduling, cancellation all still hit
MANAGER_FALLBACK_PREFIXES = ("complain", "reschedul", "cancel")

# topics a restaurant can opt out of forwarding by filling in the matching
# amenities key in its config, everything else in MANAGER_FALLBACK_EXACT
# always forwards regardless of config (dietary safety, refunds, etc.)
AMENITY_TOPICS = {
    "parking": "parking",
    "wifi": "wifi",
    "wi-fi": "wifi",
    "dress code": "dress_code",
    "wheelchair": "accessible",
    "accessible": "accessible",
    "high chair": "high_chair",
    "kids menu": "kids_menu",
    "child menu": "kids_menu",
    "pet": "pets",
    "dog": "pets",
}

PARTY_THRESHOLD_RE = re.compile(r"party of (\d+) or more", re.IGNORECASE)

AFFIRMATIVE = (
    "yes", "yes please", "yep", "yeah", "yup", "confirm", "confirmed", "correct",
    "sounds good", "go ahead", "book it", "that's right", "thats right",
    "perfect", "looks good", "all good", "good to go",
)
NEGATIVE = ("no", "nope", "cancel", "don't book it", "dont book it", "stop", "not yet")

MAX_HISTORY = 8

UnderstandFn = Callable[[list[str], str, dict], dict]

AVAILABILITY_SLOTS = {"party_size", "date", "time", "area"}


def _is_affirmative(text: str) -> bool:
    t = text.strip().lower().rstrip(".!")
    return t in AFFIRMATIVE or t.startswith("yes")


def _is_negative(text: str) -> bool:
    t = text.strip().lower().rstrip(".!")
    return t in NEGATIVE


class Engine:
    def __init__(self, restaurant: Restaurant, location: Location | None, understand_fn: UnderstandFn,
                 now_fn: Callable[[], float] = time.monotonic):
        self.restaurant = restaurant
        self.location = location
        self.understand = understand_fn
        self.booking = Booking(restaurant)
        self._now = now_fn
        self.last_activity: float | None = None
        self.history: list[str] = []
        self.slots: dict = {}
        self.extend_slots: dict = {}
        self.candidates: list[Table] = []
        self.awaiting_confirmation = False
        self.llm_calls = 0

    def _remember(self, speaker: str, text: str) -> None:
        self.history.append(f"{speaker}: {text}")
        self.history = self.history[-MAX_HISTORY:]

    def _reset_session(self) -> None:
        self.history = []
        self.slots = {}
        self.extend_slots = {}
        self.candidates = []
        self.awaiting_confirmation = False
        self.llm_calls = 0
        if not self.restaurant.single_location():
            self.location = None

    def _is_manager_topic(self, text: str) -> bool:
        lowered = text.lower()
        triggers = [t.lower() for t in self.restaurant.manager_triggers]
        if any(trigger in lowered for trigger in triggers):
            return True
        for topic in MANAGER_FALLBACK_EXACT:
            if not re.search(rf"\b{topic}\b", lowered):
                continue
            amenity_key = AMENITY_TOPICS.get(topic)
            if amenity_key and self.location and self.location.amenities.get(amenity_key):
                continue
            return True
        if any(re.search(rf"\b{prefix}", lowered) for prefix in MANAGER_FALLBACK_PREFIXES):
            return True

        for trigger in triggers:
            m = PARTY_THRESHOLD_RE.search(trigger)
            if not m:
                continue
            party = extract_party_size(text)
            if party is not None and party >= int(m.group(1)):
                return True

        return False

    def handle_message(self, text: str) -> str:
        now = self._now()
        if self.last_activity is not None and now - self.last_activity > SESSION_TIMEOUT_SECONDS:
            self._reset_session()
        self.last_activity = now

        self._remember("guest", text)

        if self._is_manager_topic(text):
            self._remember("assistant", FORWARD_MSG)
            return FORWARD_MSG

        if self.awaiting_confirmation:
            if _is_affirmative(text):
                reply = self._finish_booking()
                self._remember("assistant", reply)
                return reply
            if _is_negative(text):
                self.awaiting_confirmation = False
                self.slots = {}
                self.candidates = []
                reply = "No worries, cancelled that. Anything else I can help with?"
                self._remember("assistant", reply)
                return reply
            self.awaiting_confirmation = False

        if self.llm_calls >= MAX_LLM_CALLS_PER_SESSION:
            self._remember("assistant", LIMIT_REACHED_MSG)
            return LIMIT_REACHED_MSG
        self.llm_calls += 1

        try:
            known_slots = dict(self.slots)
            if self.location:
                known_slots["location"] = self.location.name
            result = self.understand(self.history[:-1], text, known_slots)
        except Exception:
            self._remember("assistant", TROUBLE_MSG)
            return TROUBLE_MSG

        intent = result.get("intent")
        extracted = dict(result.get("slots") or {})
        loc_name = extracted.pop("location", None)

        if self.location is None:
            if loc_name:
                try:
                    self.location = self.restaurant.get_location(loc_name)
                except KeyError:
                    pass
            if intent in ("booking", "extend"):
                self.slots.update({k: v for k, v in extracted.items() if v})
            if self.location is None:
                reply = result.get("reply") or self._ask_location_reply()
                self._remember("assistant", reply)
                return reply

        if intent == "manager":
            reply = FORWARD_MSG
        elif intent == "irrelevant":
            reply = CANT_HELP_MSG
        elif intent == "question":
            reply = result.get("reply", CANT_HELP_MSG)
        elif intent == "extend":
            reply = self._handle_extend(extracted, result.get("reply", ""))
        elif intent == "booking":
            if AVAILABILITY_SLOTS & extracted.keys():
                self.slots.pop("table_id", None)
                self.candidates = []
            self.slots.update({k: v for k, v in extracted.items() if v})
            reply = self._continue_booking(fallback_reply=result.get("reply", ""))
        else:
            reply = result.get("reply", CANT_HELP_MSG)

        self._remember("assistant", reply)
        return reply

    def _ask_location_reply(self) -> str:
        names = ", ".join(loc.name for loc in self.restaurant.locations)
        return f"Which location did you mean, {names}?"

    def _narrow_candidates(self) -> list[Table]:
        candidates = self.candidates
        area = self.slots.get("area")
        if area:
            candidates = [t for t in candidates if t.area == area]

        floor_hint = self.slots.get("floor_hint")
        if floor_hint:
            floor = self.location.find_floor(floor_hint)
            if floor:
                candidates = [t for t in candidates if t in floor.tables]

        return candidates

    def _continue_booking(self, fallback_reply: str = "") -> str:
        missing = [k for k in ("party_size", "date", "time") if k not in self.slots]
        if missing:
            return fallback_reply or "What else do you need to tell me, party size, date or time?"

        if "table_id" not in self.slots:
            if not self.candidates:
                self.candidates = self.booking.find_open_tables(
                    self.location.name, self.slots["date"], self.slots["time"],
                    self.slots["party_size"],
                )
                if not self.candidates:
                    self.slots.pop("time", None)
                    return "Nothing free at that time, want to try a different time?"

            narrowed = self._narrow_candidates() or self.candidates
            chosen = narrowed[0]
            self.slots["table_id"] = chosen.id
            self.slots["area"] = chosen.area

        if "name" not in self.slots:
            return "What name should I put it under?"

        self.awaiting_confirmation = True
        return self._confirmation_summary()

    def _confirmation_summary(self) -> str:
        return (
            f"Just to confirm: table for {self.slots['party_size']} at {self.location.name}, "
            f"{self.slots['date']} at {self.slots['time']}, {self.slots['area']} seating, "
            f"under {self.slots['name']}. Shall I book it, or is there anything to change?"
        )

    def _finish_booking(self) -> str:
        self.awaiting_confirmation = False
        area = self.slots.get("area", "")
        try:
            reservation = self.booking.book(
                self.location.name, self.slots["table_id"], self.slots["date"],
                self.slots["time"], self.slots["party_size"], self.slots["name"],
            )
        except BookingError as e:
            self.slots.pop("table_id", None)
            self.candidates = []
            return f"Couldn't book that, {e}."

        summary = (
            f"Booked. {self.restaurant.name}, {self.location.address}. "
            f"{reservation.date} at {reservation.time}, {area} seating, "
            f"party of {reservation.party_size}, under {reservation.name}."
        )
        self.slots = {}
        self.candidates = []
        return summary

    def _handle_extend(self, extracted: dict, fallback_reply: str) -> str:
        self.extend_slots.update({k: v for k, v in extracted.items() if v})
        name = self.extend_slots.get("name")
        date = self.extend_slots.get("date")
        if not name or not date:
            return fallback_reply or (
                "Who's the reservation under, and for what date? Need your name to confirm it's you."
            )

        try:
            updated = self.booking.extend(name, date, EXTEND_MINUTES)
        except BookingError as e:
            return f"Couldn't extend that, {e}."

        self.extend_slots = {}
        return f"Extended, {updated.name}'s table now runs {updated.duration_minutes} minutes."
