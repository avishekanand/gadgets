from __future__ import annotations

from pathlib import Path

from dashboard.config import load_config

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def test_loads_example_values():
    cfg = load_config(str(EXAMPLE))
    assert cfg.units == "C"
    assert cfg.lat == 52.0116
    assert cfg.tz == "Europe/Amsterdam"
    assert cfg.refresh_min == 20
    # The example uses Atlas as the calendar source (iCal URLs are the fallback).
    assert cfg.atlas_url == "http://127.0.0.1:8765"
    assert cfg.atlas_mine is True


def test_minimal_config_uses_defaults(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("lat = 1.0\nlon = 2.0\n")
    cfg = load_config(str(p))
    assert cfg.units == "C"
    assert cfg.refresh_min == 20
    assert cfg.calendars == []
