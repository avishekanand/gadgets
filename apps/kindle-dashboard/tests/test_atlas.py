from __future__ import annotations

import json
from pathlib import Path

from dashboard.atlas import parse_atlas

FIX = Path(__file__).resolve().parent / "fixtures" / "atlas_sample.json"
TZ = "Europe/Amsterdam"


def _events():
    return parse_atlas(json.loads(FIX.read_text()), TZ)


def test_timed_event_parsed():
    standup = next(e for e in _events() if e.title == "Standup - Monday")
    assert standup.all_day is False
    assert standup.start is not None
    assert standup.start.hour == 9 and standup.start.minute == 45


def test_all_day_event_has_no_time():
    lux = next(e for e in _events() if e.title == "Luxembourg Visit")
    assert lux.all_day is True
    assert lux.start is None


def test_sorted_all_day_first_within_day():
    # On a day with both, the all-day event must sort before timed ones.
    from datetime import date

    day = date(2026, 11, 23)
    same_day = [e for e in _events() if e.day == day]
    assert same_day[0].all_day is True
