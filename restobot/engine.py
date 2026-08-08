from __future__ import annotations

from typing import Callable

from restobot.availability import Booking, BookingError
from restobot.config import Location, Restaurant, Table

FORWARD_MSG = "Forwarding to the manager"
CANT_HELP_MSG = "Can't help with that here, sorry."
EXTEND_MINUTES = 30

MAX_HISTORY = 8

UnderstandFn = Callable[[list[str], str, dict], dict]


def describe_open_tables(tables: list[Table]) -> str:
    by_area: dict[str, list[Table]] = {}
    for t in tables:
        by_area.setdefault(t.area, []).append(t)
    parts = [f"{area}: {', '.join(t.id for t in ts)}" for area, ts in by_area.items()]
    return " | ".join(parts)


class Engine:
    def __init__(self, restaurant: Restaurant, location: Location, understand_fn: UnderstandFn):
        self.restaurant = restaurant
        self.location = location
        self.understand = understand_fn
        self.booking = Booking(restaurant)
        self.history: list[str] = []
        self.slots: dict = {}
        self.candidates: list[Table] = []

    def _remember(self, speaker: str, text: str) -> None:
        self.history.append(f"{speaker}: {text}")
        self.history = self.history[-MAX_HISTORY:]

    def _is_manager_topic(self, text: str) -> bool:
        lowered = text.lower()
        return any(trigger.lower() in lowered for trigger in self.restaurant.manager_triggers)

    def _match_table_id(self, text: str) -> Table | None:
        upper = text.upper()
        for t in self.candidates:
            if t.id.upper() in upper:
                return t
        return None

    def handle_message(self, text: str) -> str:
        self._remember("guest", text)

        if self._is_manager_topic(text):
            self._remember("assistant", FORWARD_MSG)
            return FORWARD_MSG

        if self.candidates and "table_id" not in self.slots:
            matched = self._match_table_id(text)
            if matched:
                self.slots["table_id"] = matched.id
                reply = self._continue_booking()
                self._remember("assistant", reply)
                return reply

        result = self.understand(self.history[:-1], text, self.slots)
        intent = result.get("intent")
        extracted = result.get("slots") or {}

        if intent == "manager":
            reply = FORWARD_MSG
        elif intent == "irrelevant":
            reply = CANT_HELP_MSG
        elif intent == "question":
            reply = result.get("reply", CANT_HELP_MSG)
        elif intent == "extend":
            reply = self._handle_extend(extracted, result.get("reply", ""))
        elif intent == "booking":
            self.slots.update({k: v for k, v in extracted.items() if v})
            reply = self._continue_booking(fallback_reply=result.get("reply", ""))
        else:
            reply = result.get("reply", CANT_HELP_MSG)

        self._remember("assistant", reply)
        return reply

    def _continue_booking(self, fallback_reply: str = "") -> str:
        missing = [k for k in ("party_size", "date", "time") if k not in self.slots]
        if missing:
            return fallback_reply or "What else do you need to tell me, party size, date or time?"

        if "table_id" not in self.slots:
            if not self.candidates:
                self.candidates = self.booking.find_open_tables(
                    self.location.name, self.slots["date"], self.slots["time"],
                    self.slots["party_size"], area=self.slots.get("area"),
                )
                if not self.candidates:
                    area = self.slots.pop("area", None)
                    if area:
                        return f"No {area} tables free then, want to try a different area?"
                    self.slots.pop("time", None)
                    return "Nothing free at that time, want to try a different time?"

            if len(self.candidates) == 1:
                self.slots["table_id"] = self.candidates[0].id
            else:
                area = self.slots.get("area")
                if area:
                    matches = [t for t in self.candidates if t.area == area]
                    if len(matches) == 1:
                        self.slots["table_id"] = matches[0].id
                if "table_id" not in self.slots:
                    return f"Open right now: {describe_open_tables(self.candidates)}. Which one?"

        if "name" not in self.slots:
            return "What name should I put it under?"

        return self._finish_booking()

    def _finish_booking(self) -> str:
        try:
            reservation = self.booking.book(
                self.location.name, self.slots["table_id"], self.slots["date"],
                self.slots["time"], self.slots["party_size"], self.slots["name"],
            )
        except BookingError as e:
            self.slots.pop("table_id", None)
            self.candidates = []
            return f"Couldn't book that, {e}."

        area = next(t.area for t in self.location.all_tables() if t.id == reservation.table_id)
        summary = (
            f"Booked. {self.restaurant.name}, {self.location.address}. "
            f"Table {reservation.table_id} ({area}), {reservation.date} at {reservation.time}, "
            f"party of {reservation.party_size}, under {reservation.name}."
        )
        self.slots = {}
        self.candidates = []
        return summary

    def _handle_extend(self, extracted: dict, fallback_reply: str) -> str:
        self.slots.update({k: v for k, v in extracted.items() if v})
        name = self.slots.get("name")
        date = self.slots.get("date")
        if not name or not date:
            return fallback_reply or "Who's the reservation under, and for what date?"

        try:
            updated = self.booking.extend(name, date, EXTEND_MINUTES)
        except BookingError as e:
            return f"Couldn't extend that, {e}."

        return f"Extended, {updated.name}'s table now runs {updated.duration_minutes} minutes."
