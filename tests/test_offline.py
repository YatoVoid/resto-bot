import os

from restobot.config import load_restaurant
from restobot.offline import build_offline_understander

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")


def _understander():
    r = load_restaurant(DEMO_PATH)
    loc = r.get_location("Downtown")
    return build_offline_understander(r, loc), r, loc


def test_booking_text_extracts_slots_and_asks_missing_detail():
    understand, _, _ = _understander()
    result = understand([], "table for 4 tomorrow at 8pm", {})
    assert result["intent"] == "booking"
    assert result["slots"]["party_size"] == 4
    assert result["reply"] == ""


def test_booking_with_missing_party_size_asks_for_it():
    understand, _, _ = _understander()
    result = understand([], "I want to book a table", {})
    assert result["intent"] == "booking"
    assert result["reply"] == "How many people?"


def test_hours_question_returns_real_hours():
    understand, _, loc = _understander()
    result = understand([], "what are your hours", {})
    assert result["intent"] == "question"
    assert loc.hours in result["reply"]


def test_address_question_returns_real_address():
    understand, _, loc = _understander()
    result = understand([], "where are you located", {})
    assert result["intent"] == "question"
    assert loc.address in result["reply"]


def test_extend_text_returns_extend_intent():
    understand, _, _ = _understander()
    result = understand([], "can we extend our table, longer please", {})
    assert result["intent"] == "extend"


def test_gibberish_returns_irrelevant():
    understand, _, _ = _understander()
    result = understand([], "do you think the stock market will crash", {})
    assert result["intent"] == "irrelevant"
