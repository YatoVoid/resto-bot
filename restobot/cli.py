from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import yaml

from restobot import llm
from restobot.config import ConfigError, Restaurant, load_restaurant
from restobot.engine import Engine

DEFAULT_CONFIG = "config/demo_restaurant.yaml"
LOG_DIR = "logs"


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

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set, export it and try again.")
        sys.exit(1)

    client = llm.build_client()
    system_prompt = llm.build_system_prompt(restaurant)
    tool_schema = llm.build_tool_schema(restaurant)

    def understand(history, text, known_slots):
        return llm.classify_turn(client, system_prompt, tool_schema, history, text, known_slots)

    location = restaurant.locations[0] if restaurant.single_location() else None
    engine = Engine(restaurant, location, understand)
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
