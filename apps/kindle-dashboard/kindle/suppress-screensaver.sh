#!/bin/sh
# Stop the stock Kindle UI from repainting the Amazon screensaver over the
# dashboard on sleep. The e-ink panel holds the last image with no power, so
# once the framework is stopped the dashboard stays on screen between refreshes.
#
# DEVICE-SPECIFIC (confirmed in Task 7 on the K4): stopping the GUI framework
# is the heavy hammer; a lighter approach (disabling just the screensaver via
# lipc) is tried first and this is the fallback.

# Lighter method (default): ask powerd not to draw the screensaver, leaving
# the framework running. dashboard.sh's Wi-Fi enable (lipc) needs the
# framework, so this is the safe default — the two scripts don't fight.
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null || true

# Heavier fallback: stop the GUI framework so nothing repaints the panel.
# OFF by default: stopping the framework also kills the lipc Wi-Fi path in
# dashboard.sh, so only enable this (STOP_FRAMEWORK=1) together with a
# framework-independent Wi-Fi method (wpa_cli/ifconfig) in dashboard.sh.
if [ "${STOP_FRAMEWORK:-0}" = "1" ]; then
    stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null || true
fi
