#!/bin/sh
# Kindle-side fridge dashboard loop (BusyBox sh, Kindle K4).
#
# Each cycle: bring Wi-Fi up, fetch the PNG the Mac renders, paint it with
# eips, then RTC-wake deep-suspend for REFRESH_MIN minutes. On a fetch
# failure it keeps the last image on screen (e-ink holds it for free) and
# still schedules the next wake.
#
# Config: /mnt/us/dashboard/dashboard.conf  (URL=... , REFRESH_MIN=...)
#
# NOTE: the three device specifics below (eips image flag, the rtc device,
# the suspend write) are confirmed against the hardware the first time this
# runs; adjust the marked lines if the Kindle disagrees.

CONF=/mnt/us/dashboard/dashboard.conf
[ -f "$CONF" ] && . "$CONF"
URL="${URL:-http://CHANGE-ME:8713/dashboard.png}"
REFRESH_MIN="${REFRESH_MIN:-20}"
STAGE=/tmp/dash.png            # /tmp is a tmpfs; never write into documents/
RTC=/sys/class/rtc/rtc1/wakealarm   # DEVICE-SPECIFIC: rtc1 on K4 (rtc0 is SoC)

log() { echo "$(date) $*" >> /mnt/us/dashboard/dashboard.log; }

wifi_up() {
    # DEVICE-SPECIFIC: enable radio via lab126 lipc, then wait for an IP.
    # NOTE: lipc talks to the framework (com.lab126.cmd). Keep the framework
    # running (suppress-screensaver.sh default) so this works; if you later
    # stop the framework, replace this with a wpa_cli/ifconfig path.
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    i=0
    while [ $i -lt 20 ]; do
        ifconfig wlan0 2>/dev/null | grep -q "inet addr" && return 0
        sleep 1; i=$((i+1))
    done
    return 1
}

paint() {
    # DEVICE-SPECIFIC: full-screen greyscale PNG. If eips rejects PNG on this
    # firmware, convert to PGM on the Mac side instead.
    eips -f -g "$STAGE" >/dev/null 2>&1
}

fetch_and_paint() {
    rm -f "$STAGE"   # BusyBox wget refuses to overwrite an existing file
    if wifi_up && wget -q -O "$STAGE" "$URL" && [ -s "$STAGE" ]; then
        paint
        log "painted from $URL"
    else
        log "fetch failed; keeping last image"
    fi
}

suspend() {
    T=$((REFRESH_MIN * 60))
    # The 2.6.31 rtc sysfs wants an ABSOLUTE epoch, not the rtcwake "+N" form
    # (which newer kernels accept). Compute now + T.
    NOW=$(cat /sys/class/rtc/rtc1/since_epoch 2>/dev/null || date +%s)
    echo 0 > "$RTC" 2>/dev/null              # clear any pending alarm
    echo $((NOW + T)) > "$RTC" 2>/dev/null   # absolute wake time
    log "suspend ${T}s (wake at $((NOW + T)))"
    echo mem > /sys/power/state 2>/dev/null   # DEVICE-SPECIFIC deep suspend
}

mkdir -p /mnt/us/dashboard
while true; do
    fetch_and_paint
    suspend
    sleep 2   # settle after wake before the next fetch
done
