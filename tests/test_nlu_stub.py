from datetime import date

from restobot.nlu_stub import extract_slots

REF = date(2026, 8, 8)  # a Saturday


def test_table_for_and_relative_date_and_time():
    slots = extract_slots("table for 4 tomorrow at 8pm", reference_date=REF)
    assert slots["party_size"] == 4
    assert slots["date"] == "2026-08-09"
    assert slots["time"] == "20:00"


def test_area_synonym_cabinet_maps_to_private():
    slots = extract_slots("can we get a private cabinet")
    assert slots["area"] == "private"


def test_window_seat():
    slots = extract_slots("window seat please")
    assert slots["area"] == "window"


def test_name_pattern():
    slots = extract_slots("my name is Alice")
    assert slots["name"] == "Alice"


def test_party_of_and_iso_date_and_24h_time():
    slots = extract_slots("party of 2 on 2026-08-10 at 19:30")
    assert slots["party_size"] == 2
    assert slots["date"] == "2026-08-10"
    assert slots["time"] == "19:30"


def test_weekday_resolves_to_next_occurrence():
    slots = extract_slots("can I book for monday evening", reference_date=REF)
    assert slots["date"] == "2026-08-10"


def test_today_resolves_to_reference_date():
    slots = extract_slots("table for 2 today at 7pm", reference_date=REF)
    assert slots["date"] == "2026-08-08"
    assert slots["time"] == "19:00"


def test_no_match_returns_empty_for_missing_fields():
    slots = extract_slots("hello there")
    assert "date" not in slots
    assert "time" not in slots
    assert "party_size" not in slots


def test_after_tomorrow_resolves_two_days_ahead():
    slots = extract_slots("can we come after tomorrow", reference_date=REF)
    assert slots["date"] == "2026-08-10"


def test_day_after_tomorrow_resolves_two_days_ahead():
    slots = extract_slots("day after tomorrow works for us", reference_date=REF)
    assert slots["date"] == "2026-08-10"


def test_written_month_day_resolves():
    slots = extract_slots("how about august 10th", reference_date=REF)
    assert slots["date"] == "2026-08-10"


def test_day_of_month_resolves():
    slots = extract_slots("the 10th of august please", reference_date=REF)
    assert slots["date"] == "2026-08-10"


def test_noon_resolves_to_twelve():
    slots = extract_slots("can we come at noon")
    assert slots["time"] == "12:00"


def test_morning_resolves_to_a_time():
    slots = extract_slots("sometime in the morning")
    assert slots["time"] == "10:00"


def test_evening_resolves_to_a_time():
    slots = extract_slots("an evening table please")
    assert slots["time"] == "19:00"


def test_couch_maps_to_private_area():
    slots = extract_slots("a couch would be nice")
    assert slots["area"] == "private"


def test_center_maps_to_regular_area():
    slots = extract_slots("something in the center")
    assert slots["area"] == "regular"


def test_corner_maps_to_regular_area():
    slots = extract_slots("a table in the corner")
    assert slots["area"] == "regular"


def test_second_floor_extracts_floor_hint():
    slots = extract_slots("can we get a spot on the second floor")
    assert slots["floor_hint"] == "2"


def test_upstairs_extracts_floor_keyword():
    slots = extract_slots("somewhere upstairs would be great")
    assert slots["floor_hint"] == "upstairs"


def test_long_message_extracts_floor_and_area_together():
    slots = extract_slots("i want a spot on second floor next to window")
    assert slots["floor_hint"] == "2"
    assert slots["area"] == "window"
