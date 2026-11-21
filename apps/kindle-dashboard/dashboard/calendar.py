"""Fetch Google 'Secret address in iCal format' URLs and build a merged agenda.

Recurrence (RRULE) is expanded with recurring-ical-events. Timed events are
converted to the config timezone; all-day events (DATE value) keep no time.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import icalendar
import recurring_ical_events
from dateutil import tz as dtz

from dashboard.config import Config

UA = {"User-Agent": "kindle-dashboard/0.1 (personal e-reader dashboard)"}


@dataclass
class Event:
    start: datetime | None  # None => all-day
    all_day: bool
    title: str
    day: date


def _sort_key(e: Event):
    # Within a day: all-day first (0), then timed by start time.
    return (e.day, 0 if e.all_day else 1, e.start.timetz() if e.start else None)


def parse_ics(data: bytes, start: datetime, end: datetime, tz: str) -> list[Event]:
    """Parse one iCal blob into Events within [start, end), recurrence expanded."""
    tzinfo = dtz.gettz(tz)
    cal = icalendar.Calendar.from_ical(data)
    out: list[Event] = []
    for comp in recurring_ical_events.of(cal).between(start, end):
        dt = comp["DTSTART"].dt
        title = " ".join(str(comp.get("SUMMARY", "")).split())
        if isinstance(dt, datetime):
            local = dt.astimezone(tzinfo) if dt.tzinfo else dt.replace(tzinfo=tzinfo)
            out.append(Event(start=local, all_day=False, title=title, day=local.date()))
        else:  # a date => all-day
            out.append(Event(start=None, all_day=True, title=title, day=dt))
    out.sort(key=_sort_key)
    return out


def fetch_agenda(cfg: Config, now: datetime) -> list[Event]:
    """Fetch every configured iCal URL and merge into one sorted agenda."""
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=2)
    events: list[Event] = []
    for url in cfg.calendars:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            events.extend(parse_ics(r.read(), start, end, cfg.tz))
    events.sort(key=_sort_key)
    return events
