# resto-bot

A terminal proof of concept for a restaurant booking assistant meant to
sit behind WhatsApp. It answers guest questions, disambiguates between
locations, walks through booking a table against a real availability
model, extends existing reservations, forwards anything a manager should
handle, and declines anything off topic. Runs against Claude when you
give it an API key, and falls back to a network-free heuristic mode when
you don't, so you can try the flow without spending anything.

## Requirements

- Python 3.10 or newer
- pip

## Setup on Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
git clone <this-repo-url> resto-bot
cd resto-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Setup on Arch

```bash
sudo pacman -S --needed python python-pip
git clone <this-repo-url> resto-bot
cd resto-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Arch ships venv as part of the base `python` package, no separate
`python-venv` package needed.

## Running it

Offline, no API key needed, uses a keyword-based fallback instead of the
real model:

```bash
python -m restobot.cli
```

With the real model, short and cheap replies from Claude:

```bash
export ANTHROPIC_API_KEY=your-key-here
python -m restobot.cli
```

The bundled demo config has two locations, so the first thing it asks is
which one you mean. Type `quit` or `exit` to end a session. The full conversation gets saved
to `logs/<restaurant>-<timestamp>.log`, one line per turn, and the
in-memory copy is cleared right after.

To try a different restaurant config:

```bash
python -m restobot.cli --config path/to/your_restaurant.yaml
```

## Running the tests

```bash
python -m pytest tests/ -q
```

Every test runs against mocked or offline logic, none of them need
network access or an API key.

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
    floors:
      - name: Ground floor
        tables:
          - id: D-G1
            capacity: 2
            area: window
```

- `area` on a table can be anything, the demo uses window, private,
  patio, regular. Whatever you pick shows up in the "which one" prompt
  and gets matched against what a guest says.
- `manager_triggers` is a list of topics that skip the model entirely
  and forward straight to a person, cheapest and most reliable way to
  handle anything sensitive.
- A single `locations` entry means no location question ever gets
  asked. Two or more, and the assistant asks once up front and
  remembers the answer for the rest of the session.
- `price_note` on a table is a free-text string like "$10pp minimum
  spend" or "$150 room fee". Leave it off a table for no special
  pricing. Both the real model and the offline fallback answer price
  questions straight from this field, nothing gets invented.

The reply tone and the rules the model follows live in
`restobot/llm.py`, in `build_system_prompt`. Edit that text directly to
change how blunt, warm, or formal the assistant sounds, nothing else
needs to change.

## How it's built

- `restobot/config.py` loads and validates the YAML.
- `restobot/availability.py` is the actual booking engine, tracks which
  table is free when, books, extends. This never touches the model.
- `restobot/llm.py` wraps the Claude call, forces a structured response
  so parsing never has to guess.
- `restobot/engine.py` routes a classified message to either the
  booking engine or a plain reply. Anything that has to be exact, the
  manager forwarding line, the decline line, the final booking summary,
  is built in Python, never left to the model's own wording.
- `restobot/offline.py` is the no-network fallback understander, used
  automatically when no API key is set.
- `restobot/cli.py` is the terminal loop tying it together.
