"""WiFi management via NetworkManager (nmcli).

Read-only queries (scan/status) run as the app user. Changing networks needs
root, so connect() uses `sudo -n nmcli ...` — see deploy/drinkmachine-sudoers.
"""
import os
import re
import subprocess

WIFI_IFACE = "wlan0"
SCAN_CACHE = "/tmp/dm-wifi-scan.txt"  # written by the boot fallback before AP mode


def _run(args, timeout=20):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))


def _split(line):
    # nmcli -t escapes ':' inside a field as '\:'
    return [f.replace("\\:", ":") for f in re.split(r"(?<!\\):", line)]


def _parse_list(text):
    seen = {}
    for line in text.splitlines():
        parts = _split(line)
        if len(parts) < 3 or not parts[0]:
            continue
        ssid, signal, security = parts[0], parts[1], parts[2]
        try:
            sig = int(signal)
        except ValueError:
            sig = 0
        if ssid not in seen or sig > seen[ssid]["signal"]:
            seen[ssid] = {
                "ssid": ssid,
                "signal": sig,
                "secured": security not in ("", "--"),
            }
    return sorted(seen.values(), key=lambda x: x["signal"], reverse=True)


def scan():
    """Nearby networks (best effort). May be empty while the Pi is in AP mode,
    in which case we fall back to the list cached at boot before the hotspot came up."""
    _run(["sudo", "-n", "nmcli", "device", "wifi", "rescan"])  # ok if it fails
    r = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
    nets = _parse_list(r.stdout)
    if not nets and os.path.exists(SCAN_CACHE):
        try:
            nets = _parse_list(open(SCAN_CACHE).read())
        except OSError:
            pass
    return nets


def status():
    r = _run(["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "device", "status"])
    connected, ssid = False, None
    for line in r.stdout.splitlines():
        parts = _split(line)
        if len(parts) >= 3 and parts[0] == WIFI_IFACE:
            connected = parts[1] == "connected"
            ssid = parts[2] if connected else None
    ip = None
    ipr = _run(["hostname", "-I"])
    if ipr.stdout.strip():
        ip = ipr.stdout.split()[0]
    return {"connected": connected, "ssid": ssid, "ip": ip}


def connect(ssid, password):
    """Join a WiFi network by building the profile explicitly.

    We set the security type ourselves (wpa-psk) rather than letting
    `nmcli device wifi connect` infer it from a scan, because a single-radio Pi
    can't scan while hosting the setup hotspot — which otherwise yields
    "802-11-wireless-security.key-mgmt: property is missing".

    Note: on success the Pi may switch networks and drop the very connection
    making this request, so callers shouldn't rely on a reply.
    """
    # Start clean so a stale/broken profile of the same name can't interfere.
    _run(["sudo", "-n", "nmcli", "connection", "delete", ssid])

    add = [
        "sudo", "-n", "nmcli", "connection", "add", "type", "wifi",
        "con-name", ssid, "ssid", ssid, "connection.autoconnect", "yes",
    ]
    if password:
        add += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    r = _run(add, timeout=30)
    if r.returncode != 0:
        return {"ok": False, "message": (r.stderr.strip() or r.stdout.strip())}

    up = _run(["sudo", "-n", "nmcli", "connection", "up", ssid], timeout=45)
    return {"ok": up.returncode == 0, "message": (up.stdout.strip() or up.stderr.strip())}
