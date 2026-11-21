#!/bin/sh
# Gadgets SSH — start/stop KOReader's dropbear on :2222 *without* KOReader running
# (so the Kindle can stay on its normal UI / a dashboard and still be reachable).
# Opens the firewall (INPUT policy is DROP) with plain ACCEPT rules.
# Writes diagnostics to /mnt/us/gadgets-ssh.log.
# Key-only auth: keys in /mnt/us/koreader/settings/SSH/authorized_keys.

PORT=2222
KO=/mnt/us/koreader
PID=/tmp/dropbear_koreader.pid
LOG=/mnt/us/gadgets-ssh.log

say() { eips 0 38 "                                                  " >/dev/null 2>&1; eips 0 38 "$1" >/dev/null 2>&1; }

diag() {
    echo "== $(date)"
    echo "-- wlan"; ifconfig wlan0 2>&1 | grep -E "inet |UP" ; ifconfig eth0 2>&1 | grep -E "inet "
    echo "-- kernel"; uname -r
    echo "-- dropbear"; ps 2>/dev/null | grep -v grep | grep dropbear || echo "not running"
    echo "-- conntrack match test"
    if iptables -A INPUT -p tcp --dport 65000 -m conntrack --ctstate NEW -j ACCEPT 2>&1; then
        echo "conntrack OK"; iptables -D INPUT -p tcp --dport 65000 -m conntrack --ctstate NEW -j ACCEPT
    else
        echo "conntrack NOT supported"
    fi
    echo "-- iptables"; iptables -L -n -v 2>&1
}

open_fw() {
    iptables -D INPUT  -p tcp --dport $PORT -j ACCEPT 2>/dev/null
    iptables -D OUTPUT -p tcp --sport $PORT -j ACCEPT 2>/dev/null
    iptables -I INPUT  -p tcp --dport $PORT -j ACCEPT
    iptables -I OUTPUT -p tcp --sport $PORT -j ACCEPT
}

close_fw() {
    iptables -D INPUT  -p tcp --dport $PORT -j ACCEPT 2>/dev/null
    iptables -D OUTPUT -p tcp --sport $PORT -j ACCEPT 2>/dev/null
}

running() { [ -f $PID ] && [ -d "/proc/$(cat $PID)" ]; }

start() {
    {
        echo "#### start"
        open_fw
        if running; then
            echo "dropbear already running (pid $(cat $PID))"
        else
            rm -f $PID
            (cd $KO && ./dropbear -E -R -s -p $PORT -P $PID) 2>&1
            sleep 1
        fi
        diag
    } >>$LOG 2>&1
    if running; then
        IP=$(ifconfig wlan0 2>/dev/null | sed -n 's/.*inet addr:\([0-9.]*\).*/\1/p')
        say "SSH on ${IP:-no-wifi}:$PORT"
    else
        say "SSH failed - see gadgets-ssh.log"
    fi
}

stop() {
    {
        echo "#### stop"
        running && kill "$(cat $PID)"
        sleep 1
        running && kill -9 "$(cat $PID)"
        rm -f $PID
        close_fw
    } >>$LOG 2>&1
    say "SSH stopped"
}

case "$1" in
    start) start ;;
    stop) stop ;;
    diag) diag >>$LOG 2>&1; say "Diagnostics written to gadgets-ssh.log" ;;
    *) echo "usage: $0 start|stop|diag" ;;
esac
