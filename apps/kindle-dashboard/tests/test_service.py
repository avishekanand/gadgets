from __future__ import annotations

import socket
import threading
import urllib.error
import urllib.request
from datetime import datetime

from PIL import Image

import dashboard.service as svc
from dashboard.config import Config
from dashboard.weather import DayFc, Weather


def _weather():
    return Weather(6.3, 0, 9.9, 3.2, [DayFc("Sun", 3, 7.1), DayFc("Mon", 3, 7.5), DayFc("Tue", 51, 4.8)])


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _headlines(*_a, **_k):
    return [{"title": "Big news today", "source": "NPR", "summary": "", "url": "", "published": None}]


def test_render_once_writes_png(tmp_path, monkeypatch):
    cfg = Config(lat=1, lon=2, units="C", out_dir=str(tmp_path))
    monkeypatch.setattr(svc, "fetch_weather", lambda c: _weather())
    monkeypatch.setattr(svc, "fetch_agenda", lambda c, n: [])
    monkeypatch.setattr(svc, "fetch_headlines", _headlines)
    p = svc.render_once(cfg, datetime(2026, 11, 21, 14, 0))
    assert p.exists()
    img = Image.open(p)
    assert img.mode == "L"
    assert img.size == (600, 800)


def test_news_outage_does_not_blank_the_board(tmp_path, monkeypatch):
    cfg = Config(lat=1, lon=2, units="C", out_dir=str(tmp_path))
    monkeypatch.setattr(svc, "fetch_weather", lambda c: _weather())
    monkeypatch.setattr(svc, "fetch_agenda", lambda c, n: [])

    def all_feeds_down(*a, **k):
        raise RuntimeError("all news feeds failed")

    captured = {}
    real = svc.render_dashboard
    monkeypatch.setattr(svc, "fetch_headlines", all_feeds_down)
    monkeypatch.setattr(svc, "render_dashboard",
                        lambda *a, **k: captured.update(news=k.get("news"), stale=k.get("stale")) or real(*a, **k))
    p = svc.render_once(cfg, datetime(2026, 11, 21, 14, 0))
    assert p.exists()
    assert captured["news"] == []      # headlines dropped
    assert captured["stale"] is False  # but weather/agenda are fresh — not stale


def test_fetch_failure_keeps_last_good(tmp_path, monkeypatch):
    cfg = Config(lat=1, lon=2, units="C", out_dir=str(tmp_path))
    # First, a successful render to seed the last-good cache.
    monkeypatch.setattr(svc, "fetch_weather", lambda c: _weather())
    monkeypatch.setattr(svc, "fetch_agenda", lambda c, n: [])
    monkeypatch.setattr(svc, "fetch_headlines", _headlines)
    svc.render_once(cfg, datetime(2026, 11, 21, 14, 0))

    # Now the weather fetch fails; render_once must still produce a PNG, marked stale.
    def boom(c):
        raise RuntimeError("no network")

    captured = {}
    real_render = svc.render_dashboard

    def spy(weather, agenda, cfg_, updated, *a, **k):
        captured["stale"] = k.get("stale")
        captured["updated"] = updated
        return real_render(weather, agenda, cfg_, updated, *a, **k)

    monkeypatch.setattr(svc, "fetch_weather", boom)
    monkeypatch.setattr(svc, "render_dashboard", spy)
    p = svc.render_once(cfg, datetime(2026, 11, 21, 14, 20))
    assert p.exists()
    assert Image.open(p).size == (600, 800)
    assert captured["stale"] is True
    # The footer must show when the data was actually current (the seed time),
    # not the failing-refresh time, or staleness is masked.
    assert captured["updated"] == datetime(2026, 11, 21, 14, 0)


def test_server_rejects_non_image_paths(tmp_path):
    Image.new("L", (600, 800), 255).save(tmp_path / "dashboard.png")
    (tmp_path / "last_good.pkl").write_bytes(b"secret agenda")
    (tmp_path / "serve.log").write_text("logs")
    cfg = Config(lat=1, lon=2, out_dir=str(tmp_path), server_host="127.0.0.1", server_port=_free_port())
    httpd = svc.make_server(cfg)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{cfg.server_port}"
    try:
        for path in ("/last_good.pkl", "/serve.log", "/"):
            try:
                urllib.request.urlopen(base + path, timeout=5)
                raise AssertionError(f"{path} should not be served")
            except urllib.error.HTTPError as e:
                assert e.code == 404
        assert urllib.request.urlopen(base + "/dashboard.png", timeout=5).status == 200
    finally:
        httpd.shutdown()


def test_server_serves_png(tmp_path):
    Image.new("L", (600, 800), 255).save(tmp_path / "dashboard.png")
    cfg = Config(lat=1, lon=2, out_dir=str(tmp_path), server_host="127.0.0.1", server_port=_free_port())
    httpd = svc.make_server(cfg)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{cfg.server_port}/dashboard.png", timeout=5)
        assert r.status == 200
        assert r.headers.get_content_type() == "image/png"
    finally:
        httpd.shutdown()
