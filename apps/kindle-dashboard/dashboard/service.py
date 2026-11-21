"""Orchestrate a render and serve the PNG on the LAN.

render_once gathers weather + agenda, draws the image, and writes it
atomically. On any fetch failure it falls back to the last good inputs and
marks the image stale, so the fridge never shows a blank or error screen.
"""
from __future__ import annotations

import functools
import pickle
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dashboard.calendar import fetch_agenda
from dashboard.config import Config
from dashboard.render import render_dashboard
from dashboard.weather import fetch_weather

PNG_NAME = "dashboard.png"
CACHE_NAME = "last_good.pkl"


def render_once(cfg: Config, now: datetime) -> Path:
    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    png = out / PNG_NAME
    cache = out / CACHE_NAME

    try:
        weather = fetch_weather(cfg)
        agenda = fetch_agenda(cfg, now)
        cache.write_bytes(pickle.dumps((weather, agenda)))
        stale = False
    except Exception:
        if not cache.exists():
            raise  # no last-good to fall back to
        weather, agenda = pickle.loads(cache.read_bytes())
        stale = True

    img = render_dashboard(weather, agenda, cfg, now, stale=stale)
    tmp = out / (PNG_NAME + ".tmp")
    img.save(tmp, "PNG")
    tmp.replace(png)
    return png


def make_server(cfg: Config) -> ThreadingHTTPServer:
    directory = str(Path(cfg.out_dir).resolve())
    handler = functools.partial(SimpleHTTPRequestHandler, directory=directory)
    return ThreadingHTTPServer((cfg.server_host, cfg.server_port), handler)


def serve(cfg: Config) -> None:
    make_server(cfg).serve_forever()
