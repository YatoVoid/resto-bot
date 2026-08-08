import os

import pytest

from restobot.config import load_restaurant
from restobot.engine import Engine, FORWARD_MSG, CANT_HELP_MSG, TROUBLE_MSG

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


def test_area_with_no_matching_candidates_does_not_loop_forever(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?",
         "slots": {"party_size": 4}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
        {"intent": "booking", "reply": "Got it.", "slots": {"time": "14:00"}},
        {"intent": "booking", "reply": "", "slots": {"area": "window"}},
    ])
    engine = Engine(restaurant, downtown, stub)

    engine.handle_message("table for 4")
    engine.handle_message("august 10th")
    r3 = engine.handle_message("2pm")
    assert "Open right now" in r3

    r4 = engine.handle_message("next to window")

    assert "Nothing matches that preference" in r4
    assert "table_id" not in engine.slots
    assert "area" not in engine.slots

    r5 = engine.handle_message("D-G3")
    assert "What name" in r5


def test_floor_and_area_narrow_candidates_together(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?",
         "slots": {"party_size": 2, "floor_hint": "2"}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
        {"intent": "booking", "reply": "", "slots": {"time": "19:00"}},
        {"intent": "booking", "reply": "", "slots": {"area": "window"}},
    ])
    engine = Engine(restaurant, downtown, stub)

    engine.handle_message("a spot on the second floor for 2")
    engine.handle_message("august 10th")
    r3 = engine.handle_message("7pm")
    assert "D-U1" in r3 and "D-U2" in r3 and "D-U3" in r3
    assert "D-G1" not in r3

    r4 = engine.handle_message("next to window")
    assert engine.slots["table_id"] == "D-U3"
    assert "What name" in r4


def test_mid_booking_gibberish_re_asks_current_missing_field(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([
        {"intent": "booking", "reply": "How many people?", "slots": {}},
    ]))
    r1 = engine.handle_message("i want to book")
    assert r1 == "How many people?"

    engine.understand = StubUnderstander([
        {"intent": "booking", "reply": "What date?", "slots": {"party_size": 2}},
    ])
    r2 = engine.handle_message("2")
    assert r2 == "What date?"


def test_table_id_matches_without_dash_or_case(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))
    engine.slots = {"party_size": 2, "date": "2026-08-10", "time": "19:00"}
    engine.candidates = [t for t in downtown.all_tables() if t.id == "D-G1"]

    reply = engine.handle_message("dg1")

    assert engine.slots["table_id"] == "D-G1"
    assert "What name" in reply


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


def test_two_bookings_in_one_session_both_succeed(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?",
         "slots": {"party_size": 2, "area": "window"}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
        {"intent": "booking", "reply": "Got it.", "slots": {"time": "19:00"}},
        {"intent": "booking", "reply": "", "slots": {"name": "Alice"}},
        {"intent": "booking", "reply": "What date works?",
         "slots": {"party_size": 2, "area": "window"}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-11"}},
        {"intent": "booking", "reply": "Got it.", "slots": {"time": "19:00"}},
        {"intent": "booking", "reply": "", "slots": {"name": "Bob"}},
    ])
    engine = Engine(restaurant, downtown, stub)

    r1 = engine.handle_message("table for 2 by the window")
    r2 = engine.handle_message("august 10th")
    r3 = engine.handle_message("7pm")
    if "Open right now" in r3:
        r3 = engine.handle_message("D-G1")
    r4 = engine.handle_message("Alice")
    assert r4.startswith("Booked.")
    assert engine.slots == {}
    assert engine.candidates == []

    r5 = engine.handle_message("table for 2 by the window again")
    r6 = engine.handle_message("august 11th")
    r7 = engine.handle_message("7pm")
    if "Open right now" in r7:
        r7 = engine.handle_message("D-G1")
    r8 = engine.handle_message("Bob")

    assert r8.startswith("Booked.")
    assert "2026-08-11 at 19:00" in r8
    assert "under Bob" in r8
    assert len(engine.booking.reservations) == 2

    names = {r.name for r in engine.booking.reservations}
    dates = {r.date for r in engine.booking.reservations}
    assert names == {"Alice", "Bob"}
    assert dates == {"2026-08-10", "2026-08-11"}


def test_extend_flow_uses_deterministic_confirmation(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))
    engine.booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Bob", duration_minutes=90)

    engine.understand = StubUnderstander([
        {"intent": "extend", "reply": "", "slots": {"name": "Bob", "date": "2026-08-10"}},
    ])

    reply = engine.handle_message("can you extend Bob's table on the 10th")

    assert reply == "Extended, Bob's table now runs 120 minutes."


def test_understand_failure_does_not_crash_or_corrupt_state(restaurant, downtown):
    def broken_understand(history, text, known_slots):
        raise RuntimeError("network blew up")

    engine = Engine(restaurant, downtown, broken_understand)
    engine.slots = {"party_size": 2}
    engine.candidates = []

    reply = engine.handle_message("table for 2 tomorrow")

    assert reply == TROUBLE_MSG
    assert engine.slots == {"party_size": 2}
    assert engine.candidates == []
    assert engine.history[-1] == f"assistant: {TROUBLE_MSG}"


def test_engine_recovers_after_a_failed_call(restaurant, downtown):
    calls = {"n": 0}

    def flaky_understand(history, text, known_slots):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("timeout")
        return {"intent": "question", "reply": "We're open noon to 11.", "slots": {}}

    engine = Engine(restaurant, downtown, flaky_understand)

    first = engine.handle_message("when are you open")
    second = engine.handle_message("when are you open")

    assert first == TROUBLE_MSG
    assert second == "We're open noon to 11."
