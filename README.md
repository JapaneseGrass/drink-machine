# Drink Machine

A smart drink dispensing machine on a Raspberry Pi 4. Guests pick drinks from a
web app on their phone; the Pi drives 8 peristaltic pumps through a relay board
to dispense the ingredients.

## Running the server

**You don't start it manually — it runs as a systemd service that launches on
boot.** Power on the Pi and the app is already serving on port 8000, with or
without a network.

```bash
systemctl status drinkmachine        # is it running?
sudo systemctl restart drinkmachine  # reload after changing code  <-- the one you'll use most
sudo systemctl stop drinkmachine
sudo systemctl start drinkmachine
journalctl -u drinkmachine -f        # live logs
```

> **Only one copy can run at a time.** The app holds the GPIO pins, so launching
> a second instance fails with `lgpio.error: 'GPIO busy'`.

### Editing code
Changes to `.html` / `.css` are served straight from disk — just reload the page.
Changes to **Python** (`main.py`, `pumps.py`, `recipes.json`, …) load at startup,
so they need a restart:

```bash
sudo systemctl restart drinkmachine
```

### Running by hand (development)
Only if you want the server in your terminal. Stop the service first so it
releases the GPIO and port 8000:

```bash
sudo systemctl stop drinkmachine
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
# Ctrl-C when done, then hand it back:
sudo systemctl start drinkmachine
```

## Opening the app

| Who | Address | Works when |
|---|---|---|
| **You** (device running Tailscale) | **`http://100.125.19.8:8000`** | **Any network, always** — even if your laptop and the Pi are on different WiFi |
| **Guests** (no Tailscale) | `http://AngelsRaspberryPi4.local:8000` | Their phone is on the **same WiFi as the Pi** |
| Pi on its own hotspot | `http://10.42.0.1:8000` | They've joined the `DrinkMachine` hotspot |

> ⚠️ `AngelsRaspberryPi4.local` and the LAN IP only resolve when **your device and
> the Pi are on the same network**. If the app won't load, that's almost always
> why — not a dead server. The Tailscale address sidesteps it entirely.

Check which WiFi the Pi is on:
```bash
iwgetid -r
```

On iPhone, Safari → **Share → Add to Home Screen** gives an app-like icon.

### Pages
- `/` — guest menu: browse drinks, pick a size, pour
- `/setup` — assign an ingredient to each pump
- `/network` — connect the Pi to a WiFi network (no terminal needed)
- `/test` — hardware test, per-pump calibration, Prime All / Rinse All

## Changing the Pi's WiFi

Easiest way: **from the app** — tap **Network** → enter the WiFi name + password
→ **Connect**.

If the Pi boots somewhere with no known network, it automatically raises its own
**DrinkMachine** hotspot — join that from your phone and use the **Network** page.
See [deploy/WIFI-SETUP.md](deploy/WIFI-SETUP.md).

### From SSH (moving the Pi to a different network)

Run [`deploy/wifi-switch.sh`](deploy/wifi-switch.sh) on the Pi, over an existing
SSH or console session. **Type the network name and password once** — it rescans,
checks the network is actually in range, clears any stale profile, and connects
in the background:

```bash
~/drink-machine/deploy/wifi-switch.sh "Network Name" "password"
```

Works for any target — home WiFi, a phone hotspot, a friend's network. It stops
with a clear message if the network isn't in range, rather than half-switching
you.

<details>
<summary>What it runs, if you'd rather do it by hand</summary>

```bash
# 1. Rescan and confirm the target network is actually visible
sudo nmcli device wifi rescan
sleep 3
sudo nmcli device wifi list | grep -i "SSID_NAME"

# 2. Delete any old/broken saved profile for that network
sudo nmcli connection delete "SSID_NAME" 2>/dev/null

# 3. Connect in the background so it survives the SSH session dropping
nohup sudo nmcli device wifi connect "SSID_NAME" password "WIFI_PASSWORD" > ~/wifi_switch.log 2>&1 &
disown
```
</details>

**Then:**
1. Wait ~15–20 s for the connection to complete.
2. Switch your own computer's WiFi to the same network — `.local` (mDNS) only
   resolves when both devices are on the same subnet.
3. Reconnect and check it landed:
   ```bash
   ssh japanesegrass@angelsraspberrypi4.local
   cat ~/wifi_switch.log
   nmcli device status
   ```

> You can skip step 2 entirely if you use the Tailscale address
> (`ssh japanesegrass@100.125.19.8`) — it reaches the Pi from any network, as
> long as the new network has internet.

**Why the `nohup` matters.** Running `nmcli device wifi connect` straight over
SSH is unreliable when you're switching *away* from the network your SSH session
is riding on: the moment `wlan0` drops the old network the session's TCP
connection dies, which can `SIGHUP` the `nmcli` process mid-negotiation and
leave the Pi on neither network. `nohup … &` plus `disown` lets the attempt run
to completion on the Pi whether or not your session survives.

**Gotchas**
- **`sudo` is required on the delete step** (the script does this for you).
  Without it the delete fails silently (`2>/dev/null` hides the reason) and
  leaves the broken profile in place, so the next connect dies with
  `802-11-wireless-security.key-mgmt: property is missing`.
- **iPhone Personal Hotspot stops broadcasting its SSID** once you leave the
  Personal Hotspot settings screen or the phone locks — even with the toggle
  still showing "on". Keep that screen open and the phone unlocked and nearby
  while you run the sequence, or the Pi never sees the network at all
  (`Error: No network with SSID 'X' found`).

## SSH (including from another network)

The Pi is on Tailscale, so you can reach it from **anywhere**, on any WiFi:

```bash
ssh japanesegrass@100.125.19.8        # Tailscale — works from any network
```

Point your VS Code Remote-SSH host's `HostName` at that address and remote
editing keeps working even when the Pi changes networks.

> Tailscale needs the Pi to have **internet**. If it's running its own isolated
> `DrinkMachine` hotspot, join that hotspot and use `ssh japanesegrass@10.42.0.1`.

## Troubleshooting

**The app won't load in my browser.**
First check whether it's a *server* problem or a *network* problem — usually it's
the network.

```bash
# 1. Is the server actually up?  (run on the Pi)
systemctl is-active drinkmachine                      # want: active
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000   # want: 200
```
If those look good, the server is fine and you simply can't *reach* it:
```bash
iwgetid -r        # which WiFi is the Pi on?
```
Are you on that same WiFi? If not, either join it, or just use the Tailscale
address `http://100.125.19.8:8000`, which works from any network.

**`lgpio.error: 'GPIO busy'` when I run uvicorn.**
Expected — the systemd service is already running the app and holding the GPIO
pins. You don't need to start anything. To run it by hand, stop the service first
(see *Running by hand* above).

**I changed the code but nothing happened.**
HTML/CSS serve from disk (just reload). Python and `recipes.json` load at startup:
```bash
sudo systemctl restart drinkmachine
```

## Layout

- `backend/` — FastAPI app, pump control (gpiozero), SQLite, recipes
- `frontend/` — the web app (HTML/CSS/JS)
- `deploy/` — systemd units, WiFi provisioning, install docs

Hardware wiring and GPIO pin mapping live in [CLAUDE.md](CLAUDE.md).
