from __future__ import annotations

import argparse
import sys

from restobot.availability import Booking, BookingError
from restobot.config import Restaurant, Location, Table, load_restaurant
from restobot.nlu_stub import extract_slots

DEFAULT_CONFIG = "config/demo_restaurant.yaml"


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


def describe_open_tables(tables: list[Table]) -> str:
    by_area: dict[str, list[Table]] = {}
    for t in tables:
        by_area.setdefault(t.area, []).append(t)

    parts = []
    for area, area_tables in by_area.items():
        ids = ", ".join(t.id for t in area_tables)
        parts.append(f"{area}: {ids}")
    return " | ".join(parts)


def missing_slot_question(slots: dict) -> str | None:
    if "party_size" not in slots:
        return "How many people?"
    if "date" not in slots:
        return "What date?"
    if "time" not in slots:
        return "What time?"
    return None


def find_table_choice(text: str, candidates: list[Table]) -> Table | None:
    upper = text.upper()
    for t in candidates:
        if t.id.upper() in upper:
            return t
    area = None
    lowered = text.lower()
    for word in ("window", "private", "patio", "regular"):
        if word in lowered:
            area = word
            break
    if area:
        matches = [t for t in candidates if t.area == area]
        if len(matches) == 1:
            return matches[0]
    return None


def run(config_path: str) -> None:
    restaurant = load_restaurant(config_path)
    print(f"{restaurant.name}, how can I help?")

    location = pick_location(restaurant)
    booking = Booking(restaurant)

    slots: dict = {}
    candidates: list[Table] = []

    while True:
        line = input("> ").strip()
        if line.lower() in ("quit", "exit"):
            break
        if not line:
            continue

        if line.lower().startswith("extend"):
            handle_extend(booking, location, line)
            continue

        slots.update(extract_slots(line))

        question = missing_slot_question(slots)
        if question:
            print(question)
            continue

        if "table_id" not in slots:
            if candidates:
                chosen = find_table_choice(line, candidates)
                if chosen:
                    slots["table_id"] = chosen.id
                else:
                    print(f"Which one? {describe_open_tables(candidates)}")
                    continue
            else:
                candidates = booking.find_open_tables(
                    location.name, slots["date"], slots["time"],
                    slots["party_size"], area=slots.get("area"),
                )
                if not candidates:
                    area = slots.get("area")
                    has_area_at_all = any(
                        t.area == area and t.capacity >= slots["party_size"]
                        for t in location.all_tables()
                    ) if area else True
                    if area and not has_area_at_all:
                        print(f"We don't have a {area} table for that many people here, try a different area?")
                        slots.pop("area", None)
                    elif area:
                        print(f"No {area} tables free then, try a different time or area?")
                        slots.pop("time", None)
                        slots.pop("area", None)
                    else:
                        print("Nothing free for that time, want to try a different time?")
                        slots.pop("time", None)
                    continue
                if len(candidates) == 1:
                    slots["table_id"] = candidates[0].id
                else:
                    print(f"Open right now: {describe_open_tables(candidates)}. Which one?")
                    continue

        if "name" not in slots:
            print("What name should I put it under?")
            continue

        try:
            reservation = booking.book(
                location.name, slots["table_id"], slots["date"], slots["time"],
                slots["party_size"], slots["name"],
            )
        except BookingError as e:
            print(f"Couldn't book that: {e}")
            slots.pop("table_id", None)
            candidates = []
            continue

        area = next(t.area for t in location.all_tables() if t.id == reservation.table_id)
        print(
            f"Booked. {restaurant.name}, {location.address}. "
            f"Table {reservation.table_id} ({area}), {reservation.date} at {reservation.time}, "
            f"party of {reservation.party_size}, under {reservation.name}."
        )
        slots = {}
        candidates = []


def handle_extend(booking: Booking, location: Location, line: str) -> None:
    extracted = extract_slots(line)
    name = extracted.get("name")
    if not name:
        print("Extend for who? Say the name.")
        return
    date = extracted.get("date")
    if not date:
        print("What date was the reservation for?")
        return
    try:
        updated = booking.extend(name, date, 30)
    except BookingError as e:
        print(f"Couldn't extend: {e}")
        return
    print(f"Extended {updated.name}'s table to {updated.duration_minutes} minutes.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
