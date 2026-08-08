import os

import pytest

from restobot.config import load_restaurant
from restobot.availability import Booking, BookingError

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "demo_restaurant.yaml")


@pytest.fixture
def booking():
    r = load_restaurant(DEMO_PATH)
    return Booking(r)


def test_find_open_tables_matches_party_and_area(booking):
    open_tables = booking.find_open_tables("Downtown", "2026-08-10", "19:00", 2, area="window")
    ids = {t.id for t in open_tables}
    assert ids == {"D-G1", "D-G2", "D-U3"}


def test_book_removes_table_from_open_list(booking):
    booking.book("Downtown", "D-G1", "2026-08-10", "19:00", 2, "Alice")
    open_tables = booking.find_open_tables("Downtown", "2026-08-10", "19:00", 2, area="window")
    ids = {t.id for t in open_tables}
    assert "D-G1" not in ids
    assert "D-G2" in ids


def test_book_party_too_big_for_table_raises(booking):
    with pytest.raises(BookingError):
        booking.book("Downtown", "D-G1", "2026-08-10", "19:00", 5, "Bob")


def test_double_booking_same_table_time_raises(booking):
    booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Carl")
    with pytest.raises(BookingError):
        booking.book("Downtown", "D-G3", "2026-08-10", "19:30", 4, "Dana")


def test_non_overlapping_time_same_table_succeeds(booking):
    booking.book("Downtown", "D-G3", "2026-08-10", "12:00", 4, "Carl", duration_minutes=60)
    reservation = booking.book("Downtown", "D-G3", "2026-08-10", "13:30", 4, "Dana")
    assert reservation.table_id == "D-G3"


def test_different_date_same_table_time_succeeds(booking):
    booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Carl")
    reservation = booking.book("Downtown", "D-G3", "2026-08-11", "19:00", 4, "Dana")
    assert reservation.date == "2026-08-11"


def test_extend_success(booking):
    booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Carl", duration_minutes=60)
    updated = booking.extend("Carl", "2026-08-10", 30)
    assert updated.duration_minutes == 90


def test_extend_blocked_by_conflict(booking):
    booking.book("Downtown", "D-G3", "2026-08-10", "19:00", 4, "Carl", duration_minutes=60)
    booking.book("Downtown", "D-G3", "2026-08-10", "20:15", 4, "Dana", duration_minutes=60)
    with pytest.raises(BookingError):
        booking.extend("Carl", "2026-08-10", 60)


def test_extend_no_reservation_raises(booking):
    with pytest.raises(BookingError):
        booking.extend("Nobody", "2026-08-10", 30)


def test_find_reservation_unknown_returns_none(booking):
    assert booking.find_reservation("Nobody", "2026-08-10") is None
