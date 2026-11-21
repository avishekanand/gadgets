# Platform: Kindle (e‑ink)

A 2012 Kindle (Paperwhite 1st gen or Kindle 5th gen — to be confirmed) used as a
jailbroken e‑ink display/app target. Apps keep their Kindle side under
`apps/<app>/kindle/`.

## Status

- [ ] Identify model + firmware (Settings → Device Options → Device Info; serial prefix →
      [models table](https://kindlemodding.org/kindle-hacking/models-table.html))
- [ ] Jailbreak — pick via the [Jailbreak Wizard](https://kindlemodding.org/jailbreak-wizard.html)
- [ ] Post‑jailbreak: hotfix, update blocking, KUAL + MRPI
- [ ] USBNetwork / SSH access
- [ ] KOReader

> Keep the Kindle in **Airplane Mode** until the jailbreak is done and updates are blocked —
> an OTA update can patch the jailbreak, and firmware can't be downgraded without one.

## How apps work on this platform

The Kindle is a thin client: a Mac server does the rendering, the Kindle just shows images
and reports taps/buttons.

```
Mac server ──► renders a grayscale PNG at the panel size (e.g. 758×1024 on PW1)
     ▲                         │
     │ HTTP (taps / buttons)   ▼
Kindle: KUAL‑launched shell script — fetch PNG every N s, draw with `eips`
```

Constraints: ~0.5–1 s refresh with flashing on full refresh, 256–512 MB RAM, old ARM CPU,
2.4 GHz Wi‑Fi only, no modern browser. Design for glanceable, slowly‑changing screens.
