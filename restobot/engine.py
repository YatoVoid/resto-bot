from __future__ import annotations

import re
import time
from typing import Callable

from restobot.availability import Booking, BookingError
from restobot.config import Location, Restaurant, Table
from restobot.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t
from restobot.nlu_stub import extract_party_size

FORWARD_MSG = t("forward", "en")
CANT_HELP_MSG = t("cant_help", "en")
TROUBLE_MSG = t("trouble", "en")
LIMIT_REACHED_MSG = t("limit_reached", "en")
EXTEND_MINUTES = 30
SESSION_TIMEOUT_SECONDS = 5 * 60
MAX_LLM_CALLS_PER_SESSION = 40

# whole-word triggers, matched with a boundary on both sides. Mixes English,
# Russian, and Azerbaijani phrasing for the same topics so the deterministic
# safety net still catches sensitive topics regardless of what language the
# guest is writing in, not just whatever the LLM happens to detect.
MANAGER_FALLBACK_EXACT = (
    "can't make it", "cant make it", "parking", "wifi", "wi-fi",
    "dress code", "wheelchair", "accessible", "discount", "private event",
    "high chair", "kids menu", "child menu", "gluten", "vegan", "vegetarian",
    "pet", "dog", "allergic", "allergy",
    # Russian
    "аллергия", "аллергик", "глютен", "веган", "парковка", "вайфай", "вай-фай",
    "дресс-код", "дресс код", "скидка", "частное мероприятие", "детский стул",
    "детское меню", "инвалид", "коляска",
    # Azerbaijani
    "allergiya", "qluten", "vegan", "parkinq", "avtodayanacaq", "geyim qaydası",
    "əlil arabası", "əlçatan", "uşaq stulu", "uşaq menyusu", "endirim",
    "özəl tədbir", "ev heyvanı",
)

# word stems, matched with a boundary only on the left so complaining,
# complaint, reschedule, rescheduling, cancellation all still hit, plus
# Russian and Azerbaijani stems for the same three topics
MANAGER_FALLBACK_PREFIXES = (
    "complain", "reschedul", "cancel",
    "жалоб", "перенос", "перенес", "отмен",
    "şikayət", "təxir", "ləğv",
)

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
    "парковка": "parking",
    "вайфай": "wifi",
    "вай-фай": "wifi",
    "дресс-код": "dress_code",
    "дресс код": "dress_code",
    "инвалид": "accessible",
    "коляска": "accessible",
    "детский стул": "high_chair",
    "детское меню": "kids_menu",
    "parkinq": "parking",
    "avtodayanacaq": "parking",
    "geyim qaydası": "dress_code",
    "əlil arabası": "accessible",
    "əlçatan": "accessible",
    "uşaq stulu": "high_chair",
    "uşaq menyusu": "kids_menu",
}

PARTY_THRESHOLD_RE = re.compile(r"party of (\d+) or more", re.IGNORECASE)

AFFIRMATIVE = (
    "yes", "yes please", "yep", "yeah", "yup", "confirm", "confirmed", "correct",
    "sounds good", "go ahead", "book it", "that's right", "thats right",
    "perfect", "looks good", "all good", "good to go",
    "да", "давай", "хорошо", "ок", "окей", "подтверждаю", "верно", "го",
    "bəli", "hə", "yaxşı", "oldu", "təsdiq", "təsdiqləyirəm", "düzdür",
)
NEGATIVE = (
    "no", "nope", "cancel", "don't book it", "dont book it", "stop", "not yet",
    "нет", "не надо", "отмена", "отменить", "неправильно",
    "yox", "xeyr", "ləğv et", "səhvdir",
)

CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
AZERBAIJANI_RE = re.compile(r"[əƏğĞıİöÖüÜşŞçÇ]")

MAX_HISTORY = 8

UnderstandFn = Callable[[list[str], str, dict], dict]

AVAILABILITY_SLOTS = {"party_size", "date", "time", "area"}


def _is_affirmative(text: str) -> bool:
    lowered = text.strip().lower().rstrip(".!")
    return lowered in AFFIRMATIVE or lowered.startswith("yes")


def _is_negative(text: str) -> bool:
    lowered = text.strip().lower().rstrip(".!")
    return lowered in NEGATIVE


def _guess_language(text: str) -> str | None:
    if CYRILLIC_RE.search(text):
        return "ru"
    if AZERBAIJANI_RE.search(text):
        return "az"
    return None


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
        self.language = DEFAULT_LANGUAGE

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
        self.language = DEFAULT_LANGUAGE
        if not self.restaurant.single_location():
            self.location = None

    def _is_manager_topic(self, text: str) -> bool:
        lowered = text.lower()
        triggers = [t.lower() for t in self.restaurant.manager_triggers]
        if any(trigger in lowered for trigger in triggers):
            return True
        for topic in MANAGER_FALLBACK_EXACT:
            if not re.search(rf"\b{re.escape(topic)}\b", lowered):
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

        guessed = _guess_language(text)
        if guessed:
            self.language = guessed

        self._remember("guest", text)

        if self._is_manager_topic(text):
            reply = t("forward", self.language)
            self._remember("assistant", reply)
            return reply

        if self.awaiting_confirmation:
            if _is_affirmative(text):
                reply = self._finish_booking()
                self._remember("assistant", reply)
                return reply
            if _is_negative(text):
                self.awaiting_confirmation = False
                self.slots = {}
                self.candidates = []
                reply = t("cancelled", self.language)
                self._remember("assistant", reply)
                return reply
            self.awaiting_confirmation = False

        if self.llm_calls >= MAX_LLM_CALLS_PER_SESSION:
            reply = t("limit_reached", self.language)
            self._remember("assistant", reply)
            return reply
        self.llm_calls += 1

        try:
            known_slots = dict(self.slots)
            if self.location:
                known_slots["location"] = self.location.name
            result = self.understand(self.history[:-1], text, known_slots)
        except Exception:
            reply = t("trouble", self.language)
            self._remember("assistant", reply)
            return reply

        detected_language = result.get("language")
        if detected_language in SUPPORTED_LANGUAGES:
            self.language = detected_language

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
            reply = t("forward", self.language)
        elif intent == "irrelevant":
            reply = t("cant_help", self.language)
        elif intent == "question":
            reply = result.get("reply") or t("cant_help", self.language)
        elif intent == "extend":
            reply = self._handle_extend(extracted, result.get("reply", ""))
        elif intent == "booking":
            if AVAILABILITY_SLOTS & extracted.keys():
                self.slots.pop("table_id", None)
                self.candidates = []
            self.slots.update({k: v for k, v in extracted.items() if v})
            reply = self._continue_booking(fallback_reply=result.get("reply", ""))
        else:
            reply = result.get("reply") or t("cant_help", self.language)

        self._remember("assistant", reply)
        return reply

    def _ask_location_reply(self) -> str:
        names = ", ".join(loc.name for loc in self.restaurant.locations)
        return t("ask_location", self.language, names=names)

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
            return fallback_reply or t("ask_missing_booking_info", self.language)

        if "table_id" not in self.slots:
            if not self.candidates:
                self.candidates = self.booking.find_open_tables(
                    self.location.name, self.slots["date"], self.slots["time"],
                    self.slots["party_size"],
                )
                if not self.candidates:
                    self.slots.pop("time", None)
                    return t("nothing_free", self.language)

            narrowed = self._narrow_candidates() or self.candidates
            chosen = narrowed[0]
            self.slots["table_id"] = chosen.id
            self.slots["area"] = chosen.area

        if "name" not in self.slots:
            return t("ask_name", self.language)

        self.awaiting_confirmation = True
        return self._confirmation_summary()

    def _confirmation_summary(self) -> str:
        return t(
            "confirm_booking", self.language,
            party_size=self.slots["party_size"], location=self.location.name,
            date=self.slots["date"], time=self.slots["time"],
            area=self.slots["area"], name=self.slots["name"],
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
            return t("booking_failed", self.language, error=str(e))

        summary = t(
            "booked", self.language,
            restaurant=self.restaurant.name, address=self.location.address,
            date=reservation.date, time=reservation.time, area=area,
            party_size=reservation.party_size, name=reservation.name,
        )
        self.slots = {}
        self.candidates = []
        return summary

    def _handle_extend(self, extracted: dict, fallback_reply: str) -> str:
        self.extend_slots.update({k: v for k, v in extracted.items() if v})
        name = self.extend_slots.get("name")
        date = self.extend_slots.get("date")
        if not name or not date:
            return fallback_reply or t("ask_extend_info", self.language)

        try:
            updated = self.booking.extend(name, date, EXTEND_MINUTES)
        except BookingError as e:
            return t("extend_failed", self.language, error=str(e))

        self.extend_slots = {}
        return t("extended", self.language, name=updated.name, duration=updated.duration_minutes)
