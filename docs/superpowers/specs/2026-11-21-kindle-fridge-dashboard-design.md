# Kindle Fridge Dashboard — Design

**Status:** draft for approval
**Date:** 2026-11-21
**Repo:** gadgets
**Platform:** `platforms/kindle/` (jailbroken Kindle K4)
**Likely app home:** `apps/kindle-dashboard/`

## Intent and why

The owner has a jailbroken Kindle K4 that would otherwise sit in a drawer. Mounted
on the kitchen fridge, it becomes an always-on, glanceable screen showing the
weather and the day's agenda — the information you want when you walk into the
kitchen, on a device that costs almost no power to keep showing it.

This is the first of two threads in a broader goal ("use my e-readers in a more
functional manner"): **dashboards** (this doc) and **reading on demand** (the
Boox / arXiv work, tracked separately). They are separate projects, built one at
a time. The agent-status panel discussed earlier is explicitly out of scope here;
if built later it becomes one more tile, not a redesign.

## The device and its constraints (fixed facts)

- **Kindle K4 non-touch**, FW 4.1.3, jailbroken; KUAL, MRPI, KOReader, SSH-over-Wi-Fi
  all working (see `platforms/kindle/README.md`).
- Screen: **600×800, greyscale e-ink, portrait.** No colour, no smooth animation.
  Content is painted with `eips`.
- **256 MB RAM**, BusyBox 1.7.2, kernel 2.6.31. Weak; cannot render a rich page itself.
- **Battery-powered on the fridge — no mains socket nearby.** This is the hard
  constraint. Every Wi-Fi wake costs power; the screen itself costs power only when
  it changes. So the device must spend most of its time asleep and refresh
  infrequently. Target: **refresh every ~20–30 min**, giving an estimated one to two
  weeks per charge. The owner takes it down to charge when low.
- Known gotcha from setup: **Wi-Fi drops when the Kindle sleeps** and must be
  re-joined on wake. The dashboard loop must bring Wi-Fi up itself, not assume it.

## Architecture: thin client, renderer on the always-on Mac

The Kindle is too weak and its browser too old to draw this well on-device, so it
does none of the drawing. The split:

- **Always-on Mac (the owner has one).** A scheduled job fetches weather and
  calendar, renders a single **600×800 greyscale PNG**, and serves it at a fixed
  URL on the home LAN. This reuses the gadgets Mac tooling (Python, already present).
  The Windows machine is not involved.
- **Kindle.** A small loop wakes on a timer, joins Wi-Fi, fetches the current PNG
  over the LAN, displays it with `eips`, and sleeps again.

Rendering on the Mac keeps all the smarts (API keys, layout, fonts, your real
calendar) in one place you can change, and keeps the Kindle side dumb and robust.
The ESP32 display and, later, other devices could consume the same renderer.

**Reachability:** because the Mac is always on, the PNG URL is always available when
the Kindle wakes. No cloud host needed. The service binds to the LAN; nothing is
exposed to the public internet.

**Tailscale** is installed on the Mac. The Kindle K4 is too old to run the Tailscale
client, so on the fridge it fetches the image over plain home Wi-Fi (LAN). But
Tailscale is still useful on the Mac side: a **stable MagicDNS name / Tailscale IP**
that survives LAN IP changes, and remote management/debugging of the renderer from
elsewhere. Builder may use the Tailscale name as the canonical host for the service
and, if convenient, as the fetch URL when the Kindle is on the same tailnet-served
LAN; it is not a dependency for the core fridge loop.

**The Mac must stay awake at the system level.** macOS sleeps by default, which would
stop both the scheduled render and the file server — producing the "blank/frozen
screen" anti-goal, nightly. So the build **includes configuring the always-on Mac to
prevent system sleep** (e.g. `caffeinate`/`pmset`, display may still sleep). Which
physical Mac this is must be confirmed at build start, along with permission to
install a scheduled job + LAN file server on it.

### Display during sleep — the linchpin

The device is asleep ~99% of the time, so what the screen holds *between* refreshes is
the whole product, not an afterthought. On a stock jailbroken K4 the OS paints its own
Amazon screensaver on sleep, which would overwrite the `eips`-painted dashboard — a
glance would show the dashboard for a second every 20 min and Amazon art the rest of
the time. **Decision: suppress the stock screensaver** (the "ScreenSavers hack" already
noted as pending in `platforms/kindle/README.md`) so that e-ink **retains the last
painted dashboard image through deep suspend with zero power**. The device then does a
**timed deep-suspend wake** (RTC-based) every ~20–30 min to refresh and sleeps again.
This is what simultaneously delivers the "always visible" goal and the 1–2-week battery
target; a bare KUAL loop that only `sleep`s may never enter deep suspend and could
drain in days (an explicit anti-goal). The exact wake mechanism (rtcwake-style timed
suspend vs. alternatives) remains the builder's to pick, but the screensaver must be
suppressed and the refresh must ride a true deep-suspend cycle.

### Must auto-resume after charging — no fiddling

The owner takes the Kindle down to charge when low, i.e. routine full power-off/on
cycles. **The dashboard loop must auto-start on boot** (init/upstart/KUAL-autostart
hook) so that after charging the owner simply puts it back on the fridge and it
resumes — no SSH, no KUAL re-launch. This serves the "no fiddling to recover"
anti-goal and is a firm requirement, not optional.

## The screen — Layout C (approved from mockups)

Two columns, portrait 600×800, greyscale:

- **Left column (~42%): weather for Delft, °C.**
  - Current: condition glyph, temperature, today's high/low.
  - **3-day forecast** strip at the bottom: day abbrev, glyph, high.
- **Right column (~58%): agenda.**
  - A single chronological list merging the owner's **primary calendar
    (avishekanand@gmail.com)** and the **Family** calendar.
  - Each entry: start time (24h, tabular) + title. Today's events; roll into
    tomorrow if the day is thin (builder's call on exact count that fits).
  - All-day events shown without a time.
- **Footer:** a small **"updated HH:MM"** line so a glance confirms the screen is
  live and not frozen. No live clock (e-ink can't tick, and a stale clock looks broken).

Mockup reference: the three-layout artifact shown during brainstorming; option C chosen.

## Data sources

- **Weather:** a free weather API keyed by Delft's coordinates, °C. Choice of
  provider (e.g. Open-Meteo, which needs no API key) is the builder's call; prefer
  one with no key and a clear licence. Current conditions + 3-day daily forecast.
- **Calendar:** Google Calendar. During the project the owner's account is reachable
  through the session's connector, but the **running service needs its own standing
  credential** (an owner-owned Google OAuth token with `calendar.readonly` scope on the
  Mac), since it runs unattended on a schedule. An owner OAuth token with that scope
  reads every calendar the owner is subscribed to, **including Family**, so the standing
  credential covers both without extra sharing steps. Setting that up is part of the
  build. Two calendars, merged and sorted by start time:
  - primary: `avishekanand@gmail.com`
  - Family: `family01407447969389415336@group.calendar.google.com`

## Goals

- At a glance from across the kitchen: today's weather and what's next.
- Runs unattended for 1–2 weeks per charge.
- Survives Wi-Fi drops, Mac reboots, and transient API failures without needing a touch.
- All configuration (city, which calendars, refresh interval) in one place on the Mac.

## Non-goals

- Not a clock, timer, or anything needing second/minute precision.
- Not interactive — the K4 non-touch has no touch; buttons are not used for dashboard
  navigation in v1.
- Not also the reading device while in dashboard mode (reading is the Boox).
- No colour, no photos, no animation.
- Not exposed to the public internet.

## Anti-goals (these would make it a failure even if it "works")

- A refresh rate that drains the battery in days, turning it into a chore.
- A blank or frozen screen when the Mac sleeps/reboots or an API hiccups, with no
  way to tell it is stale.
- Requiring the owner to SSH in or fiddle to recover after a Wi-Fi drop.
- Cluttering the small screen with all five calendars or dense text that can't be
  read from a step back.

## Constraints

- Greyscale 600×800; fonts and glyphs must be legible at a glance and render under
  `eips`.
- Battery budget dominates: minimise wake time and Wi-Fi-on time per cycle.
- BusyBox userland on the Kindle (limited `find`, `grep`, etc. — seen in setup).
- Writes into `documents/` on the Kindle can hit "Stale NFS file handle"; the image
  should be staged outside `documents/` and moved into place, consistent with the
  existing arxiv-to-kindle approach.
- Keep the owner's email out of third-party requests (generic User-Agent), per repo
  practice.

## Decided (builder may refine within these)

- Thin client; renderer on the always-on Mac; LAN-only PNG at a fixed URL.
- Layout C; Delft/°C; primary + Family calendars; "updated HH:MM" footer; no clock.
- Refresh ~20–30 min, tuned for battery life.
- Rendering in Python on the Mac (reuses existing tooling).

## Left to the builder

- **Render technology** on the Mac (e.g. HTML+headless-render to PNG, or Pillow/SVG
  → PNG). Pick what gives clean greyscale text at 600×800 with the least moving parts.
- **Weather provider** (prefer keyless, e.g. Open-Meteo) and the exact forecast fields.
- **How the renderer is scheduled and served** on the Mac (launchd/cron + a tiny
  static file server, or a small long-running process). Must be reachable on the LAN
  when the Kindle wakes.
- **The Kindle-side loop**: how it wakes on a timer with the screen asleep (e.g. an
  RTC/`rtcwake`-style wake vs. a KUAL-launched looping script that sleeps between
  cycles), brings up Wi-Fi, fetches, paints with `eips`, and handles failure
  (show last-good image + a small "stale since HH:MM" marker rather than blanking).
- **Exact refresh interval** and any quiet-hours (e.g. refresh less overnight) to
  save battery.
- **Number of agenda rows** that fit cleanly, and how far into tomorrow to spill.
- **Fonts/glyph set** for weather icons in greyscale.
- **Credential setup** for Google Calendar on the Mac (standing OAuth token), and
  where the config (city, calendar IDs, interval) lives.
- Where exactly the app lives in the repo (`apps/kindle-dashboard/` suggested) and
  how it shares code with `apps/arxiv-to-kindle/` (both talk to the Kindle over SSH).

## Open questions for the owner

A design review (builder-check) raised four points; all were resolvable without
changing what gets built, and are now folded into the sections above. Calls made
during that pass, for the owner to sanity-check while reading:

1. **Screensaver suppressed, e-ink holds the image through deep suspend** (not: push
   the dashboard as the Amazon screensaver). This is what makes it always-visible and
   long-lived on battery. See "Display during sleep."
2. **The always-on Mac will be configured to never system-sleep** as part of the build;
   which physical Mac, and access to install the job + server, confirmed at build start.
3. **The Kindle loop auto-starts on boot**, so charging and re-mounting needs no SSH or
   KUAL fiddling. Treated as a firm requirement.
4. **Family calendar is read via the owner's own OAuth token** (`calendar.readonly`),
   which already sees subscribed calendars; no separate sharing setup.

The only thing genuinely needing the owner at build time is **which Mac** is the
always-on host (point 2) — a setup detail, not a design change.
