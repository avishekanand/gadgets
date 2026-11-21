from __future__ import annotations

from datetime import date, datetime

from PIL import ImageFont

from dashboard.calendar import Event
from dashboard.config import Config
from dashboard.render import (
    _compose_news,
    _wrap,
    _compose_landscape,
    render_dashboard,
    render_news_panel,
    select_rows,
    truncate,
)
from dashboard.weather import DayFc, Weather

CFG = Config(lat=52.0, lon=4.3, units="C")


def _weather():
    return Weather(6.3, 0, 9.9, 3.2, [DayFc("Sun", 3, 7.1), DayFc("Mon", 3, 7.5), DayFc("Tue", 51, 4.8)])


def test_image_size_and_mode():
    img = render_dashboard(_weather(), [], CFG, datetime(2026, 11, 21, 14, 32))
    assert img.mode == "L"
    assert img.size == (600, 800)


def test_landscape_canvas_is_800x600():
    img = _compose_landscape(_weather(), [], CFG, datetime(2026, 11, 21, 14, 0))
    assert img.size == (800, 600)


def test_landscape_with_news_renders_and_differs():
    news = [{"title": "Headline one", "source": "NPR"},
            {"title": "Headline two", "source": "NYT"}]
    plain = _compose_landscape(_weather(), [], CFG, datetime(2026, 11, 21, 14, 0), news=[])
    withn = _compose_landscape(_weather(), [], CFG, datetime(2026, 11, 21, 14, 0), news=news)
    assert withn.size == (800, 600)
    # drawing headlines must change pixels
    assert list(plain.getdata()) != list(withn.getdata())


def test_headlines_block_does_not_clip_canvas_bottom():
    # Three stories with descender-heavy sources (default news_count=3).
    news = [{"title": f"Headline number {i}", "source": "The Verge gpy"} for i in range(3)]
    img = _compose_landscape(_weather(), [], CFG, datetime(2026, 11, 21, 14, 0), news=news)
    px = img.load()
    rx = 324  # right (agenda/headlines) column start
    # the last two pixel rows of the right column must be blank — nothing clipped
    for yy in (598, 599):
        assert all(px[xx, yy] == 255 for xx in range(rx, 800))


def test_landscape_render_is_device_portrait_size():
    img = render_dashboard(_weather(), [], CFG, datetime(2026, 11, 21, 14, 0), orientation="landscape")
    assert img.mode == "L"
    assert img.size == (600, 800)  # rotated 90° for the device framebuffer


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


def _news(n=5):
    return [{"title": f"Story number {i} with a fairly long headline that will wrap",
             "summary": "A summary sentence that is long enough to span two lines on the panel so we exercise wrapping.",
             "source": "The Verge"} for i in range(n)]


def test_wrap_limits_lines_and_ellipsises():
    f = ImageFont.load_default(size=18)
    lines = _wrap("word " * 80, f, 200, 2)
    assert len(lines) == 2
    assert lines[-1].endswith("…")
    assert all(f.getlength(ln) <= 200 for ln in lines)


def test_news_panel_is_device_portrait_size():
    img = render_news_panel("US", _news(), CFG, datetime(2026, 11, 21, 14, 0))
    assert img.mode == "L"
    assert img.size == (600, 800)


def test_news_panel_differs_by_content():
    a = _compose_news("US", _news(), CFG, datetime(2026, 11, 21, 14, 0))
    b = _compose_news("Science", _news(), CFG, datetime(2026, 11, 21, 14, 0))
    assert a.size == (800, 600)
    assert list(a.getdata()) != list(b.getdata())


def _mixed_news():
    # Short title-only items creep y toward the boundary, then a full
    # 2-line-title + 2-line-summary story — the case that overran the footer.
    short = [{"title": f"Short one {i}", "source": "NPR"} for i in range(9)]
    full = [{"title": "A very long headline that certainly wraps onto a second line here",
             "summary": "And a summary long enough to also span two full lines on the news panel body.",
             "source": "The Verge gpy"}]
    return short + full


def test_news_panel_does_not_clip_bottom_uniform():
    img = _compose_news("US", _news(8), CFG, datetime(2026, 11, 21, 14, 0))
    px = img.load()
    for yy in (598, 599):
        assert all(px[xx, yy] == 255 for xx in range(800))


def test_news_panel_does_not_clip_bottom_mixed_lengths():
    img = _compose_news("US", _mixed_news(), CFG, datetime(2026, 11, 21, 14, 0))
    px = img.load()
    # bottom rows and the footer band must stay clear of story text
    for yy in (568, 598, 599):
        assert all(px[xx, yy] == 255 for xx in range(800))


def test_news_panel_portrait_does_not_clip_bottom():
    cfg = Config(lat=52.0, lon=4.3, orientation="portrait")
    img = _compose_news("US", _mixed_news(), cfg, datetime(2026, 11, 21, 14, 0), size=(600, 800))
    px = img.load()
    for yy in (798, 799):
        assert all(px[xx, yy] == 255 for xx in range(600))


def test_news_panel_handles_empty():
    img = render_news_panel("US", [], CFG, datetime(2026, 11, 21, 14, 0))
    assert img.size == (600, 800)


def test_news_panel_follows_orientation():
    land = Config(lat=52.0, lon=4.3, orientation="landscape")
    port = Config(lat=52.0, lon=4.3, orientation="portrait")
    a = render_news_panel("US", _news(), land, datetime(2026, 11, 21, 14, 0))
    b = render_news_panel("US", _news(), port, datetime(2026, 11, 21, 14, 0))
    assert a.size == b.size == (600, 800)
    assert list(a.getdata()) != list(b.getdata())  # genuinely different orientation
