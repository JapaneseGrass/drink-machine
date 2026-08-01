#!/usr/bin/env bash
# Move the Pi to a different WiFi network, run from an SSH or console session
# on the Pi itself. Give it the SSID and password once:
#
#   ./deploy/wifi-switch.sh "Network Name" "password"
#
# The connect runs in the background on purpose: the moment wlan0 leaves the old
# network your SSH session dies, which can SIGHUP nmcli mid-negotiation and
# leave the Pi on neither network.
set -u

SSID="${1:-}"
PASSWORD="${2:-}"

if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: $0 \"SSID\" \"PASSWORD\""
  exit 1
fi

echo "=== Switching wlan0 to '$SSID' ==="

echo "[1/3] Rescanning..."
sudo nmcli device wifi rescan
sleep 3

if ! sudo nmcli device wifi list | grep -qi "$SSID"; then
  echo "WARNING: '$SSID' not found in scan results."
  echo "If this is an iPhone hotspot, make sure the Personal Hotspot"
  echo "screen is open and the phone is unlocked/nearby, then re-run."
  exit 1
fi

# sudo matters here: without it the delete fails silently and leaves a broken
# profile behind, and the next connect dies with "key-mgmt: property is missing".
echo "[2/3] Removing any old/broken saved profile for '$SSID'..."
sudo nmcli connection delete "$SSID" 2>/dev/null

echo "[3/3] Connecting in the background (survives SSH session drop)..."
nohup sudo nmcli device wifi connect "$SSID" password "$PASSWORD" > ~/wifi_switch.log 2>&1 &
disown

echo ""
echo "Connection attempt running in the background."
echo "Wait ~15-20 seconds, then reconnect via SSH and run:"
echo "  cat ~/wifi_switch.log"
echo "  nmcli device status"
