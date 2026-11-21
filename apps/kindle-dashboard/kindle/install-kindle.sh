#!/bin/bash
# Deploy the dashboard loop to the Kindle over the existing `ssh kindle` alias.
# Run from the Mac. Copies the scripts, installs a boot autostart hook, and
# (optionally) starts the loop. Does NOT reboot the Kindle.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${1:-kindle}"
DEST=/mnt/us/dashboard

echo "Deploying to $HOST:$DEST ..."
ssh "$HOST" "mkdir -p $DEST"
scp "$HERE/dashboard.sh" "$HERE/suppress-screensaver.sh" "$HOST:$DEST/"
ssh "$HOST" "chmod +x $DEST/dashboard.sh $DEST/suppress-screensaver.sh"

# Seed the config if none exists yet.
ssh "$HOST" "[ -f $DEST/dashboard.conf ]" || {
  echo "No dashboard.conf on the Kindle yet — copy kindle/dashboard.conf.example to"
  echo "$DEST/dashboard.conf and set URL before starting."
}

# Autostart on boot via KUAL's startup hook directory.
# DEVICE-SPECIFIC: confirm the autostart path on this firmware (Task 7).
ssh "$HOST" "cat > /mnt/us/extensions/dashboard-autostart.sh" <<'HOOK'
#!/bin/sh
# Launched at boot; starts the dashboard loop if not already running.
pgrep -f /mnt/us/dashboard/dashboard.sh >/dev/null 2>&1 && exit 0
/mnt/us/dashboard/suppress-screensaver.sh
/mnt/us/dashboard/dashboard.sh &
HOOK
ssh "$HOST" "chmod +x /mnt/us/extensions/dashboard-autostart.sh"

echo "Deployed. To start now:  ssh $HOST '$DEST/suppress-screensaver.sh; nohup $DEST/dashboard.sh >/dev/null 2>&1 &'"
echo "Autostart hook written; verify it fires on reboot (Task 7)."
