from __future__ import annotations

import os

import anthropic

from restobot.config import Location, Restaurant
from restobot.i18n import SUPPORTED_LANGUAGES

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

INTENTS = ["booking", "extend", "question", "irrelevant", "manager"]


def build_tool_schema(restaurant: Restaurant) -> dict:
    slot_properties = {
        "date": {"type": "string", "description": "YYYY-MM-DD if mentioned"},
        "time": {"type": "string", "description": "HH:MM 24h if mentioned"},
        "party_size": {"type": "integer"},
        "area": {"type": "string", "enum": ["window", "private", "patio", "regular"]},
        "name": {"type": "string"},
    }
    if not restaurant.single_location():
        slot_properties["location"] = {
            "type": "string",
            "enum": [loc.name for loc in restaurant.locations],
            "description": "Which location the guest means, once it's clear from what they said",
        }

    return {
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
                    "description": "Short WhatsApp-style reply to send the guest, one or two sentences, "
                                    "written in the language field below.",
                },
                "language": {
                    "type": "string",
                    "enum": list(SUPPORTED_LANGUAGES),
                    "description": "The language the guest just wrote in: en (English), ru (Russian), "
                                    "or az (Azerbaijani). Always match this in your reply.",
                },
                "slots": {
                    "type": "object",
                    "properties": slot_properties,
                },
            },
            "required": ["intent", "reply", "language"],
        },
    }


def _price_lines(location: Location) -> str:
    priced = [t for t in location.all_tables() if t.price_note]
    if not priced:
        return "No special pricing, standard menu prices apply everywhere."
    return "\n".join(f"- {t.area} ({t.id}): {t.price_note}" for t in priced)


def _notes_lines(location: Location) -> str:
    noted = [t for t in location.all_tables() if t.notes]
    if not noted:
        return ""
    lines = "\n".join(f"- {t.area} ({t.id}): {t.notes}" for t in noted)
    return f"Notes on specific tables:\n{lines}\n"


def _amenities_lines(location: Location) -> str:
    if not location.amenities:
        return ""
    lines = "\n".join(f"- {k}: {v}" for k, v in location.amenities.items())
    return f"Amenities, answer these directly instead of forwarding to a person:\n{lines}\n"


def _location_block(location: Location) -> str:
    return (
        f"{location.name}, {location.address}. Hours: {location.hours}. "
        f"Busy times: {location.busy_hours or 'not specified'}.\n"
        f"Pricing by table:\n{_price_lines(location)}\n"
        f"{_notes_lines(location)}"
        f"{_amenities_lines(location)}"
    ).rstrip()


def build_system_prompt(restaurant: Restaurant) -> str:
    triggers = ", ".join(restaurant.manager_triggers) or "none listed"
    prompt = (
        f"You are the booking assistant for {restaurant.name}, a {restaurant.cuisine} "
        f"restaurant, texting with a guest over WhatsApp.\n\n"
        f"Topics that need a person, not you: {triggers}.\n\n"
    )

    if restaurant.single_location():
        prompt += f"You're handling this location: {_location_block(restaurant.locations[0])}\n\n"
    else:
        blocks = "\n\n".join(_location_block(loc) for loc in restaurant.locations)
        prompt += (
            f"We have multiple locations:\n\n{blocks}\n\n"
            "Figure out which location the guest means from what they say (a name, a "
            "street, 'the one downtown', context earlier in the chat), and put it in "
            "slots.location once you're confident. If it's genuinely unclear and it "
            "matters for what they're asking, ask which location in your reply instead "
            "of guessing.\n\n"
        )

    prompt += (
        "Reply like a real staff member texting back, short and warm, one or two "
        "sentences, no filler, no corporate tone. Ask for one missing detail at a time "
        "when booking. Never invent a table number, a price, or an availability answer, "
        "the app checks real availability separately, you only handle language. Only "
        "state a price using the pricing list above, word for word if possible. Never "
        "mention internal table numbers or IDs (like 'D-G1') to the guest, even if they "
        "ask, that's staff-only. Only describe seating by its general area, window, "
        "patio, private, or regular.\n\n"
        "You understand English, Russian, and Azerbaijani. Reply in whichever one the "
        "guest is currently writing in, even if the conversation started in a different "
        "language, switch the moment they switch. Never mix two languages in one reply."
    )
    return prompt


def build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def classify_turn(client: anthropic.Anthropic, system_prompt: str, tool_schema: dict,
                   history: list[str], user_message: str, known_slots: dict) -> dict:
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
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=[{"role": "user", "content": "\n\n".join(context_lines)}],
    )

    for block in response.content:
        if block.type == "tool_use":
            data = dict(block.input)
            data.setdefault("slots", {})
            return data

    raise RuntimeError("model did not return a tool_use block")
