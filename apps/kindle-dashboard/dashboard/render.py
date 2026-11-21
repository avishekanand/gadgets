"""Render the 600x800 greyscale dashboard (Layout C) with Pillow.

Left column: weather (now + 3-day forecast). Right column: merged agenda.
Footer: "updated HH:MM". No clock. Weather glyphs are drawn, not fonted.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

from dashboard.calendar import Event
from dashboard.config import Config
from dashboard.weather import Weather, weather_glyph

W, H = 600, 800
LEFT_W = 252  # ~42%
INK = 0
GRAY = 110
FAINT = 160
BAND = 232  # light grey left-column background

Row = tuple  # ("event", Event) | ("divider", "Tomorrow")


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def truncate(text: str, font, max_px: float) -> str:
    """Shorten text with an ellipsis so it fits within max_px."""
    if font.getlength(text) <= max_px:
        return text
    ell = "…"
    while text and font.getlength(text + ell) > max_px:
        text = text[:-1]
    return text + ell


def _wrap(text: str, font, max_px: float, max_lines: int) -> list[str]:
    """Greedy word-wrap into at most max_lines lines; ellipsise if it overflows."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    i = 0
    while i < len(words):
        trial = (cur + " " + words[i]).strip()
        if font.getlength(trial) <= max_px or not cur:
            cur = trial
            i += 1
        else:
            lines.append(cur)
            cur = ""
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
        i = len(words)
    if i < len(words) and lines:  # text remained → ellipsise the last line
        last = lines[-1]
        while last and font.getlength(last + "…") > max_px:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def _day_label(day: date, today: date) -> str:
    if day == today + timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%A")  # e.g. "Monday"


def select_rows(agenda: list[Event], today: date, max_rows: int) -> list[Row]:
    """Flatten the agenda into drawable rows, inserting a divider before each
    new day past `today` (named 'Tomorrow' or the weekday). Capped at max_rows."""
    rows: list[Row] = []
    last_day: date | None = None
    for e in agenda:
        if e.day != today and e.day != last_day:
            rows.append(("divider", _day_label(e.day, today)))
        last_day = e.day
        rows.append(("event", e))
        if len(rows) >= max_rows:
            break
    return rows[:max_rows]


def _fmt_temp(c: float, units: str) -> str:
    v = c * 9 / 5 + 32 if units.upper() == "F" else c
    return f"{round(v)}°"


def _draw_glyph(d: ImageDraw.ImageDraw, key: str, cx: int, cy: int, r: int) -> None:
    """Draw a simple distinct weather icon centred at (cx, cy)."""
    def cloud(oy: int = 0):
        d.ellipse([cx - r, cy - r // 3 + oy, cx + r, cy + r + oy], fill=FAINT, outline=INK, width=3)

    if key == "clear":
        d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=FAINT, outline=INK, width=3)
        for a in range(0, 360, 45):
            import math
            dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([cx + dx * (r * 0.7), cy + dy * (r * 0.7), cx + dx * r, cy + dy * r], fill=INK, width=3)
    elif key == "partly":
        d.ellipse([cx - r, cy - r, cx, cy], fill=FAINT, outline=INK, width=3)
        cloud(oy=r // 3)
    elif key == "fog":
        for i, yy in enumerate(range(cy - r // 2, cy + r, max(1, r // 3))):
            d.line([cx - r + (i % 2) * 8, yy, cx + r - (i % 2) * 8, yy], fill=INK, width=3)
    elif key == "storm":
        cloud()
        d.line([cx, cy + r // 2, cx - r // 3, cy + r, cx + r // 6, cy + r, cx - r // 6, cy + r * 1.5], fill=INK, width=4, joint="curve")
    elif key == "snow":
        cloud()
        for dx in (-r // 2, 0, r // 2):
            d.ellipse([cx + dx - 4, cy + r + 4, cx + dx + 4, cy + r + 12], fill=INK)
    elif key == "rain":
        cloud()
        for dx in (-r // 2, 0, r // 2):
            d.line([cx + dx, cy + r + 4, cx + dx - 4, cy + r + 16], fill=INK, width=3)
    else:  # cloud
        cloud()


def render_dashboard(
    weather: Weather,
    agenda: list[Event],
    cfg: Config,
    updated: datetime,
    stale: bool = False,
    orientation: str | None = None,
    news: list[dict] | None = None,
) -> Image.Image:
    """Device-ready 600x800 greyscale image for eips. In landscape mode the
    content is composed at 800x600 and rotated 90° so it reads upright when the
    Kindle is turned on its side."""
    news = news or []
    mode = orientation or cfg.orientation
    if mode == "landscape":
        canvas = _compose_landscape(weather, agenda, cfg, updated, stale, news)
        return canvas.transpose(Image.ROTATE_90 if cfg.flip else Image.ROTATE_270)
    return _compose_portrait(weather, agenda, cfg, updated, stale, news)


def _draw_headlines(d, news, x, y, w, section, fonts):
    """HEADLINES block: a label + up to len(news) stories (title, then source).
    Returns the y below the block."""
    f_label, f_title, f_src = fonts
    d.text((x, y), ("HEADLINES · " + section.upper()) if section else "HEADLINES",
           font=f_label, fill=GRAY)
    d.line([x, y + 22, x + w, y + 22], fill=FAINT, width=2)
    y += 34
    for it in news:
        d.text((x, y), "•", font=f_title, fill=INK)
        d.text((x + 20, y), truncate(it["title"], f_title, w - 20), font=f_title, fill=INK)
        y += 30
        src = it.get("source", "")
        if src:
            d.text((x + 20, y), src, font=f_src, fill=FAINT)
        y += 28
    return y


def render_news_panel(
    section: str,
    items: list[dict],
    cfg: Config,
    updated: datetime,
    stale: bool = False,
) -> Image.Image:
    """A full-screen news card, device-ready 600x800. Follows cfg.orientation so
    it reads upright the same way as the Agenda panel: in landscape it is composed
    at 800x600 and rotated 90°; in portrait it is drawn at 600x800 directly."""
    if cfg.orientation == "landscape":
        canvas = _compose_news(section, items, cfg, updated, stale, (800, 600))
        return canvas.transpose(Image.ROTATE_90 if cfg.flip else Image.ROTATE_270)
    return _compose_news(section, items, cfg, updated, stale, (W, H))


# Worst-case height of one story: 2-line title + 2-line summary + source + gaps.
_STORY_MAX_H = 2 * 29 + 2 * 23 + 21 + 18
_FOOTER_RESERVE = 34


def _compose_news(
    section: str,
    items: list[dict],
    cfg: Config,
    updated: datetime,
    stale: bool = False,
    size: tuple[int, int] = (800, 600),
) -> Image.Image:
    LW, LH = size
    img = Image.new("L", (LW, LH), 255)
    d = ImageDraw.Draw(img)
    pad = 28
    f_hdr = _font(30)
    f_title = _font(25)
    f_sum = _font(18)
    f_src = _font(16)
    f_foot = _font(16)

    head = ("HEADLINES · " + section.upper()) if section else "HEADLINES"
    d.text((pad, 22), head, font=f_hdr, fill=INK)
    d.line([pad, 64, LW - pad, 64], fill=INK, width=2)

    maxw = LW - 2 * pad - 16
    x = pad + 16
    y = 82
    # Stop before a worst-case story could overrun the footer / canvas bottom.
    limit = LH - _STORY_MAX_H - _FOOTER_RESERVE
    if not items:
        d.text((x, y), "No headlines available.", font=f_title, fill=GRAY)
    for it in items:
        if y > limit:
            break
        for ln in _wrap(it.get("title", ""), f_title, maxw, 2):
            d.text((x, y), ln, font=f_title, fill=INK)
            y += 29
        summ = it.get("summary", "")
        if summ:
            for ln in _wrap(summ, f_sum, maxw, 2):
                d.text((x, y), ln, font=f_sum, fill=GRAY)
                y += 23
        src = it.get("source", "")
        if src:
            d.text((x, y), src, font=f_src, fill=FAINT)
            y += 21
        y += 12
        d.line([pad, y - 6, LW - pad, y - 6], fill=BAND, width=1)
        y += 6

    foot = "updated " + updated.strftime("%H:%M") + ("  ·  stale" if stale else "")
    d.text((pad, LH - 28), foot, font=f_foot, fill=FAINT)
    return img


def _compose_portrait(
    weather: Weather,
    agenda: list[Event],
    cfg: Config,
    updated: datetime,
    stale: bool = False,
    news: list[dict] | None = None,
) -> Image.Image:
    news = news or []
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    f_label = _font(18)
    f_big = _font(96)
    f_hilo = _font(28)
    f_fc_day = _font(20)
    f_fc_hi = _font(22)
    f_sec = _font(24)
    f_time = _font(24)
    f_title = _font(26)
    f_div = _font(20)
    f_foot = _font(18)

    today = updated.date()

    # ---- left weather column ----
    d.rectangle([0, 0, LEFT_W, H], fill=BAND)
    pad = 22
    d.text((pad, 24), "NOW", font=f_label, fill=GRAY)
    _draw_glyph(d, weather_glyph(weather.code), LEFT_W // 2, 110, 42)
    d.text((pad, 168), _fmt_temp(weather.temp_c, cfg.units), font=f_big, fill=INK)
    d.text((pad, 288), f"H {_fmt_temp(weather.hi_c, cfg.units)}   L {_fmt_temp(weather.lo_c, cfg.units)}", font=f_hilo, fill=GRAY)

    # 3-day forecast strip near the bottom of the column
    fc_y = 640
    d.line([pad, fc_y - 20, LEFT_W - pad, fc_y - 20], fill=FAINT, width=2)
    cell_w = (LEFT_W - 2 * pad) // 3
    for i, day in enumerate(weather.forecast[:3]):
        cx = pad + cell_w * i + cell_w // 2
        d.text((cx, fc_y), day.day_abbr, font=f_fc_day, fill=GRAY, anchor="ma")
        _draw_glyph(d, weather_glyph(day.code), cx, fc_y + 52, 18)
        d.text((cx, fc_y + 86), _fmt_temp(day.hi_c, cfg.units), font=f_fc_hi, fill=INK, anchor="ma")

    # ---- right agenda column ----
    rx = LEFT_W + 24
    rw = W - rx - 20
    d.text((rx, 24), updated.strftime("%a %-d %b").upper(), font=f_sec, fill=INK)
    d.line([rx, 60, W - 20, 60], fill=FAINT, width=2)

    y = 78
    line_h = 46
    for kind, payload in select_rows(agenda, today, cfg.agenda_rows):
        if kind == "divider":
            y += 8
            d.text((rx, y), payload, font=f_div, fill=GRAY)
            d.line([rx, y + 26, W - 20, y + 26], fill=FAINT, width=1)
            y += 38
            continue
        e: Event = payload
        if e.all_day:
            d.text((rx, y), "all-day", font=f_time, fill=FAINT)
        else:
            d.text((rx, y), e.start.strftime("%H:%M"), font=f_time, fill=GRAY)
        title = truncate(e.title, f_title, rw - 90)
        d.text((rx + 90, y - 1), title, font=f_title, fill=INK)
        y += line_h

    # ---- footer ----
    foot = "updated " + updated.strftime("%H:%M") + ("  ·  stale" if stale else "")
    d.text((rx, H - 34), foot, font=f_foot, fill=FAINT)

    return img


def _compose_landscape(
    weather: Weather,
    agenda: list[Event],
    cfg: Config,
    updated: datetime,
    stale: bool = False,
    news: list[dict] | None = None,
) -> Image.Image:
    news = news or []
    LW, LH = 800, 600
    col = 300  # weather column width
    img = Image.new("L", (LW, LH), 255)
    d = ImageDraw.Draw(img)

    f_label = _font(18)
    f_big = _font(92)
    f_hilo = _font(28)
    f_fc_day = _font(20)
    f_fc_hi = _font(22)
    f_sec = _font(24)
    f_time = _font(24)
    f_title = _font(26)
    f_div = _font(20)
    f_foot = _font(18)

    today = updated.date()
    pad = 22

    # ---- left weather column ----
    d.rectangle([0, 0, col, LH], fill=BAND)
    d.text((pad, 20), "NOW", font=f_label, fill=GRAY)
    _draw_glyph(d, weather_glyph(weather.code), col // 2, 96, 40)
    d.text((pad, 150), _fmt_temp(weather.temp_c, cfg.units), font=f_big, fill=INK)
    d.text((pad, 262), f"H {_fmt_temp(weather.hi_c, cfg.units)}   L {_fmt_temp(weather.lo_c, cfg.units)}", font=f_hilo, fill=GRAY)

    # hourly strip (next few hours)
    if weather.hourly:
        hy = 322
        d.text((pad, hy), "NEXT HOURS", font=f_label, fill=GRAY)
        f_hr, f_ht = _font(16), _font(19)
        n = len(weather.hourly)
        hw = (col - 2 * pad) // n
        for i, hr in enumerate(weather.hourly):
            cx = pad + hw * i + hw // 2
            d.text((cx, hy + 28), hr.label[:2], font=f_hr, fill=GRAY, anchor="ma")
            d.text((cx, hy + 50), _fmt_temp(hr.temp_c, cfg.units), font=f_ht, fill=INK, anchor="ma")

    fc_y = 452
    d.line([pad, fc_y - 18, col - pad, fc_y - 18], fill=FAINT, width=2)
    cell_w = (col - 2 * pad) // 3
    for i, day in enumerate(weather.forecast[:3]):
        cx = pad + cell_w * i + cell_w // 2
        d.text((cx, fc_y), day.day_abbr, font=f_fc_day, fill=GRAY, anchor="ma")
        _draw_glyph(d, weather_glyph(day.code), cx, fc_y + 50, 18)
        d.text((cx, fc_y + 84), _fmt_temp(day.hi_c, cfg.units), font=f_fc_hi, fill=INK, anchor="ma")

    # ---- right agenda column (wider, shorter) ----
    rx = col + 24
    rw = LW - rx - 20
    d.text((rx, 20), updated.strftime("%a %-d %b").upper(), font=f_sec, fill=INK)
    d.line([rx, 56, LW - 20, 56], fill=FAINT, width=2)

    y = 74
    line_h = 44
    # Leave room at the bottom of the right column for the headlines block.
    news = news[:3]
    max_rows = min(cfg.agenda_rows, 6 if news else 9)
    for kind, payload in select_rows(agenda, today, max_rows):
        if kind == "divider":
            y += 6
            d.text((rx, y), payload, font=f_div, fill=GRAY)
            d.line([rx, y + 24, LW - 20, y + 24], fill=FAINT, width=1)
            y += 34
            continue
        e: Event = payload
        if e.all_day:
            d.text((rx, y), "all-day", font=f_time, fill=FAINT)
        else:
            d.text((rx, y), e.start.strftime("%H:%M"), font=f_time, fill=GRAY)
        d.text((rx + 90, y - 1), truncate(e.title, f_title, rw - 90), font=f_title, fill=INK)
        y += line_h

    # ---- headlines block (bottom of the right column) ----
    if news:
        # Block height is a 34px header + 58px per story (30 title + 28 source).
        # Anchor so the last source line's descenders clear the 600px canvas,
        # but never ride up into the agenda (the y+12 floor).
        block_h = 34 + 58 * len(news)
        hy = max(y + 12, LH - 6 - block_h)
        _draw_headlines(d, news, rx, hy, rw, cfg.news_section,
                        (f_label, f_title, _font(18)))

    # footer moves to the bottom of the weather column so headlines own the right
    foot = "updated " + updated.strftime("%H:%M") + ("  ·  stale" if stale else "")
    d.text((pad, LH - 28), foot, font=f_foot, fill=FAINT)

    return img


def _sample():  # pragma: no cover - eyeball helper
    from datetime import timedelta

    from dashboard.weather import DayFc

    w = Weather(6.3, 0, 9.9, 3.2, [DayFc("Sun", 3, 7.1), DayFc("Mon", 3, 7.5), DayFc("Tue", 51, 4.8)])
    now = datetime(2026, 11, 21, 14, 32)
    tmrw = (now + timedelta(days=1)).date()
    ag = [
        Event(now.replace(hour=9, minute=30), False, "Standup", now.date()),
        Event(None, True, "Family Day", now.date()),
        Event(now.replace(hour=13), False, "Lunch with a very long title that must truncate", now.date()),
        Event(datetime(2026, 11, 22, 10, 0), False, "Flight BLR to DEL", tmrw),
    ]
    cfg = Config(lat=52.0, lon=4.3, units="C")
    render_dashboard(w, ag, cfg, now).save("/tmp/dashboard_sample.png")
    print("wrote /tmp/dashboard_sample.png")


if __name__ == "__main__":  # pragma: no cover
    _sample()
