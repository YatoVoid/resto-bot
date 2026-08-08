import os

import pytest

from restobot.config import load_restaurant
from restobot.engine import Engine, FORWARD_MSG
from restobot.offline import build_offline_understander

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")


@pytest.fixture
def restaurant():
    return load_restaurant(DEMO_PATH)


@pytest.fixture
def downtown(restaurant):
    return restaurant.get_location("Downtown")


def _fresh_engine(restaurant, downtown):
    return Engine(restaurant, downtown, build_offline_understander(restaurant, downtown))


@pytest.mark.parametrize("text", [
    "my daughter has a nut allergy",
    "i want to complain about last time",
    "can I get a refund",
    "what's the wifi password",
    "do you have parking",
    "is there a dress code",
    "can I bring my dog",
    "we have a gluten free kid, is that ok",
    "do you have a high chair",
    "can we cancel our booking",
    "we need to reschedule",
    "cant make it 2day, can we do it 2moro instead",
])
def test_topics_needing_a_human_forward_to_manager(restaurant, downtown, text):
    engine = _fresh_engine(restaurant, downtown)
    assert engine.handle_message(text) == FORWARD_MSG


def test_large_party_forwards_even_though_config_only_lists_the_phrase(restaurant, downtown):
    engine = _fresh_engine(restaurant, downtown)
    assert engine.handle_message("we are a party of 12") == FORWARD_MSG


def test_party_under_threshold_does_not_forward(restaurant, downtown):
    engine = _fresh_engine(restaurant, downtown)
    reply = engine.handle_message("table for 4 tomorrow at 8pm")
    assert reply != FORWARD_MSG


@pytest.mark.parametrize("text", [
    "can we extend our reservation by 30 mins",
    "running a bit late, can we get more time",
    "we r running late can we push our booking",
])
def test_extend_phrasing_variants_are_recognised(restaurant, downtown, text):
    engine = _fresh_engine(restaurant, downtown)
    reply = engine.handle_message(text)
    assert reply == "Who's the reservation under?"


def test_texting_shorthand_books_a_table_end_to_end(restaurant, downtown):
    engine = _fresh_engine(restaurant, downtown)

    r1 = engine.handle_message("tbl for 2 2moro at 7pm")
    assert "Open right now" in r1 or "Booked" in r1

    if "Open right now" in r1:
        r1 = engine.handle_message("D-G1")

    assert "What name" in r1

    r2 = engine.handle_message("its wali")
    assert r2.startswith("Booked.")
    assert "party of 2" in r2


def test_long_rambling_message_books_a_table_end_to_end(restaurant, downtown):
    engine = _fresh_engine(restaurant, downtown)
    text = (
        "hey so basically me and my wife want to come by maybe tomorrow "
        "evening around 7 or so, table for two, somewhere quiet would be "
        "nice if possible thanks"
    )
    r1 = engine.handle_message(text)
    assert "Open right now" in r1 or "Booked" in r1

    if "Open right now" in r1:
        r1 = engine.handle_message("D-U1")

    assert "What name" in r1

    r2 = engine.handle_message("my name is Sam")
    assert r2.startswith("Booked.")
    assert "party of 2" in r2


def test_long_formal_message_books_a_table_end_to_end(restaurant, downtown):
    engine = _fresh_engine(restaurant, downtown)
    text = (
        "good afternoon, I was wondering if it would be possible to "
        "reserve a table for four people this coming friday at around "
        "half past seven in the evening, preferably somewhere near a "
        "window if available"
    )
    r1 = engine.handle_message(text)
    assert "Nothing matches that preference" in r1
    assert "area" not in engine.slots

    r1 = engine.handle_message("D-G3")
    assert "What name" in r1

    r2 = engine.handle_message("name is Alice")
    assert r2.startswith("Booked.")
    assert "party of 4" in r2
    assert "19:30" in r2
