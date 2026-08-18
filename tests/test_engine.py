import os
from dataclasses import replace

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


def test_area_with_no_matching_candidates_falls_back_to_any_open_table(restaurant, downtown):
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
    engine.handle_message("2pm")

    r4 = engine.handle_message("next to window")
    assert "table_id" in engine.slots
    assert engine.slots["area"] == "regular"
    assert "D-" not in r4 and "-U" not in r4


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
    engine.handle_message("7pm")

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


def test_table_id_and_area_are_auto_assigned_without_asking(restaurant, downtown):
    stub = StubUnderstander([{"intent": "booking", "reply": "", "slots": {}}])
    engine = Engine(restaurant, downtown, stub)
    engine.slots = {"party_size": 2, "date": "2026-08-10", "time": "19:00"}

    reply = engine.handle_message("does not matter, slots already complete")

    assert "table_id" in engine.slots
    assert "area" in engine.slots
    assert "What name" in reply


def test_full_booking_flow_asks_for_confirmation_before_booking(restaurant, downtown):
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
    assert "What name" in r3

    r4 = engine.handle_message("Alice")
    assert "Just to confirm" in r4
    assert "window" in r4
    assert "D-" not in r4
    assert engine.awaiting_confirmation is True
    assert len(engine.booking.reservations) == 0

    r5 = engine.handle_message("yes")

    assert r5.startswith("Booked.")
    assert "Nonna Rosa" in r5
    assert "14 Baker Street" in r5
    assert "2026-08-10 at 19:00" in r5
    assert "party of 2" in r5
    assert "under Alice" in r5
    assert "D-" not in r5
    assert len(engine.booking.reservations) == 1
    assert engine.awaiting_confirmation is False


def test_declining_confirmation_cancels_and_clears_slots(restaurant, downtown):
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?", "slots": {"party_size": 2}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
        {"intent": "booking", "reply": "", "slots": {"time": "19:00"}},
        {"intent": "booking", "reply": "", "slots": {"name": "Alice"}},
    ])
    engine = Engine(restaurant, downtown, stub)

    engine.handle_message("table for 2")
    engine.handle_message("august 10th")
    engine.handle_message("7pm")
    r4 = engine.handle_message("Alice")
    assert "Just to confirm" in r4

    r5 = engine.handle_message("no")

    assert "cancelled" in r5.lower()
    assert engine.slots == {}
    assert engine.awaiting_confirmation is False
    assert len(engine.booking.reservations) == 0


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

    engine.handle_message("table for 2 by the window")
    engine.handle_message("august 10th")
    engine.handle_message("7pm")
    engine.handle_message("Alice")
    r4 = engine.handle_message("yes")
    assert r4.startswith("Booked.")
    assert engine.slots == {}
    assert engine.candidates == []

    engine.handle_message("table for 2 by the window again")
    engine.handle_message("august 11th")
    engine.handle_message("7pm")
    engine.handle_message("Bob")
    r8 = engine.handle_message("yes")

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


def test_resolved_location_is_fed_back_to_the_understander(restaurant):
    stub = StubUnderstander([
        {"intent": "question", "reply": "We're at 14 Baker Street.", "slots": {"location": "Downtown"}},
        {"intent": "question", "reply": "We're open Tue-Sun.", "slots": {}},
    ])
    engine = Engine(restaurant, None, stub)

    engine.handle_message("where's the downtown one")
    engine.handle_message("what are your hours")

    assert stub.calls[1][2]["location"] == "Downtown"


def test_idle_session_past_timeout_forgets_conversation(restaurant, downtown):
    clock = {"t": 0.0}
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?", "slots": {"party_size": 2}},
        {"intent": "booking", "reply": "How many people?", "slots": {}},
    ])
    engine = Engine(restaurant, downtown, stub, now_fn=lambda: clock["t"])

    engine.handle_message("table for 2")
    assert engine.slots == {"party_size": 2}

    clock["t"] += 301
    engine.handle_message("still there?")

    assert engine.slots == {}
    assert engine.history == ["guest: still there?", "assistant: How many people?"]


def test_active_session_within_timeout_keeps_state(restaurant, downtown):
    clock = {"t": 0.0}
    stub = StubUnderstander([
        {"intent": "booking", "reply": "What date works?", "slots": {"party_size": 2}},
        {"intent": "booking", "reply": "What time?", "slots": {"date": "2026-08-10"}},
    ])
    engine = Engine(restaurant, downtown, stub, now_fn=lambda: clock["t"])

    engine.handle_message("table for 2")
    clock["t"] += 200
    engine.handle_message("august 10th")

    assert engine.slots == {"party_size": 2, "date": "2026-08-10"}


def test_extend_requires_fresh_name_even_if_a_prior_booking_named_someone(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))
    engine.booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Alice", duration_minutes=90)
    engine.slots = {"name": "Alice"}

    engine.understand = StubUnderstander([
        {"intent": "extend", "reply": "", "slots": {"date": "2026-08-10"}},
    ])

    reply = engine.handle_message("can you extend our table on the 10th")

    assert reply != "Extended, Alice's table now runs 120 minutes."
    assert "name" in reply.lower() or "who" in reply.lower()


def test_llm_call_cap_stops_burning_tokens_and_forwards_instead(restaurant, downtown):
    from restobot.engine import MAX_LLM_CALLS_PER_SESSION, LIMIT_REACHED_MSG

    stub = StubUnderstander([
        {"intent": "irrelevant", "reply": "", "slots": {}}
        for _ in range(MAX_LLM_CALLS_PER_SESSION)
    ])
    engine = Engine(restaurant, downtown, stub)

    for _ in range(MAX_LLM_CALLS_PER_SESSION):
        engine.handle_message("hello")

    assert len(stub.calls) == MAX_LLM_CALLS_PER_SESSION

    reply = engine.handle_message("hello again")

    assert reply == LIMIT_REACHED_MSG
    assert len(stub.calls) == MAX_LLM_CALLS_PER_SESSION


def test_configured_amenity_is_answered_instead_of_forwarded(restaurant):
    downtown = restaurant.get_location("Downtown")
    downtown_with_parking = replace(downtown, amenities={"parking": "free lot behind the building"})
    stub = StubUnderstander([
        {"intent": "question", "reply": "Yes, free lot behind the building.", "slots": {}},
    ])
    engine = Engine(restaurant, downtown_with_parking, stub)

    reply = engine.handle_message("do you have parking")

    assert reply == "Yes, free lot behind the building."


def test_unconfigured_amenity_still_forwards(restaurant, downtown):
    engine = Engine(restaurant, downtown, StubUnderstander([]))

    reply = engine.handle_message("do you have parking")

    assert reply == FORWARD_MSG
