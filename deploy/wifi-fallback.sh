#!/usr/bin/env bash
# On boot, if the Pi doesn't join a known WiFi network, raise the "DrinkMachine"
# setup hotspot so you can reach the app and configure the venue's WiFi from a
# phone (Network page). Once you connect to a real network, the hotspot drops.
set -u

AP_CONN="DrinkMachine"
WIFI_IFACE="wlan0"
SCAN_CACHE="/tmp/dm-wifi-scan.txt"

# Give NetworkManager time to auto-join a remembered network on boot.
sleep 25

state=$(nmcli -t -f DEVICE,STATE device status | awk -F: -v i="$WIFI_IFACE" '$1==i{print $2}')

if [ "$state" = "connected" ]; then
  # Already on a known network — nothing to do.
  exit 0
fi

# Cache a scan of nearby networks *before* switching to AP mode, since a single
# radio can't scan while hosting an access point. The Network page reads this.
nmcli -t -f SSID,SIGNAL,SECURITY device wifi list > "$SCAN_CACHE" 2>/dev/null || true

# No known network in range — bring up the setup hotspot.
nmcli connection up "$AP_CONN" || true
