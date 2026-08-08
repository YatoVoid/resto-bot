import os
import tempfile

import pytest

from restobot.config import load_restaurant, ConfigError

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "template_restaurant.yaml")


def test_loads_demo_restaurant():
    r = load_restaurant(DEMO_PATH)
    assert r.name == "Nonna Rosa"
    assert len(r.locations) == 2
    assert not r.single_location()

    downtown = r.get_location("Downtown")
    assert downtown.address == "14 Baker Street"
    assert len(downtown.floors) == 2

    tables = downtown.all_tables()
    assert len(tables) == 8
    window_tables = [t for t in tables if t.area == "window"]
    assert len(window_tables) == 3
    private_tables = [t for t in tables if t.area == "private"]
    assert len(private_tables) == 2


def test_find_floor_by_ordinal_index():
    r = load_restaurant(DEMO_PATH)
    downtown = r.get_location("Downtown")
    assert downtown.find_floor("2").name == "Upper floor"
    assert downtown.find_floor("1").name == "Ground floor"


def test_find_floor_by_keyword():
    r = load_restaurant(DEMO_PATH)
    downtown = r.get_location("Downtown")
    assert downtown.find_floor("ground").name == "Ground floor"
    assert downtown.find_floor("upstairs").name == "Upper floor"

    riverside = r.get_location("Riverside")
    assert riverside.find_floor("main").name == "Main hall"
    assert riverside.find_floor("terrace").name == "Terrace"


def test_find_floor_out_of_range_returns_none():
    r = load_restaurant(DEMO_PATH)
    downtown = r.get_location("Downtown")
    assert downtown.find_floor("9") is None
    assert downtown.find_floor("nonsense") is None


def test_price_note_parsed_when_present():
    r = load_restaurant(DEMO_PATH)
    downtown = r.get_location("Downtown")
    cabinet = next(t for t in downtown.all_tables() if t.id == "D-U1")
    assert cabinet.price_note == "$150 room fee, waived over $400 spend"


def test_price_note_defaults_to_empty_string():
    r = load_restaurant(DEMO_PATH)
    downtown = r.get_location("Downtown")
    regular = next(t for t in downtown.all_tables() if t.id == "D-G3")
    assert regular.price_note == ""


def test_template_config_parses_as_is():
    r = load_restaurant(TEMPLATE_PATH)
    assert r.single_location()
    location = r.locations[0]
    assert len(location.floors) == 2
    assert len(location.all_tables()) == 4


def test_single_location_restaurant():
    yaml_text = """
name: Small Place
locations:
  - name: Only
    address: 1 Main St
    hours: "9-5"
    floors:
      - name: Floor 1
        tables:
          - id: T1
            capacity: 2
            area: regular
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        r = load_restaurant(path)
        assert r.single_location()
        assert r.get_location("Only").hours == "9-5"
    finally:
        os.unlink(path)


def test_missing_name_raises():
    yaml_text = """
locations:
  - name: Only
    address: 1 Main St
    hours: "9-5"
    floors: []
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        with pytest.raises(ConfigError):
            load_restaurant(path)
    finally:
        os.unlink(path)


def test_duplicate_table_id_raises():
    yaml_text = """
name: Dup Place
locations:
  - name: Only
    address: 1 Main St
    hours: "9-5"
    floors:
      - name: Floor 1
        tables:
          - id: T1
            capacity: 2
            area: regular
          - id: T1
            capacity: 4
            area: regular
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        with pytest.raises(ConfigError):
            load_restaurant(path)
    finally:
        os.unlink(path)


def test_zero_capacity_raises():
    yaml_text = """
name: Bad Capacity Place
locations:
  - name: Only
    address: 1 Main St
    hours: "9-5"
    floors:
      - name: Floor 1
        tables:
          - id: T1
            capacity: 0
            area: regular
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        with pytest.raises(ConfigError):
            load_restaurant(path)
    finally:
        os.unlink(path)


def test_negative_capacity_raises():
    yaml_text = """
name: Bad Capacity Place
locations:
  - name: Only
    address: 1 Main St
    hours: "9-5"
    floors:
      - name: Floor 1
        tables:
          - id: T1
            capacity: -2
            area: regular
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        with pytest.raises(ConfigError):
            load_restaurant(path)
    finally:
        os.unlink(path)


def test_empty_locations_raises():
    yaml_text = """
name: No Locations
locations: []
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    try:
        with pytest.raises(ConfigError):
            load_restaurant(path)
    finally:
        os.unlink(path)
