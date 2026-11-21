"""Orchestrate a render and serve the PNG on the LAN.

render_once gathers weather + agenda, draws the image, and writes it
atomically. On any fetch failure it falls back to the last good inputs,
marks the image stale, and keeps the footer timestamp at the last time the
data was actually current — so the fridge never shows a blank screen and
never masks staleness behind a fresh-looking time.

The LAN server exposes only /dashboard.png: the cache and logs that also
live in out_dir hold the parsed agenda and must not be reachable.
"""
from __future__ import annotations

import functools
import pickle
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dashboard.atlas import fetch_atlas_agenda
from dashboard.calendar import fetch_agenda
from dashboard.config import Config
from dashboard.news import fetch_headlines
from dashboard.render import render_dashboard
from dashboard.weather import fetch_weather

PNG_NAME = "dashboard.png"
CACHE_NAME = "last_good_v2.pkl"  # v2: the cached tuple now carries news headlines


def render_once(cfg: Config, now: datetime) -> Path:
    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    png = out / PNG_NAME
    cache = out / CACHE_NAME

    try:
        weather = fetch_weather(cfg)
        agenda = fetch_atlas_agenda(cfg, now) if cfg.atlas_url else fetch_agenda(cfg, now)
        try:
            # Headlines are optional: a feed outage must never blank the board.
            news = fetch_headlines(cfg.news, cfg.news_section, cfg.news_count)
        except Exception:
            news = []
        updated = now
        cache.write_bytes(pickle.dumps((weather, agenda, news, updated)))
        stale = False
    except Exception:
        if not cache.exists():
            raise  # no last-good to fall back to
        weather, agenda, news, updated = pickle.loads(cache.read_bytes())
        stale = True

    img = render_dashboard(weather, agenda, cfg, updated, stale=stale, news=news)
    tmp = out / (PNG_NAME + ".tmp")
    img.save(tmp, "PNG")
    tmp.replace(png)
    return png


class _ImageOnlyHandler(BaseHTTPRequestHandler):
    """Serve only GET /dashboard.png; 404 everything else, no listings."""

    def __init__(self, *args, out_dir: str, **kwargs):
        self._out_dir = out_dir
        super().__init__(*args, **kwargs)

    def do_GET(self):  # noqa: N802 (http.server API)
        if self.path != "/" + PNG_NAME:
            self.send_error(404)
            return
        png = Path(self._out_dir) / PNG_NAME
        if not png.exists():
            self.send_error(404)
            return
        data = png.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence default stderr logging
        pass


def make_server(cfg: Config) -> ThreadingHTTPServer:
    out_dir = str(Path(cfg.out_dir).resolve())
    handler = functools.partial(_ImageOnlyHandler, out_dir=out_dir)
    return ThreadingHTTPServer((cfg.server_host, cfg.server_port), handler)


def serve(cfg: Config) -> None:
    make_server(cfg).serve_forever()
