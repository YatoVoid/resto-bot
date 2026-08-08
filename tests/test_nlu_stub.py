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


def test_party_size_as_written_word():
    slots = extract_slots("table for two please")
    assert slots["party_size"] == 2


def test_we_are_word_number():
    slots = extract_slots("we are four")
    assert slots["party_size"] == 4


def test_party_of_word_number():
    slots = extract_slots("party of six")
    assert slots["party_size"] == 6


def test_table_for_word_number_and_people():
    slots = extract_slots("a table for eight people")
    assert slots["party_size"] == 8


def test_just_the_word_number_of_us():
    slots = extract_slots("just the two of us")
    assert slots["party_size"] == 2


def test_ppl_abbreviation():
    slots = extract_slots("2 ppl")
    assert slots["party_size"] == 2


def test_tmrw_shorthand_resolves_to_tomorrow():
    slots = extract_slots("tmrw", reference_date=REF)
    assert slots["date"] == "2026-08-09"


def test_2moro_shorthand_resolves_to_tomorrow():
    slots = extract_slots("2moro", reference_date=REF)
    assert slots["date"] == "2026-08-09"


def test_2day_shorthand_resolves_to_today():
    slots = extract_slots("free 2day?", reference_date=REF)
    assert slots["date"] == "2026-08-08"


def test_half_past_resolves_with_pm_assumption():
    slots = extract_slots("half past seven")
    assert slots["time"] == "19:30"


def test_quarter_to_resolves_with_pm_assumption():
    slots = extract_slots("quarter to eight")
    assert slots["time"] == "19:45"


def test_quarter_past_resolves_with_pm_assumption():
    slots = extract_slots("quarter past six")
    assert slots["time"] == "18:15"


def test_oclock_with_apostrophe():
    slots = extract_slots("8 o'clock")
    assert slots["time"] == "20:00"


def test_oclock_no_space_no_apostrophe():
    slots = extract_slots("8oclock")
    assert slots["time"] == "20:00"


def test_ish_time_resolves():
    slots = extract_slots("around 7ish")
    assert slots["time"] == "19:00"


def test_around_bare_hour_resolves():
    slots = extract_slots("can we come around 7")
    assert slots["time"] == "19:00"


def test_around_with_explicit_pm_is_not_double_shifted():
    slots = extract_slots("around 7pm")
    assert slots["time"] == "19:00"


def test_in_n_days_resolves():
    slots = extract_slots("in 3 days", reference_date=REF)
    assert slots["date"] == "2026-08-11"


def test_in_a_week_resolves():
    slots = extract_slots("in a week", reference_date=REF)
    assert slots["date"] == "2026-08-15"


def test_in_n_weeks_resolves():
    slots = extract_slots("in 2 weeks", reference_date=REF)
    assert slots["date"] == "2026-08-22"


def test_day_only_this_month_resolves():
    slots = extract_slots("on the 15th", reference_date=REF)
    assert slots["date"] == "2026-08-15"


def test_day_only_already_passed_rolls_to_next_month():
    slots = extract_slots("on the 1st", reference_date=REF)
    assert slots["date"] == "2026-09-01"


def test_negated_area_is_not_extracted():
    slots = extract_slots("actually not window, something else")
    assert "area" not in slots


def test_anything_but_area_is_not_extracted():
    slots = extract_slots("anything but window is fine")
    assert "area" not in slots


def test_long_rambling_message_extracts_everything():
    text = (
        "hey so basically me and my wife want to come by maybe tomorrow "
        "evening around 7 or so, table for two, somewhere quiet would be "
        "nice if possible thanks"
    )
    slots = extract_slots(text, reference_date=REF)
    assert slots["date"] == "2026-08-09"
    assert slots["time"] == "19:00"
    assert slots["party_size"] == 2


def test_long_formal_message_extracts_everything():
    text = (
        "good afternoon, I was wondering if it would be possible to "
        "reserve a table for four people this coming friday at around "
        "half past seven in the evening, preferably somewhere near a "
        "window if available"
    )
    slots = extract_slots(text, reference_date=REF)
    assert slots["date"] == "2026-08-14"
    assert slots["time"] == "19:30"
    assert slots["party_size"] == 4
    assert slots["area"] == "window"
