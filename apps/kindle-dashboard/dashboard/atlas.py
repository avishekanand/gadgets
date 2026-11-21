"""Calendar agenda from the local Atlas app (repo: voice-email).

Atlas (http://127.0.0.1:8765) already indexes and merges every calendar with
recurrence expanded, so this is the preferred source: no iCal URLs to paste.
GET /api/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD[&mine=true] returns
{"events": [{title, start, end, all_day, calendar, ...}]}.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from dashboard.calendar import Event, _sort_key
from dashboard.config import Config

UA = {"User-Agent": "kindle-dashboard/0.1 (personal e-reader dashboard)"}


def parse_atlas(payload: dict, tz: str) -> list[Event]:
    from dateutil import tz as dtz

    tzinfo = dtz.gettz(tz)
    out: list[Event] = []
    for e in payload.get("events", []):
        title = " ".join(str(e.get("title", "")).split())
        if e.get("all_day"):
            d = date.fromisoformat(e["start"][:10])
            out.append(Event(start=None, all_day=True, title=title, day=d))
        else:
            dt = datetime.fromisoformat(e["start"])  # e.g. "2026-11-23T09:45" (naive, local)
            local = dt if dt.tzinfo else dt.replace(tzinfo=tzinfo)
            out.append(Event(start=local, all_day=False, title=title, day=local.date()))
    out.sort(key=_sort_key)
    return out


def fetch_atlas_agenda(cfg: Config, now: datetime) -> list[Event]:
    start = date(now.year, now.month, now.day)
    end = start + timedelta(days=2)
    params = {"start": start.isoformat(), "end": end.isoformat()}
    if cfg.atlas_mine:
        params["mine"] = "true"
    url = f"{cfg.atlas_url.rstrip('/')}/api/calendar?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        return parse_atlas(json.loads(r.read()), cfg.tz)
