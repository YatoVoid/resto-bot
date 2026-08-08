from __future__ import annotations

from dataclasses import dataclass

from restobot.config import Restaurant, Table

DEFAULT_DURATION_MINUTES = 90


class BookingError(Exception):
    pass


@dataclass
class Reservation:
    name: str
    party_size: int
    date: str
    time: str
    duration_minutes: int
    table_id: str
    location_name: str


def _to_minutes(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _windows_overlap(start_a: int, dur_a: int, start_b: int, dur_b: int) -> bool:
    end_a = start_a + dur_a
    end_b = start_b + dur_b
    return not (end_a <= start_b or end_b <= start_a)


class Booking:
    def __init__(self, restaurant: Restaurant):
        self.restaurant = restaurant
        self.reservations: list[Reservation] = []

    def _table_reservations(self, location_name: str, table_id: str, date: str) -> list[Reservation]:
        return [
            r for r in self.reservations
            if r.location_name == location_name and r.table_id == table_id and r.date == date
        ]

    def _is_free(self, location_name: str, table: Table, date: str, time: str,
                 duration_minutes: int, exclude: Reservation | None = None) -> bool:
        start = _to_minutes(time)
        for r in self._table_reservations(location_name, table.id, date):
            if r is exclude:
                continue
            if _windows_overlap(start, duration_minutes, _to_minutes(r.time), r.duration_minutes):
                return False
        return True

    def find_open_tables(self, location_name: str, date: str, time: str, party_size: int,
                          area: str | None = None,
                          duration_minutes: int = DEFAULT_DURATION_MINUTES) -> list[Table]:
        location = self.restaurant.get_location(location_name)
        open_tables = []
        for table in location.all_tables():
            if table.capacity < party_size:
                continue
            if area and table.area != area:
                continue
            if self._is_free(location_name, table, date, time, duration_minutes):
                open_tables.append(table)
        return open_tables

    def book(self, location_name: str, table_id: str, date: str, time: str,
              party_size: int, name: str,
              duration_minutes: int = DEFAULT_DURATION_MINUTES) -> Reservation:
        location = self.restaurant.get_location(location_name)
        table = next((t for t in location.all_tables() if t.id == table_id), None)
        if table is None:
            raise BookingError(f"no such table '{table_id}' at {location_name}")
        if table.capacity < party_size:
            raise BookingError(f"table {table_id} seats {table.capacity}, party is {party_size}")
        if not self._is_free(location_name, table, date, time, duration_minutes):
            raise BookingError(f"table {table_id} is already booked at that time")

        reservation = Reservation(
            name=name,
            party_size=party_size,
            date=date,
            time=time,
            duration_minutes=duration_minutes,
            table_id=table_id,
            location_name=location_name,
        )
        self.reservations.append(reservation)
        return reservation

    def find_reservation(self, name: str, date: str) -> Reservation | None:
        for r in self.reservations:
            if r.name.lower() == name.lower() and r.date == date:
                return r
        return None

    def extend(self, name: str, date: str, extra_minutes: int) -> Reservation:
        reservation = self.find_reservation(name, date)
        if reservation is None:
            raise BookingError(f"no reservation found for {name} on {date}")

        location = self.restaurant.get_location(reservation.location_name)
        table = next(t for t in location.all_tables() if t.id == reservation.table_id)
        new_duration = reservation.duration_minutes + extra_minutes

        if not self._is_free(reservation.location_name, table, date, reservation.time,
                              new_duration, exclude=reservation):
            raise BookingError("extending would overlap another reservation on that table")

        reservation.duration_minutes = new_duration
        return reservation
