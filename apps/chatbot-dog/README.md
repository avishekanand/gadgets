# 🐶 Chatbot Dog

A standalone, Wi-Fi voice chatbot on an ESP32‑S3 touchscreen board that talks to a local
AI "brain" running on a Mac (speech‑to‑text → LLM → text‑to‑speech), all on the LAN.

Tap a button on the touchscreen, talk, and a cheeky robot‑dog persona ("Pip") transcribes
what you said, thinks up a reply with a local LLM, and **speaks it back** through the
onboard speaker in a natural neural voice. The eventual enclosure is a small radio‑style
housing, possibly inside a crocheted dog.

### How it works

```
                ESP32‑S3 (device)                         Mac (local "brain")
   ┌─────────────────────────────────┐          ┌──────────────────────────────────┐
   │  mic ─▶ ES8311 ADC ─▶ I2S        │          │  /stt   whisper.cpp (base.en)     │
   │  touchscreen UI (ST77922, LVGL‑  │  Wi‑Fi   │  /chat  Ollama (qwen2.5:7b, "Pip")│
   │  free Arduino_GFX) push‑to‑talk  │ ───────▶ │  /tts   Kokoro neural TTS         │
   │  record PCM ─▶ HTTP POST ────────┼──────────┤         (say fallback)            │
   │  play reply ◀─ I2S ◀─ ES8311 DAC │ ◀─────── │  stt_server.py + kokoro_tts.py    │
   └─────────────────────────────────┘   audio   └──────────────────────────────────┘
```

State machine on the device:
`IDLE → RECORDING → UPLOADING(/stt) → THINKING(/chat) → SPEAKING(/tts) → RESULT`

### Hardware

Runs on the LCDWIKI **ES3C35P** (ESP32‑S3, ST77922 touch display, ES8311 audio). Board
specs, pin map, quirks and the bring‑up sketches live in
[`platforms/esp32/`](../../platforms/esp32/README.md).

---

## Layout

```
apps/chatbot-dog/
├── esp32/20_Chatbot_STT/     # ⭐ device firmware (Arduino sketch)
├── server/
│   ├── stt_server.py         # LAN‑facing server: /health /stt /chat /tts /converse
│   └── kokoro_tts.py         # localhost Kokoro neural‑TTS microservice
├── scripts/
│   ├── download_models.sh    # fetch whisper + Kokoro models (not stored in git)
│   └── run_servers.sh        # start the whole Mac "brain"
├── models/                   # model files (gitignored; see scripts/download_models.sh)
└── enclosure/                # 3D‑printable dog housing (OpenSCAD → STL)
```

---

## Setup

All commands below run from the **repo root**.

### Device

Install the ESP32 toolchain once — see [`platforms/esp32/`](../../platforms/esp32/README.md).

Wi‑Fi credentials: copy `apps/chatbot-dog/esp32/20_Chatbot_STT/wifi_secrets.h.example` →
`wifi_secrets.h` and fill in your 2.4 GHz SSID/password (gitignored). In
`20_Chatbot_STT.ino` set `SERVER_BASE` to your Mac's LAN IP.

```bash
platforms/esp32/esp.sh flash apps/chatbot-dog/esp32/20_Chatbot_STT   # compile + upload
platforms/esp32/esp.sh monitor                                       # serial @115200
```

### Server (the Mac "brain")

```bash
brew install whisper-cpp ollama
ollama pull qwen2.5:3b
apps/chatbot-dog/scripts/download_models.sh        # whisper + Kokoro model files

# Kokoro TTS venv
python3.12 -m venv apps/chatbot-dog/server/tts-venv
apps/chatbot-dog/server/tts-venv/bin/pip install kokoro-onnx soxr soundfile

# Start everything (whisper-server :8082, Kokoro :8081, gateway :8080):
apps/chatbot-dog/scripts/run_servers.sh
```

Three local services make up the brain:

| Service | Port | Runtime | Role |
|---|---|---|---|
| `whisper-server` | 8082 (loopback) | homebrew whisper‑cpp | STT, model resident on the GPU |
| `kokoro_tts.py` | 8081 (loopback) | `server/tts-venv` python | neural TTS, model warm |
| `stt_server.py` | 8080 (**LAN**) | Apple‑signed `/usr/bin/python3` | gateway: `/stt` `/chat` `/tts` `/converse` |

The device uses **`/converse`**, which streams the LLM sentence‑by‑sentence and returns
framed `[type][len][payload]` chunks (text + audio) so Pip starts speaking ~1.2–1.5 s after
you stop, and keeps talking while the rest generates.

> **macOS firewall gotcha:** the LAN‑facing server must run under Apple‑signed
> `/usr/bin/python3`. Homebrew Python is ad‑hoc signed and macOS silently resets its
> incoming LAN connections even when "allowed". The Kokoro service binds to localhost
> only (loopback is firewall‑exempt), so it can use the venv Python.

---

## Status

### ✅ Working
- All hardware verified: ES8311 codec, speaker (DAC), microphone (ADC), Wi‑Fi, ST77922
  display, capacitive touch.
- End‑to‑end voice chatbot: push‑to‑talk → transcription on screen → LLM reply → spoken
  reply through the speaker.
- Two‑panel touchscreen UI ("You:" / "Pip:"), mic‑reactive animation, scrollable replies.
- Local brain: whisper.cpp (STT), Ollama `qwen2.5:7b` with a funny "Pip" persona (LLM),
  Kokoro neural TTS (natural voice; `say` fallback).

### 🔭 Roadmap
- ✅ **Streaming** `/converse` (sentence‑chunked) — ~1.2–1.5 s to first audio.
- ✅ **Resident Whisper** (whisper‑server) — no per‑turn model reload.
- ✅ **24 kHz audio** end‑to‑end — full‑fidelity Kokoro playback (mic + speaker at 24 kHz).
- **LLM speedup (evaluating):** move the LLM to Apple **MLX** + a 3B model for faster
  first token vs the current warm Ollama `qwen2.5:7b`.
- **Later:** point the device at a dedicated home server; conversation memory; wake word;
  LVGL UI polish; the physical crocheted‑dog enclosure.

### Measured latencies (warm, localhost)
`/stt` ~0.2–0.4 s · `/chat` ~0.5–0.7 s (short reply) · `/tts` (Kokoro) RTF ~0.29.
Perceived latency today is dominated by waiting for the **full** LLM reply before speaking —
hence the streaming work above.

---

## Notes
- Keep the known‑good sketches as references; don't swap the ES8311 driver for a generic
  ES8388 config — this board is ES8311.
- The factory firmware backup (if taken) lives in a `backup/` folder and is gitignored.

🤖 Built with [Claude Code](https://claude.com/claude-code).
