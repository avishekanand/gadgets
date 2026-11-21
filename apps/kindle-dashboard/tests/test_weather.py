from __future__ import annotations

import json
from pathlib import Path

from dashboard.weather import parse_weather, weather_glyph

FIX = Path(__file__).resolve().parent / "fixtures" / "openmeteo_sample.json"


def test_parse_weather_fields():
    w = parse_weather(json.loads(FIX.read_text()))
    assert w.temp_c == 6.3
    assert w.code == 0
    assert w.hi_c == 9.9
    assert w.lo_c == 3.2
    assert len(w.forecast) == 3
    assert w.forecast[0].hi_c == 7.1
    assert w.forecast[0].code == 3
    assert len(w.forecast[0].day_abbr) == 3


def test_glyph_maps_known_codes():
    assert weather_glyph(0) == "clear"
    assert weather_glyph(3) == "cloud"
    assert weather_glyph(61) == "rain"
    assert weather_glyph(0) != weather_glyph(61)
