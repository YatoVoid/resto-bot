from __future__ import annotations

from dataclasses import dataclass, field
import yaml


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Table:
    id: str
    capacity: int
    area: str
    notes: str = ""
    price_note: str = ""


@dataclass(frozen=True)
class Floor:
    name: str
    tables: list[Table]


@dataclass(frozen=True)
class Location:
    name: str
    address: str
    hours: str
    floors: list[Floor]
    busy_hours: str = ""
    amenities: dict[str, str] = field(default_factory=dict)

    def all_tables(self) -> list[Table]:
        return [t for f in self.floors for t in f.tables]

    def table_floor(self, table_id: str) -> str:
        for f in self.floors:
            for t in f.tables:
                if t.id == table_id:
                    return f.name
        raise KeyError(table_id)

    def find_floor(self, hint: str) -> Floor | None:
        hint = hint.lower()
        if hint.isdigit():
            idx = int(hint) - 1
            if 0 <= idx < len(self.floors):
                return self.floors[idx]
            return None

        keyword_groups = {
            "ground": ("ground",), "bottom": ("ground",), "downstairs": ("ground",),
            "upper": ("upper",), "top": ("upper",), "upstairs": ("upper",),
            "roof": ("upper",), "rooftop": ("upper",),
            "main": ("main",), "terrace": ("terrace",),
        }
        for keyword in keyword_groups.get(hint, (hint,)):
            for f in self.floors:
                if keyword in f.name.lower():
                    return f
        return None


@dataclass(frozen=True)
class Restaurant:
    name: str
    cuisine: str
    locations: list[Location]
    manager_triggers: list[str] = field(default_factory=list)

    def single_location(self) -> bool:
        return len(self.locations) == 1

    def get_location(self, name: str) -> Location:
        for loc in self.locations:
            if loc.name.lower() == name.lower():
                return loc
        raise KeyError(name)


def _require(d: dict, key: str, ctx: str):
    if key not in d or d[key] in (None, ""):
        raise ConfigError(f"missing '{key}' in {ctx}")
    return d[key]


def _build_table(raw: dict, ctx: str) -> Table:
    table_id = str(_require(raw, "id", ctx))
    capacity = int(_require(raw, "capacity", ctx))
    if capacity <= 0:
        raise ConfigError(f"table '{table_id}' in {ctx} has capacity {capacity}, must be positive")
    return Table(
        id=table_id,
        capacity=capacity,
        area=str(_require(raw, "area", ctx)),
        notes=str(raw.get("notes", "")),
        price_note=str(raw.get("price_note", "")),
    )


def _build_floor(raw: dict, ctx: str) -> Floor:
    name = _require(raw, "name", ctx)
    raw_tables = _require(raw, "tables", ctx)
    tables = [_build_table(t, f"{ctx}/{name}") for t in raw_tables]
    seen = set()
    for t in tables:
        if t.id in seen:
            raise ConfigError(f"duplicate table id '{t.id}' in {ctx}/{name}")
        seen.add(t.id)
    return Floor(name=name, tables=tables)


def _build_location(raw: dict, ctx: str) -> Location:
    name = _require(raw, "name", ctx)
    raw_floors = _require(raw, "floors", ctx)
    floors = [_build_floor(f, f"{ctx}/{name}") for f in raw_floors]
    return Location(
        name=name,
        address=str(_require(raw, "address", ctx)),
        hours=str(_require(raw, "hours", ctx)),
        floors=floors,
        busy_hours=str(raw.get("busy_hours", "")),
        amenities={str(k): str(v) for k, v in (raw.get("amenities") or {}).items()},
    )


def load_restaurant(path: str) -> Restaurant:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ConfigError(f"empty config file: {path}")

    name = _require(raw, "name", "restaurant")
    raw_locations = _require(raw, "locations", "restaurant")
    if not raw_locations:
        raise ConfigError("restaurant must have at least one location")

    locations = [_build_location(loc, "restaurant") for loc in raw_locations]

    return Restaurant(
        name=str(name),
        cuisine=str(raw.get("cuisine", "")),
        locations=locations,
        manager_triggers=list(raw.get("manager_triggers", [])),
    )
