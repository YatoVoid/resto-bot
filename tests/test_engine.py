import os

import pytest

from restobot.config import load_restaurant
from restobot.engine import Engine, FORWARD_MSG, CANT_HELP_MSG

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


def test_manager_keyword_precheck_skips_llm(restaurant, downtown):
    stub = StubUnderstander([])
    engine = Engine(restaurant, downtown, stub)

    reply = engine.handle_message("I need to talk about a refund")

    assert reply == FORWARD_MSG
    assert stub.calls == []


def test_manager_intent_forces_fixed_reply(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "manager", "reply": "let me check on that for you personally", "slots": {}},
    ])
    engine = Engine(restaurant, downtown, stub)

    reply = engine.handle_message("something odd happened last visit")

    assert reply == FORWARD_MSG


def test_irrelevant_intent_forces_fixed_decline(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "irrelevant", "reply": "haha good one", "slots": {}},
    ])
    engine = Engine(restaurant, downtown, stub)

    reply = engine.handle_message("what's the weather like")

    assert reply == CANT_HELP_MSG


def test_question_intent_passes_model_reply_through(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "question", "reply": "We're open Tue-Sun noon to 11.", "slots": {}},
    ])
    engine = Engine(restaurant, downtown, stub)

    reply = engine.handle_message("when are you open")

    assert reply == "We're open Tue-Sun noon to 11."


def test_full_booking_flow_produces_accurate_summary(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?",
         "slots": {"party_size": 2, "area": "window"}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
        {"intent": "booking", "reply": "Got it.", "slots": {"time": "19:00"}},
        {"intent": "booking", "reply": "", "slots": {"name": "Alice"}},
    ])
    engine = Engine(restaurant, downtown, stub)

    r1 = engine.handle_message("table for 2 by the window")
    assert r1 == "What date works?"

    r2 = engine.handle_message("august 10th")
    assert r2 == "What time?"

    r3 = engine.handle_message("7pm")
    assert "Open right now" in r3 or "Booked" in r3

    if "Open right now" in r3:
        r3 = engine.handle_message("D-G1")

    assert "What name" in r3

    r4 = engine.handle_message("Alice")

    assert r4.startswith("Booked.")
    assert "Nonna Rosa" in r4
    assert "14 Baker Street" in r4
    assert "2026-08-10 at 19:00" in r4
    assert "party of 2" in r4
    assert "under Alice" in r4
    assert len(engine.booking.reservations) == 1


def test_extend_flow_uses_deterministic_confirmation(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))
    engine.booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Bob", duration_minutes=90)

    engine.understand = StubUnderstander([
        {"intent": "extend", "reply": "", "slots": {"name": "Bob", "date": "2026-08-10"}},
    ])

    reply = engine.handle_message("can you extend Bob's table on the 10th")

    assert reply == "Extended, Bob's table now runs 120 minutes."
