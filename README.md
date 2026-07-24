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

1. **From the app:** tap **Network** → enter the WiFi name + password → **Connect**.
2. **From SSH:** `sudo nmcli device wifi connect "SSID" password "PASSWORD"`

If the Pi boots somewhere with no known network, it automatically raises its own
**DrinkMachine** hotspot — join that from your phone and use the **Network** page.
See [deploy/WIFI-SETUP.md](deploy/WIFI-SETUP.md).

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
