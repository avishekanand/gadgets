#!/bin/bash
# Install the Kindle dashboard as two LaunchAgents on the always-on Mac:
#   * serve  — runs the LAN image server under `caffeinate -s` (keeps the Mac
#              awake at the system level so it is always reachable)
#   * render — re-renders dashboard.png every refresh_min minutes
#
# Run from anywhere; it locates the app relative to this script. It does NOT
# touch the Kindle. Re-run to update. Use --uninstall to remove.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$APP_DIR/.venv/bin/python"
CFG="$APP_DIR/config.toml"
LA="$HOME/Library/LaunchAgents"
SERVE="com.gadgets.kindledash.serve"
RENDER="com.gadgets.kindledash.render"

uninstall() {
  for L in "$SERVE" "$RENDER"; do
    launchctl unload "$LA/$L.plist" 2>/dev/null || true
    rm -f "$LA/$L.plist"
  done
  echo "Uninstalled."
  exit 0
}
[ "${1:-}" = "--uninstall" ] && uninstall

[ -x "$PY" ] || { echo "venv missing: run 'python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt' in $APP_DIR"; exit 1; }
[ -f "$CFG" ] || { echo "config missing: cp $APP_DIR/config.example.toml $CFG and fill in your calendar URLs"; exit 1; }

# refresh interval (seconds) from config
INTERVAL=$("$PY" -c "from dashboard.config import load_config; print(load_config('$CFG').refresh_min*60)")
mkdir -p "$LA"

cat > "$LA/$SERVE.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$SERVE</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string><string>-s</string>
    <string>$PY</string><string>-m</string><string>dashboard</string>
    <string>serve</string><string>--config</string><string>$CFG</string>
  </array>
  <key>WorkingDirectory</key><string>$APP_DIR</string>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>$APP_DIR/out/serve.log</string>
  <key>StandardOutPath</key><string>$APP_DIR/out/serve.log</string>
</dict></plist>
EOF

cat > "$LA/$RENDER.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$RENDER</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string><string>-m</string><string>dashboard</string>
    <string>render</string><string>--config</string><string>$CFG</string>
  </array>
  <key>WorkingDirectory</key><string>$APP_DIR</string>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>$APP_DIR/out/render.log</string>
  <key>StandardOutPath</key><string>$APP_DIR/out/render.log</string>
</dict></plist>
EOF

mkdir -p "$APP_DIR/out"
for L in "$SERVE" "$RENDER"; do
  launchctl unload "$LA/$L.plist" 2>/dev/null || true
  launchctl load "$LA/$L.plist"
done

echo "Installed. Serving on port $("$PY" -c "from dashboard.config import load_config; print(load_config('$CFG').server_port)"), re-rendering every $((INTERVAL/60)) min."
echo "Image URL for the Kindle: http://<this-mac-host>:PORT/dashboard.png"
