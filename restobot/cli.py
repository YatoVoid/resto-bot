from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import yaml

from restobot.config import ConfigError, Restaurant, Location, load_restaurant
from restobot.engine import Engine, UnderstandFn
from restobot.offline import build_offline_understander

DEFAULT_CONFIG = "config/demo_restaurant.yaml"
LOG_DIR = "logs"


def pick_location(restaurant: Restaurant) -> Location:
    if restaurant.single_location():
        return restaurant.locations[0]

    names = ", ".join(loc.name for loc in restaurant.locations)
    print(f"We have a few locations: {names}. Which one?")
    while True:
        reply = input("> ").strip()
        if reply.lower() in ("quit", "exit"):
            sys.exit(0)
        for loc in restaurant.locations:
            if loc.name.lower() in reply.lower() or reply.lower() in loc.name.lower():
                return loc
        print(f"Didn't catch that. Pick one of: {names}")


def build_understander(restaurant: Restaurant, location: Location) -> tuple[UnderstandFn, bool]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        from restobot import llm

        client = llm.build_client()
        system_prompt = llm.build_system_prompt(restaurant, location)

        def understand(history, text, known_slots):
            return llm.classify_turn(client, system_prompt, history, text, known_slots)

        return understand, True

    return build_offline_understander(restaurant, location), False


def save_session_log(restaurant: Restaurant, lines: list[str]) -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = restaurant.name.lower().replace(" ", "_")
    path = os.path.join(LOG_DIR, f"{slug}-{ts}.log")
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return path


def run(config_path: str) -> None:
    try:
        restaurant = load_restaurant(config_path)
    except FileNotFoundError:
        print(f"Can't find a config file at {config_path}")
        sys.exit(1)
    except (ConfigError, yaml.YAMLError) as e:
        print(f"That config file has a problem: {e}")
        sys.exit(1)

    print(f"{restaurant.name}, how can I help?")

    location = pick_location(restaurant)
    understand_fn, live = build_understander(restaurant, location)
    if not live:
        print("(no ANTHROPIC_API_KEY set, running in offline mode)")

    engine = Engine(restaurant, location, understand_fn)
    log_lines: list[str] = []

    while True:
        line = input("> ").strip()
        if line.lower() in ("quit", "exit"):
            break
        if not line:
            continue

        reply = engine.handle_message(line)
        print(reply)
        log_lines.append(f"guest: {line}")
        log_lines.append(f"assistant: {reply}")

    if log_lines:
        path = save_session_log(restaurant, log_lines)
        print(f"(session saved to {path})")
        log_lines.clear()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
