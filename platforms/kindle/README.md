# Platform: Kindle (e‑ink)

A non‑touch Kindle 4 / Kindle (5th gen, 2012) — 5‑way pad, no touch, no keyboard —
on **firmware 4.1.3 (build 2692310002)**, 2 GB (1.4 GB user storage), 600×800 e‑ink.
Used as a jailbroken e‑ink display/app target. Apps keep their Kindle side under
`apps/<app>/kindle/`.

## Status

- [x] Identify model + firmware
- [x] Jailbreak — [NiLuJe K4 jailbreak](https://kindlemodding.org/jailbreaking/Legacy/K4-Jailbreak/)
      (`data.tar.gz` + `ENABLE_DIAGS` + `diagnostic_logs/` → diags → D → R → Q)
- [x] OTA updates blocked — empty folder `update.bin.tmp.partial` in the USB root
- [x] KUAL (`documents/KUAL-KDK-1.0.azw2`, legacy K4 build) + MRPI 1.7.N
      (`extensions/MRInstaller`, `mrpackages/`)
- [x] KOReader (`koreader-kindle` package — the one for K4/KT/PW1) via KUAL
- [x] SSH over Wi‑Fi — KOReader's dropbear on :2222, key‑only
      (`koreader/settings/SSH/authorized_keys`; Mac side: `ssh kindle`, key `~/.ssh/kindle_ed25519`).
      KOReader → Network → SSH server, with "start with KOReader" ticked.
      `kual/gadgets-ssh/` is a KUAL extension that starts the same server without KOReader
      (copy it to `extensions/` on the Kindle).
- [ ] ScreenSavers hack

Hotfix: not used — the universal hotfix targets K5+; the K4 jailbreak persists on its own
as long as OTA updates stay blocked.

Gotchas: if the SSH toggle gets stuck on "shutting down", exit and restart KOReader.
The library only picked up KUAL after a restart (Menu → Settings → Menu →
Restart). Don't enter USB drive mode while KOReader is running. The USB link dropped once
mid‑copy — use `rsync` (resumable) for large copies.

> Keep the Kindle in **Airplane Mode** until the jailbreak is done and updates are blocked —
> an OTA update can patch the jailbreak, and firmware can't be downgraded without one.

## How apps work on this platform

The Kindle is a thin client: a Mac server does the rendering, the Kindle just shows images
and reports taps/buttons.

```
Mac server ──► renders a grayscale PNG at the panel size (600×800 on this K4)
     ▲                         │
     │ HTTP (taps / buttons)   ▼
Kindle: KUAL‑launched shell script — fetch PNG every N s, draw with `eips`
```

Constraints: ~0.5–1 s refresh with flashing on full refresh, 256–512 MB RAM, old ARM CPU,
2.4 GHz Wi‑Fi only, no modern browser. Design for glanceable, slowly‑changing screens.
