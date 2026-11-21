# Platform: ESP32

Toolchain, board notes and bring‑up sketches for ESP32 boards. Apps that run on an ESP32
keep their firmware under `apps/<app>/esp32/` and build with the helper here.

## Toolchain (headless, via arduino‑cli)

```bash
brew install arduino-cli
arduino-cli config init
arduino-cli config add board_manager.additional_urls \
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32            # 3.3.12
arduino-cli lib install "DevLab_AudioTools@1.2.6" "DevLab_AudioDriver" "GFX Library for Arduino"
```

## `esp.sh` — build / flash / monitor

```bash
platforms/esp32/esp.sh build   <sketch_dir>
platforms/esp32/esp.sh flash   <sketch_dir>     # compile + upload
platforms/esp32/esp.sh monitor                  # serial @115200
platforms/esp32/esp.sh run     <sketch_dir>     # flash + monitor
platforms/esp32/esp.sh port                     # autodetect port (override with ESP_PORT)
```

Board settings are baked into `esp.sh` as this FQBN (ES3C35P):

```
esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,FlashSize=16M,\
PartitionScheme=app3M_fat9M_16MB,PSRAM=opi
```

## Board: LCDWIKI ES3C35P

| | |
|---|---|
| Board | LCDWIKI **ES3C35P** — 3.5" IPS ESP32‑S3 touchscreen |
| MCU | ESP32‑S3 (rev v0.2), dual‑core 240 MHz, **8 MB PSRAM**, **16 MB flash** |
| Display | **Sitronix ST77922**, 320×480 RGB565, QSPI @ 40 MHz |
| Touch | Integrated in ST77922, I²C **0x55** (not the address the vendor PDF prints) |
| Audio codec | **ES8311** @ I²C 0x18; mic in + speaker out; amp enable GPIO1 (active LOW) |
| Connectivity | 2.4 GHz Wi‑Fi, BLE; USB‑Serial/JTAG |

**Pin map** (ESP32‑S3 GPIO): LCD QSPI CS=10 SCK=12 D0=11 D1=13 D2=14 D3=9, backlight=41 ·
Touch/I²C SDA=38 SCL=39 INT=47 RST=48 · Audio I2S MCLK=17 BCLK=18 WS=21 DOUT=15 DIN=16 ·
Amp enable=1 (active LOW).

> ⚠️ The display panel reset is tied to chip power (no GPIO), so a software reboot does
> **not** reset the panel — a USB unplug/replug (cold power cycle) is sometimes needed.
> The USB‑Serial/JTAG can also wedge; the same cold power cycle recovers it.

- Keep the known‑good sketches as references; don't swap the ES8311 driver for a generic
  ES8388 config — this board is ES8311.

## Bring‑up sketches

```
sketches/
├── 00_Quiet/             # disable amp / idle
├── 04_Speaker_Tone/      # ES8311 DAC + speaker tone (known‑good audio baseline)
├── 05_Microphone_Record/ # ES8311 mic capture + amplitude meter
├── 06_WiFi_Connection/   # Wi‑Fi association test (copy wifi_secrets.h.example → wifi_secrets.h)
├── 10_Display_Test/      # ST77922 display + touch bring‑up (custom panel class)
├── 11_Touch_Probe/       # touch register reverse‑engineering probe
├── 12_WiFi_Scan/         # list visible networks (check SSID / 2.4 GHz band)
└── 13_WiFi_Connect_Test/ # join + print disconnect reason codes (wrong password vs. no AP)
```
