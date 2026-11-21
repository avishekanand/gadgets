"""Load the dashboard's TOML config into a typed Config object."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

import tomli


@dataclass
class Config:
    lat: float
    lon: float
    units: str = "C"
    tz: str = "Europe/Amsterdam"
    refresh_min: int = 20
    server_host: str = "0.0.0.0"
    server_port: int = 8713
    out_dir: str = "./out"
    agenda_rows: int = 8
    calendars: list[str] = field(default_factory=list)


def load_config(path: str | None = None) -> Config:
    """Read a TOML config file into a Config. Unknown keys are ignored."""
    if path is None:
        path = str(Path(__file__).resolve().parents[1] / "config.toml")
    data = tomli.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})
