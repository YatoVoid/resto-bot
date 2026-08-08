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


def test_price_question_returns_real_price_note():
    understand, _, loc = _understander()
    result = understand([], "how much for a window table", {})
    assert result["intent"] == "question"
    priced = next(t for t in loc.all_tables() if t.price_note)
    assert priced.price_note in result["reply"]


def test_coffee_is_not_misread_as_a_price_question():
    understand, _, _ = _understander()
    result = understand([], "do you have good coffee", {})
    assert result["intent"] == "irrelevant"


def test_toffee_alone_is_not_misread_as_a_price_question():
    understand, _, _ = _understander()
    result = understand([], "do you serve toffee desserts", {})
    assert result["intent"] == "irrelevant"


def test_extend_text_returns_extend_intent():
    understand, _, _ = _understander()
    result = understand([], "can we extend our table, longer please", {})
    assert result["intent"] == "extend"


def test_multi_word_phrase_still_matches_after_boundary_fix():
    understand, _, loc = _understander()
    result = understand([], "how much would a window table run", {})
    assert result["intent"] == "question"
    priced = next(t for t in loc.all_tables() if t.price_note)
    assert priced.price_note in result["reply"]


def test_gibberish_returns_irrelevant():
    understand, _, _ = _understander()
    result = understand([], "do you think the stock market will crash", {})
    assert result["intent"] == "irrelevant"
