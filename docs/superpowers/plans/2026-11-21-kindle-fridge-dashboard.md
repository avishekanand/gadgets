# Kindle Fridge Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A battery-powered Kindle K4 on the fridge shows a greyscale weather + calendar dashboard, rendered on the always-on Mac and fetched by the Kindle every ~20 min.

**Architecture:** Thin client. A Python renderer on the Mac fetches weather (Open-Meteo, keyless) and calendar (private iCal URLs), draws a 600×800 greyscale PNG with Pillow, and writes it atomically into a directory served over the LAN by a tiny HTTP server. A scheduled job re-renders every N minutes and keeps the Mac awake. The Kindle runs a BusyBox loop that wakes on an RTC timer, joins Wi-Fi, fetches the PNG, paints it with `eips`, and deep-suspends again; the stock screensaver is suppressed so e-ink holds the image between refreshes.

**Tech Stack:** Python 3.9 (`from __future__ import annotations`), Pillow 10.4 (installed), `icalendar` + `recurring-ical-events` (pip, in a venv), stdlib `http.server`/`urllib`, macOS `launchd` + `caffeinate`, Kindle BusyBox sh + `eips` + RTC wakealarm.

**Spec:** `docs/superpowers/specs/2026-11-21-kindle-fridge-dashboard-design.md`

## Global Constraints

- Python files start with `from __future__ import annotations` (system python3 is 3.9.1).
- Screen is exactly **600×800, greyscale** (PNG mode `L`), portrait.
- Weather location: **Delft** (lat 52.0116, lon 4.3571), units **°C**.
- Calendars merged, sorted by start: primary `avishekanand@gmail.com` + Family `family01407447969389415336@group.calendar.google.com`, fetched via their **private iCal URLs** (no OAuth).
- Never send the user's email to third-party services; generic `User-Agent` on all outbound HTTP.
- Kindle refresh interval **~20 min** (configurable); must ride a true RTC deep-suspend cycle.
- Renderer must emit a **last-good** image on any fetch failure, never a blank/error screen.
- App lives in `apps/kindle-dashboard/`. Pin any pip dep to an exact version in `requirements.txt`.

## Review Focus

- **A weather or calendar fetch fails / times out** (no network, API down): the renderer keeps the last-good PNG and marks it stale, rather than crashing or blanking — covered in Task 5.
- **An all-day or multi-day event** (DTSTART is a date, not datetime): shown without a time, not dropped or crashed on — covered in Task 3.
- **A recurring event** (RRULE, e.g. weekly standup): appears on the correct day via `recurring-ical-events` expansion, not missing — covered in Task 3.
- **A thin day** (few/no events today): agenda spills into tomorrow with a divider rather than leaving the column empty — covered in Task 4.
- **Long event titles / many events** overflow the 600×800 column: titles truncate with an ellipsis and the list caps at the rows that fit, never drawing past the screen — covered in Task 4.

---

### Task 1: Scaffold + config

**Files:**
- Create: `apps/kindle-dashboard/dashboard/__init__.py`, `apps/kindle-dashboard/dashboard/config.py`
- Create: `apps/kindle-dashboard/config.example.toml`, `apps/kindle-dashboard/requirements.txt`, `apps/kindle-dashboard/README.md`
- Test: `apps/kindle-dashboard/tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str | None = None) -> Config`; `Config` dataclass with fields `lat: float`, `lon: float`, `units: str`, `calendars: list[str]` (iCal URLs), `refresh_min: int`, `server_host: str`, `server_port: int`, `out_dir: str`, `agenda_rows: int`, `tz: str`.

- [ ] **Step 1: Write the failing test** — `test_loads_defaults_and_overrides`: loading `config.example.toml` yields `units == "C"`, `lat == 52.0116`, `tz == "Europe/Amsterdam"`, `refresh_min == 20`, and `len(calendars) == 2`.
- [ ] **Step 2: Run it, verify it fails** (`ModuleNotFoundError`/`load_config` undefined).
- [ ] **Step 3: Implement `load_config` + `Config`** using stdlib `tomllib`? No — 3.9 has no `tomllib`; parse with a pinned `tomli` dep, or use JSON. Use **`tomli`** (pinned) for the config file. `config.example.toml` carries Delft coords, the two calendar placeholders, defaults above.
- [ ] **Step 4: Run test, verify pass.**
- [ ] **Step 5: Commit** (`feat(kindle-dashboard): config loader + scaffold`).

---

### Task 2: Weather (Open-Meteo)

**Files:**
- Create: `apps/kindle-dashboard/dashboard/weather.py`
- Test: `apps/kindle-dashboard/tests/test_weather.py` + `tests/fixtures/openmeteo_sample.json`

**Interfaces:**
- Consumes: `Config` (lat, lon, units).
- Produces: `fetch_weather(cfg: Config) -> Weather`; `Weather` dataclass: `temp_c: float`, `code: int` (WMO), `hi_c: float`, `lo_c: float`, `forecast: list[DayFc]` (3 items: `day_abbr: str`, `code: int`, `hi_c: float`); `parse_weather(payload: dict) -> Weather` (pure, testable without network); `weather_glyph(code: int) -> str` mapping WMO codes to an icon key.

- [ ] **Step 1: Write the failing test** — `test_parse_weather_fields` parses `openmeteo_sample.json` → asserts `temp_c`, today `hi_c`/`lo_c`, and `len(forecast) == 3` with the first day's `hi_c`. `test_glyph_maps_known_codes` asserts a clear/cloud/rain code each map to distinct keys.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** `parse_weather`, `weather_glyph`, then `fetch_weather` (urllib GET to Open-Meteo `forecast?latitude=&longitude=&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe/Amsterdam&forecast_days=4`, generic UA, then `parse_weather`). Save a real response as the fixture.
- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** (`feat(kindle-dashboard): Open-Meteo weather`).

---

### Task 3: Calendar (private iCal)

**Files:**
- Create: `apps/kindle-dashboard/dashboard/calendar.py`
- Test: `apps/kindle-dashboard/tests/test_calendar.py` + `tests/fixtures/sample.ics`

**Interfaces:**
- Consumes: `Config` (calendars, tz, agenda_rows).
- Produces: `fetch_agenda(cfg: Config, now: datetime) -> list[Event]`; `Event` dataclass: `start: datetime | None` (None ⇒ all-day), `all_day: bool`, `title: str`, `day: date`; `parse_ics(data: bytes, start: datetime, end: datetime, tz: str) -> list[Event]` (pure; expands recurrence).

- [ ] **Step 1: Write the failing test** — `sample.ics` contains a timed event today, an all-day event today, and a **weekly recurring** event. `test_parse_includes_recurring` asserts the recurring instance for today is present; `test_all_day_has_no_time` asserts the all-day event has `all_day is True` and `start is None`; `test_sorted_by_start` asserts ordering (all-day first or last — pick: all-day sorts to top of its day).
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** `parse_ics` with `icalendar` + `recurring-ical-events` over a window `[start, end]`; `fetch_agenda` fetches each URL (urllib, generic UA), parses over `now` → `now + 2 days`, merges, sorts by `(day, all_day desc, start)`. Pin `icalendar`, `recurring-ical-events`, `python-dateutil` in requirements.
- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** (`feat(kindle-dashboard): iCal agenda with recurrence`).

---

### Task 4: Render Layout C (Pillow)

**Files:**
- Create: `apps/kindle-dashboard/dashboard/render.py`
- Add: `apps/kindle-dashboard/assets/` (bundled TTF fonts + a small weather glyph set)
- Test: `apps/kindle-dashboard/tests/test_render.py`

**Interfaces:**
- Consumes: `Weather`, `list[Event]`, `Config`.
- Produces: `render_dashboard(weather: Weather, agenda: list[Event], cfg: Config, updated: datetime, stale: bool = False) -> PIL.Image.Image` (mode `L`, size 600×800); `truncate(text: str, font, max_px: int) -> str`.

- [ ] **Step 1: Write the failing test** — `test_image_size_and_mode` asserts output is mode `"L"`, size `(600, 800)`. `test_truncate_adds_ellipsis` asserts a too-long title is shortened with `…` and fits `max_px`. `test_agenda_spills_to_tomorrow` asserts that with one event today + events tomorrow, a "Tomorrow" divider label is drawn (assert via a returned layout/debug structure or by checking agenda slicing helper `select_rows(agenda, n)`).
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** Layout C: left ~42% weather column (glyph, big temp, hi/lo, 3-day forecast strip), right ~58% agenda (section label, rows of `HH:MM title`, all-day without time, "Tomorrow" divider on spill), footer `updated HH:MM` (+ "stale" marker when `stale`). Use bundled TTF; `truncate` by pixel width; cap rows to `agenda_rows`.
- [ ] **Step 4: Run, verify pass.** Also write a `__main__` that renders sample data to `/tmp` for eyeball check.
- [ ] **Step 5: Commit** (`feat(kindle-dashboard): Pillow Layout C renderer`).

---

### Task 5: Orchestrator, LAN server, scheduling

**Files:**
- Create: `apps/kindle-dashboard/dashboard/service.py` (render-once + serve), `apps/kindle-dashboard/dashboard/__main__.py`
- Create: `apps/kindle-dashboard/launchd/com.gadgets.kindledash.render.plist`, `.../com.gadgets.kindledash.serve.plist`, `apps/kindle-dashboard/scripts/install-mac.sh`
- Test: `apps/kindle-dashboard/tests/test_service.py`

**Interfaces:**
- Consumes: all of the above.
- Produces: `render_once(cfg: Config, now: datetime) -> Path` (gathers weather+agenda, renders, writes `out_dir/dashboard.png` atomically via temp+rename; on any fetch exception, re-renders from last-good inputs or re-stamps the existing PNG as stale and keeps serving); `serve(cfg: Config)` (stdlib `http.server` bound to `server_host:server_port`, serves `out_dir`).

- [ ] **Step 1: Write the failing test** — `test_render_once_writes_png` (mode L, 600×800 at `out_dir/dashboard.png`); `test_fetch_failure_keeps_last_good`: with a pre-existing PNG and weather fetch monkeypatched to raise, `render_once` still leaves a valid PNG and sets a stale marker (assert file mtime/stale sidecar), does not raise; `test_server_serves_png`: start `serve` on an ephemeral port, GET `/dashboard.png` → 200 + `image/png`.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** `render_once`, `serve`, `__main__` subcommands (`render`, `serve`). `install-mac.sh` loads both launchd jobs; the serve job runs under `caffeinate -s` (or a `caffeinate` plist) so the Mac does not system-sleep; render job runs every `refresh_min`. Use the Tailscale MagicDNS name as the documented host.
- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** (`feat(kindle-dashboard): orchestrator + LAN server + launchd`).

---

### Task 6: Kindle display + refresh loop (device)

**Files:**
- Create: `apps/kindle-dashboard/kindle/dashboard.sh`, `apps/kindle-dashboard/kindle/install-kindle.sh`
- Verify: on the physical Kindle (manual).

**Interfaces:**
- Consumes: the Mac server URL (`http://<mac-host>:<port>/dashboard.png`).

- [ ] **Step 1: Write `dashboard.sh`** (BusyBox sh): bring up Wi-Fi if down; `wget -O /tmp/dash.png <URL>`; validate it is a PNG and non-empty; `eips -g /tmp/dash.png` (full-screen 600×800 greyscale); set RTC wakealarm `refresh_min*60` seconds ahead (`/sys/class/rtc/rtc1/wakealarm`) and `echo mem > /sys/power/state`; on fetch failure, skip repaint (keep last image) and still schedule the next wake. Stage any file outside `documents/`.
- [ ] **Step 2: Deploy** via `install-kindle.sh` (scp over the existing `ssh kindle` alias) to `/mnt/us/extensions/` or `/mnt/us/dashboard/`.
- [ ] **Step 3: Manual verify** — run once over SSH: the fridge image appears via `eips`; confirm the device enters deep suspend (`powerd`/current draw) and wakes on the RTC alarm to repaint. Record the real per-cycle behavior.
- [ ] **Step 4: Commit** (`feat(kindle-dashboard): Kindle fetch+display+rtc loop`).

> Device-dependent: exact `eips` image flags, the RTC path (`rtc0` vs `rtc1`), and the suspend command are confirmed against the hardware in this task, with the owner driving the Kindle.

---

### Task 7: Screensaver suppression + boot autostart (device)

**Files:**
- Create: `apps/kindle-dashboard/kindle/suppress-screensaver.sh`, an upstart/KUAL autostart hook
- Verify: on the physical Kindle (manual).

- [ ] **Step 1: Suppress the stock screensaver** so the framework does not repaint over the dashboard on sleep (stop the relevant framework/powerd screensaver path — exact mechanism confirmed on-device; this is the pending "ScreenSavers hack" in the platform README).
- [ ] **Step 2: Auto-start on boot** — install a hook (upstart job in `/etc/upstart`, or a KUAL/`extensions` autostart) that launches `dashboard.sh` after boot, so charging → remount needs no SSH/KUAL.
- [ ] **Step 3: Manual verify** — reboot the Kindle; confirm the dashboard comes up on its own and the Amazon screensaver never reappears; confirm a charge cycle resumes cleanly.
- [ ] **Step 4: Commit** (`feat(kindle-dashboard): screensaver suppression + autostart`) and tick the platform README checklist.

---

## Notes for execution

- Tasks 1–5 are Mac-side and fully testable now; Task 2/3 need the user to paste the two **private iCal URLs** (Google Calendar → each calendar's Settings → "Secret address in iCal format") into `config.toml`, and real weather/calendar verification uses those.
- Tasks 6–7 require the **physical Kindle** on Wi-Fi and the owner driving it; their exact device commands are confirmed during those tasks.
- The owner will also confirm **which Mac** is the always-on host at Task 5 install time.
