from __future__ import annotations

from datetime import datetime
from pathlib import Path

from dashboard.calendar import parse_ics

FIX = Path(__file__).resolve().parent / "fixtures" / "sample.ics"
TZ = "Europe/Amsterdam"
START = datetime(2026, 11, 21, 0, 0)
END = datetime(2026, 11, 23, 0, 0)


def _events():
    return parse_ics(FIX.read_bytes(), START, END, TZ)


def test_parse_includes_recurring():
    titles = [e.title for e in _events()]
    assert "Weekly Review" in titles  # the Sat instance of the weekly rule


def test_all_day_has_no_time():
    fam = next(e for e in _events() if e.title == "Family Day")
    assert fam.all_day is True
    assert fam.start is None


def test_sorted_all_day_first_then_by_start():
    titles = [e.title for e in _events()]
    assert titles == ["Family Day", "Standup", "Weekly Review"]
