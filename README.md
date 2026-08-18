# resto-bot

A terminal proof of concept for a restaurant booking assistant meant to
sit behind WhatsApp. It answers guest questions, figures out which
location a guest means from what they say, walks through booking a
table against a real availability model, extends existing reservations,
forwards anything a manager should handle, and declines anything off
topic. Requires an Anthropic API key, runs the real model, no offline
fallback.

## Requirements

- Python 3.10 or newer
- pip
- An Anthropic API key (console.anthropic.com)

## Setup on Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
git clone https://github.com/YatoVoid/resto-bot.git
cd resto-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Setup on Arch

```bash
sudo pacman -S --needed python python-pip
git clone https://github.com/YatoVoid/resto-bot.git
cd resto-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Arch ships venv as part of the base `python` package, no separate
`python-venv` package needed.

## Running it

```bash
export ANTHROPIC_API_KEY=your-key-here
python -m restobot.cli
```

The bot doesn't message first, it waits for the guest's opening message
like a real WhatsApp thread would. Type `quit` or `exit` to end a
session. The full conversation gets saved to
`logs/<restaurant>-<timestamp>.log`, one line per turn, and the
in-memory copy is cleared right after.

To try a different restaurant config:

```bash
python -m restobot.cli --config path/to/your_restaurant.yaml
```

## Running the tests

```bash
python -m pytest tests/ -q
```

Every test runs against mocked logic, none of them need network access
or an API key.

## Customizing a restaurant

Everything about a restaurant lives in one YAML file. Copy
`config/template_restaurant.yaml` to start from a blank, commented
skeleton, or look at `config/demo_restaurant.yaml` for a full
two-location example already filled in. Shape:

```yaml
name: Your Restaurant
cuisine: whatever you serve
manager_triggers:
  - catering
  - complaint

locations:
  - name: Downtown
    address: 14 Baker Street
    hours: "Tue-Sun 12:00-23:00, closed Monday"
    busy_hours: "Fri-Sat 19:00-21:30 is our busiest window"
    amenities:
      parking: "free lot behind the building"
      wifi: "network Guest, password guest123"
      dress_code: "smart casual"
    floors:
      - name: Ground floor
        tables:
          - id: D-G1
            capacity: 2
            area: window
            notes: "quiet corner, good for a date"
            price_note: "$10pp minimum spend"
```

- `area` on a table can be anything, the demo uses window, private,
  patio, regular. The bot never reads out a table's internal `id` to a
  guest, it only ever describes the area.
- `notes` on a table is a free-text hint (accessibility, view, whether
  it's good for groups) that gets fed to the model so it can answer
  questions about specific seating honestly instead of guessing.
- `amenities` is a per-location map of topic to answer. Any key here
  (`parking`, `wifi`, `dress_code`, `accessible`, `high_chair`,
  `kids_menu`, `pets`) makes the bot answer that question directly from
  your text instead of forwarding it to a person. Leave a key out and
  that topic keeps forwarding, which is the safe default. Dietary
  questions (allergy, gluten, vegan, vegetarian), refunds, complaints,
  and cancellations always forward regardless of config, those aren't
  configurable.
- `manager_triggers` is a list of topics that skip the model entirely
  and forward straight to a person, the cheapest and most reliable way
  to handle anything sensitive.
- A single `locations` entry means the bot never has to ask which
  location, it just knows. Two or more, and it figures out the location
  from what the guest says, or asks once if it's genuinely unclear.
- `price_note` on a table is a free-text string like "$10pp minimum
  spend" or "$150 room fee". Leave it off a table for no special
  pricing. The model answers price questions straight from this field,
  nothing gets invented.

The reply tone and the rules the model follows live in
`restobot/llm.py`, in `build_system_prompt`. Edit that text directly to
change how blunt, warm, or formal the assistant sounds, nothing else
needs to change.

## Cost per conversation

The bot runs on `claude-haiku-4-5-20251001` ($1 per million input
tokens, $5 per million output tokens as of this writing). Each guest
message costs one API call. For the bundled demo config, a single turn
runs roughly:

- ~460 tokens for the system prompt (restaurant facts, pricing,
  amenities, tone rules)
- ~270 tokens for the tool schema (sent as part of every request)
- a small, growing slice for conversation history, capped at 8 lines
- ~50-150 tokens for the reply itself, capped at 300

That's roughly 800 input tokens and 100 output tokens per turn, around
**$0.0013 per turn**. A typical booking runs 5-10 turns end to end, so
**expect $0.005-$0.015 per completed conversation** — a fraction of a
cent to a cent and a half. Larger restaurant configs with more
locations, tables, and amenities push the system prompt up and raise
this a bit. Call `client.messages.count_tokens(model=..., system=...)`
against your own config's system prompt (see `restobot/llm.py`,
`build_system_prompt`) for an exact figure instead of this estimate.

## Keeping usage bounded

A guest can't loop forever and run up the bill. Two limits are built
into `restobot/engine.py`:

- **Per-session call cap.** After `MAX_LLM_CALLS_PER_SESSION` (40)
  model calls in one conversation, the bot stops calling the model and
  hands off to a person instead, regardless of what the guest is
  saying. A guest repeating themselves or trying to keep the bot
  talking hits this ceiling and gets forwarded, not an infinite string
  of billed replies.
- **5-minute idle timeout.** If a guest goes quiet for more than five
  minutes, the next message starts a fresh session, conversation
  history and in-progress booking slots included. This also resets the
  call counter, so it's a per-conversation cap, not a per-phone-number
  one.

Manager-topic keyword matching (`_is_manager_topic`) runs before either
limit is even relevant. Complaints, allergies, refunds, and anything
else in `manager_triggers` never reach the model at all, they're
matched with plain regex and forwarded immediately at zero cost.

## How it's built

- `restobot/config.py` loads and validates the YAML.
- `restobot/availability.py` is the actual booking engine, tracks which
  table is free when, books, extends. This never touches the model.
- `restobot/llm.py` wraps the Claude call, forces a structured response
  so parsing never has to guess.
- `restobot/engine.py` routes a classified message to either the
  booking engine or a plain reply. Anything that has to be exact, the
  manager forwarding line, the decline line, the final booking summary,
  is built in Python, never left to the model's own wording. It also
  owns the session timeout and the per-session call cap.
- `restobot/cli.py` is the terminal loop tying it together.
