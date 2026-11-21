# kindle-dashboard

A weather + calendar dashboard for a battery-powered, fridge-mounted Kindle K4.
The always-on Mac renders a 600×800 greyscale PNG and serves it on the LAN; the
Kindle wakes every ~20 min, fetches it, paints it with `eips`, and deep-suspends.

Platform: [kindle](../../platforms/kindle/). Design:
[spec](../../docs/superpowers/specs/2026-11-21-kindle-fridge-dashboard-design.md),
[plan](../../docs/superpowers/plans/2026-11-21-kindle-fridge-dashboard.md).

## Setup (Mac)

```bash
cd apps/kindle-dashboard
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp config.example.toml config.toml   # then fill in your two calendar iCal URLs
```

Calendar URLs come from Google Calendar → each calendar's **Settings → Integrate
calendar → "Secret address in iCal format"**. No OAuth or Google Cloud project needed.

## Config

See `config.example.toml`. Location defaults to Delft (°C); `refresh_min` sets the
Kindle refresh cadence; `calendars` is the list of iCal URLs, merged into one agenda.

## Layout

Layout C: weather column (now + 3-day forecast) beside a merged agenda, greyscale,
with an "updated HH:MM" footer. No clock.
