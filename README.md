# gadgets

Apps for small devices — microcontrollers, e‑ink readers, and whatever else is in the
drawer — usually paired with a server running on a Mac on the same LAN.

## Layout

```
.
├── platforms/            # one folder per hardware family: toolchain, board notes, bring‑up
│   ├── esp32/            #   arduino‑cli helper (esp.sh), ES3C35P board, test sketches
│   └── kindle/           #   jailbroken 2012 Kindle as an e‑ink display
└── apps/                 # one folder per app; subfolders per target it runs on
    └── chatbot-dog/      #   voice chatbot: esp32/ firmware + server/ Mac brain + enclosure/
```

**Conventions**

- `platforms/<platform>/` holds what is reusable across apps on that hardware: how to set
  up the toolchain, flash/deploy helpers, pin maps and quirks, bring‑up tests.
- `apps/<app>/` holds one app end to end. Device code goes in a subfolder named after the
  platform (`esp32/`, `kindle/`, …); the Mac side goes in `server/`; hardware like
  enclosures goes alongside. An app can target more than one platform.
- Secrets (`wifi_secrets.h`, `*.secret`) and large model files are gitignored.

## Apps

| App | Platforms | What it does |
|---|---|---|
| [chatbot-dog](apps/chatbot-dog/) | ESP32‑S3 + Mac | Push‑to‑talk voice chatbot "Pip" with local STT → LLM → TTS |

## Platforms

| Platform | Notes |
|---|---|
| [esp32](platforms/esp32/) | arduino‑cli toolchain, `esp.sh`, LCDWIKI ES3C35P board |
| [kindle](platforms/kindle/) | 2012 Kindle, jailbreak in progress |
