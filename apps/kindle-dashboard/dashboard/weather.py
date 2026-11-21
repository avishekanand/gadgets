"""Fetch and parse weather from Open-Meteo (keyless). Temps kept in Celsius."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date

from dashboard.config import Config

API = "https://api.open-meteo.com/v1/forecast"
UA = {"User-Agent": "kindle-dashboard/0.1 (personal e-reader dashboard)"}


@dataclass
class DayFc:
    day_abbr: str
    code: int
    hi_c: float


@dataclass
class Weather:
    temp_c: float
    code: int
    hi_c: float
    lo_c: float
    forecast: list[DayFc]


def weather_glyph(code: int) -> str:
    """Map a WMO weather code to a glyph key."""
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "cloud"
    if code in (45, 48):
        return "fog"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if 95 <= code <= 99:
        return "storm"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    return "cloud"


def parse_weather(payload: dict) -> Weather:
    cur = payload["current"]
    daily = payload["daily"]
    times = daily["time"]
    fc: list[DayFc] = []
    for i in range(1, min(4, len(times))):
        d = date.fromisoformat(times[i])
        fc.append(DayFc(d.strftime("%a"), daily["weather_code"][i], daily["temperature_2m_max"][i]))
    return Weather(
        temp_c=cur["temperature_2m"],
        code=cur["weather_code"],
        hi_c=daily["temperature_2m_max"][0],
        lo_c=daily["temperature_2m_min"][0],
        forecast=fc,
    )


def fetch_weather(cfg: Config) -> Weather:
    params = {
        "latitude": cfg.lat,
        "longitude": cfg.lon,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": cfg.tz,
        "forecast_days": 4,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return parse_weather(json.loads(r.read()))
