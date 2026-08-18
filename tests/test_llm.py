from anthropic.types import Message, ToolUseBlock, Usage

from restobot.config import load_restaurant
import os

from restobot.llm import build_system_prompt, build_tool_schema, classify_turn, INTENTS

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")


def _fake_response(tool_input: dict) -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-haiku-4-5-20251001",
        content=[ToolUseBlock(type="tool_use", id="tool_1", name="respond", input=tool_input)],
        stop_reason="tool_use",
        stop_sequence=None,
        usage=Usage(input_tokens=1, output_tokens=1),
    )


class FakeMessages:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class FakeClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def test_build_system_prompt_includes_facts_for_every_location():
    r = load_restaurant(DEMO_PATH)
    prompt = build_system_prompt(r)
    assert r.name in prompt
    for trigger in r.manager_triggers:
        assert trigger in prompt
    for location in r.locations:
        assert location.address in prompt
        priced_table = next((t for t in location.all_tables() if t.price_note), None)
        if priced_table:
            assert priced_table.price_note in prompt


def test_tool_schema_includes_location_when_multiple_locations():
    r = load_restaurant(DEMO_PATH)
    schema = build_tool_schema(r)["input_schema"]
    assert set(schema["properties"]["intent"]["enum"]) == set(INTENTS)
    assert set(schema["properties"]["intent"]["enum"]) == {
        "booking", "extend", "question", "irrelevant", "manager",
    }
    slot_props = schema["properties"]["slots"]["properties"]
    assert set(slot_props.keys()) == {"date", "time", "party_size", "area", "name", "location"}
    assert set(slot_props["location"]["enum"]) == {loc.name for loc in r.locations}


def test_tool_schema_omits_location_for_single_location_restaurant():
    r = load_restaurant(DEMO_PATH)
    single = r.__class__(
        name=r.name, cuisine=r.cuisine, locations=r.locations[:1], manager_triggers=r.manager_triggers,
    )
    schema = build_tool_schema(single)["input_schema"]
    slot_props = schema["properties"]["slots"]["properties"]
    assert "location" not in slot_props


def test_classify_turn_parses_tool_use_response():
    fake_response = _fake_response({
        "intent": "booking",
        "reply": "Sure, what time works?",
        "slots": {"party_size": 4},
    })
    client = FakeClient(fake_response)
    tool_schema = {"name": "respond", "input_schema": {}}

    result = classify_turn(client, "system prompt", tool_schema, [], "table for 4", {})

    assert result["intent"] == "booking"
    assert result["reply"] == "Sure, what time works?"
    assert result["slots"] == {"party_size": 4}
    assert client.messages.calls[0]["tool_choice"] == {"type": "tool", "name": "respond"}


def test_classify_turn_defaults_missing_slots_to_empty_dict():
    fake_response = _fake_response({"intent": "question", "reply": "We open at noon."})
    client = FakeClient(fake_response)
    tool_schema = {"name": "respond", "input_schema": {}}

    result = classify_turn(client, "system prompt", tool_schema, [], "when do you open", {})

    assert result["slots"] == {}
