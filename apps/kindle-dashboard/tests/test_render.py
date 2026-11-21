from __future__ import annotations

from datetime import date, datetime

from PIL import ImageFont

from dashboard.calendar import Event
from dashboard.config import Config
from dashboard.render import render_dashboard, select_rows, truncate
from dashboard.weather import DayFc, Weather

CFG = Config(lat=52.0, lon=4.3, units="C")


def _weather():
    return Weather(6.3, 0, 9.9, 3.2, [DayFc("Sun", 3, 7.1), DayFc("Mon", 3, 7.5), DayFc("Tue", 51, 4.8)])


def test_image_size_and_mode():
    img = render_dashboard(_weather(), [], CFG, datetime(2026, 11, 21, 14, 32))
    assert img.mode == "L"
    assert img.size == (600, 800)


def test_truncate_adds_ellipsis():
    f = ImageFont.load_default(size=20)
    out = truncate("x" * 200, f, 100)
    assert out.endswith("…")
    assert f.getlength(out) <= 100


def test_agenda_spills_to_tomorrow():
    today = date(2026, 11, 21)
    tmrw = date(2026, 11, 22)
    ag = [
        Event(datetime(2026, 11, 21, 9, 0), False, "A", today),
        Event(datetime(2026, 11, 22, 9, 0), False, "B", tmrw),
        Event(datetime(2026, 11, 22, 10, 0), False, "C", tmrw),
    ]
    rows = select_rows(ag, today, 8)
    assert ("divider", "Tomorrow") in rows


def test_divider_names_non_tomorrow_day_by_weekday():
    today = date(2026, 11, 21)  # Saturday
    monday = date(2026, 11, 23)
    ag = [Event(datetime(2026, 11, 23, 9, 0), False, "X", monday)]
    rows = select_rows(ag, today, 8)
    assert ("divider", "Monday") in rows
    assert ("divider", "Tomorrow") not in rows
