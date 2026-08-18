import os

import pytest

from restobot.config import load_restaurant
from restobot.engine import Engine, CANT_HELP_MSG
from restobot.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, t

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")


class StubUnderstander:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, history, text, known_slots):
        self.calls.append((history, text, dict(known_slots)))
        return self.responses.pop(0)


@pytest.fixture
def restaurant():
    return load_restaurant(DEMO_PATH)


@pytest.fixture
def downtown(restaurant):
    return restaurant.get_location("Downtown")


def test_every_language_has_every_key():
    en_keys = set(TRANSLATIONS["en"].keys())
    for lang in SUPPORTED_LANGUAGES:
        assert set(TRANSLATIONS[lang].keys()) == en_keys


def test_t_falls_back_to_english_for_unknown_language():
    assert t("forward", "fr") == TRANSLATIONS["en"]["forward"]


def test_cyrillic_message_switches_language_before_any_llm_call(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))

    reply = engine.handle_message("у меня аллергия на орехи")

    assert engine.language == "ru"
    assert reply == TRANSLATIONS["ru"]["forward"]


def test_azerbaijani_diacritics_switch_language_before_any_llm_call(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))

    reply = engine.handle_message("şikayətim var")

    assert engine.language == "az"
    assert reply == TRANSLATIONS["az"]["forward"]


def test_llm_reported_language_is_adopted_and_used_for_fixed_replies(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "irrelevant", "reply": "", "slots": {}, "language": "ru"},
    ])
    engine = Engine(restaurant, downtown, stub)

    reply = engine.handle_message("какая погода")

    assert engine.language == "ru"
    assert reply == TRANSLATIONS["ru"]["cant_help"]


def test_language_switches_mid_conversation(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "irrelevant", "reply": "", "slots": {}, "language": "en"},
        {"intent": "irrelevant", "reply": "", "slots": {}, "language": "az"},
    ])
    engine = Engine(restaurant, downtown, stub)

    first = engine.handle_message("what's the weather like")
    assert first == CANT_HELP_MSG
    assert engine.language == "en"

    second = engine.handle_message("hava necedir")
    assert engine.language == "az"
    assert second == TRANSLATIONS["az"]["cant_help"]


def test_confirmation_summary_and_booking_use_current_language(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "", "slots": {"party_size": 2}, "language": "ru"},
        {"intent": "booking", "reply": "", "slots": {"date": "2026-08-10"}, "language": "ru"},
        {"intent": "booking", "reply": "", "slots": {"time": "19:00"}, "language": "ru"},
        {"intent": "booking", "reply": "", "slots": {"name": "Alice"}, "language": "ru"},
    ])
    engine = Engine(restaurant, downtown, stub)

    engine.handle_message("столик на 2")
    engine.handle_message("10 августа")
    engine.handle_message("в 19:00")
    r4 = engine.handle_message("Алиса")

    assert "Подтвердите" in r4

    r5 = engine.handle_message("да")

    assert r5.startswith("Забронировано.")
    assert "на имя Alice" in r5


def test_reset_session_reverts_language_to_default(restaurant, downtown):
    clock = {"t": 0.0}
    engine = Engine(restaurant, downtown, StubUnderstander([]), now_fn=lambda: clock["t"])

    engine.handle_message("у меня аллергия")
    assert engine.language == "ru"

    clock["t"] += 301
    engine.handle_message("hello")

    assert engine.language == "en"
