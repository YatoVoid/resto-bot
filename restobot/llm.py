from __future__ import annotations

import os

import anthropic

from restobot.config import Location, Restaurant

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

INTENTS = ["booking", "extend", "question", "irrelevant", "manager"]

TOOL_SCHEMA = {
    "name": "respond",
    "description": "Reply to the guest and classify what they need.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": INTENTS,
                "description": "booking = wants a table, extend = wants to change an existing "
                                "reservation, question = asking about the restaurant, irrelevant "
                                "= not about the restaurant at all, manager = needs a human",
            },
            "reply": {
                "type": "string",
                "description": "Short WhatsApp-style reply to send the guest, one or two sentences.",
            },
            "slots": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD if mentioned"},
                    "time": {"type": "string", "description": "HH:MM 24h if mentioned"},
                    "party_size": {"type": "integer"},
                    "area": {"type": "string", "enum": ["window", "private", "patio", "regular"]},
                    "name": {"type": "string"},
                },
            },
        },
        "required": ["intent", "reply"],
    },
}


def build_system_prompt(restaurant: Restaurant, location: Location) -> str:
    triggers = ", ".join(restaurant.manager_triggers) or "none listed"
    return (
        f"You are the booking assistant for {restaurant.name}, a {restaurant.cuisine} "
        f"restaurant. You are texting with a guest over WhatsApp about the {location.name} "
        f"location at {location.address}. Hours: {location.hours}. "
        f"Busy times: {location.busy_hours or 'not specified'}.\n\n"
        f"Topics that need a person, not you: {triggers}.\n\n"
        "Reply like a real staff member texting back, short and warm, one or two "
        "sentences, no filler, no corporate tone. Ask for one missing detail at a time "
        "when booking. Never invent a table number, a price, or an availability answer, "
        "the app checks real availability separately, you only handle language."
    )


def build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def classify_turn(client: anthropic.Anthropic, system_prompt: str, history: list[str],
                   user_message: str, known_slots: dict) -> dict:
    context_lines = []
    if history:
        context_lines.append("Conversation so far:\n" + "\n".join(history))
    if known_slots:
        context_lines.append(f"Details already collected: {known_slots}")
    context_lines.append(f"Guest just said: {user_message}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "respond"},
        messages=[{"role": "user", "content": "\n\n".join(context_lines)}],
    )

    for block in response.content:
        if block.type == "tool_use":
            data = dict(block.input)
            data.setdefault("slots", {})
            return data

    raise RuntimeError("model did not return a tool_use block")
