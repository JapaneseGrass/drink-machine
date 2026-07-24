# Drink Machine Project

## Overview
A smart drink dispensing machine controlled by a Raspberry Pi 4.
Users interact with the machine through a web app on their phone.
The Pi hosts both the backend API and the web app, and triggers
peristaltic pumps via relays to dispense drinks.

## User Experience Vision
1. The machine has 8 pumps, each connected to a bottle of liquid
   (spirits, mixers, juices, etc.)
2. The user opens the web app on their phone and assigns which
   bottle/ingredient is loaded at each pump (e.g., Pump 1 = Vodka,
   Pump 2 = Cranberry Juice)
3. Based on the available ingredients, the app automatically
   compiles a list of every drink the machine can currently make,
   pulled from a recipe database
4. The user browses the drink list, taps one, and presses pour —
   the machine dispenses it
5. The UI is the centerpiece: aesthetically pleasing, simple,
   fun, and memorable. This should feel like a delightful product,
   not a utility dashboard.

## Tech Stack
- Raspberry Pi 4
- Python + FastAPI + Uvicorn (backend API)
- gpiozero (GPIO/pump control)
- SQLite (drink recipes, ingredients, pump configuration)
- Web frontend (HTML/CSS/JavaScript) served by the Pi, accessed
  from any phone browser on the local network
- REST API over local WiFi

## Frontend Notes
- Phase 1: Served on local network only (user's phone connects
  to the Pi's IP/hostname)
- Phase 2 (maybe): Public deployment to a real domain
- Mobile-first design — primary device is a phone
- Design priorities: beautiful, simple, fun, memorable

## Hardware
- Red 8-channel **"High/Low Level Trigger"** relay module (SRD-12VDC relays)
- 8 peristaltic pumps (12V DC, Kamoer NKP, 3mm ID x 5mm OD tubing)
- 12V **5A** power supply
- Raspberry Pi 4 GPIO pins control the relay channels

### Relay configuration (important — this cost a long debugging session)
- The board's two `Low/Com/High` jumpers **must be set to `High`**, and
  `RELAY_ACTIVE_HIGH = True` in `backend/pumps.py` (drive pin HIGH = relay on).
- In **Low**-trigger mode the board's input is referenced to the 12V rail, so the
  Pi's 3.3V can never reach the "off" level and the relay sticks on. High-trigger
  is ground-referenced and works fine from 3.3V.
- A **common ground is mandatory**: a Pi GND pin → the board's `DC−`. Without it
  the GPIO signal has no reference and nothing switches.

### Wiring
- Relay board power: `DC+` / `DC−` from the **12V supply** (never from the Pi)
- Control: each `IN` → its GPIO, plus one shared Pi GND → `DC−`
- Pumps: 12V+ → relay `COM`, relay `NO` → pump (+), pump (−) → 12V−
- Pours are capped at **3 concurrent pumps** (`MAX_CONCURRENT_POURS`) to stay well
  inside the 5A budget, with staggered starts to spread motor inrush.

## GPIO Pin Mapping
Common ground: any Pi GND (e.g. physical pin 9) → relay `DC−`.

| Pump | Relay IN | GPIO (BCM) | Pi physical pin |
|------|----------|------------|-----------------|
| 1    | IN1      | 17         | 11              |
| 2    | IN2      | 18         | 12              |
| 3    | IN3      | 27         | 13              |
| 4    | IN4      | 22         | 15              |
| 5    | IN5      | 23         | 16              |
| 6    | IN6      | 24         | 18              |
| 7    | IN7      | 25         | 22              |
| 8    | IN8      | 4          | 7               |

## Project Structure
- /backend - Python FastAPI code (runs on Pi)
- /frontend - Web app (HTML/CSS/JS) served by the Pi

## Developer Notes
- All development via Remote SSH in VS Code on Mac
- SSH user: japanesegrass
- GitHub repo: https://github.com/JapaneseGrass/drink-machine

### SSH
- From any network (Tailscale — survives WiFi changes):
  `ssh japanesegrass@100.125.19.8`
- On the same local network: `ssh japanesegrass@AngelsRaspberryPi4.local`
- Pi running its own isolated hotspot (no internet): `ssh japanesegrass@10.42.0.1`

### Running the server
The app runs as a **systemd service that starts on boot** — do NOT launch uvicorn
by hand while it's running. Only one process can hold the GPIO pins, so a second
copy dies with `lgpio.error: 'GPIO busy'`.

- Reload after changing Python or `recipes.json`: `sudo systemctl restart drinkmachine`
- HTML/CSS changes need no restart — they're served from disk, just reload the page
- Status: `systemctl status drinkmachine` · Logs: `journalctl -u drinkmachine -f`
- To run it by hand, stop the service first:
  `sudo systemctl stop drinkmachine` then `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
  (hand it back afterwards with `sudo systemctl start drinkmachine`)

### App URLs
- Normal: http://AngelsRaspberryPi4.local:8000
- On the `DrinkMachine` hotspot: http://10.42.0.1:8000
- Pages: `/` (drinks) · `/setup` (pumps) · `/network` (WiFi) · `/test` (hardware, calibration, prime/rinse)

### Other
- Test pumps without the server: `cd backend && python pump_test.py`
- Install deps: `cd backend && pip install -r requirements.txt`

## Built
1. Pump configuration — assign ingredients to pumps (`/setup`, searchable combobox)
2. Recipe database — 31 drinks with ingredients, pour amounts (ml), glass art, history
3. "What can I make?" engine — matches loaded ingredients to recipes
4. Drink menu UI — 2-up tiles with SVG glass art, search, detail modal
5. Pour flow — ml → time via per-pump calibration, up to 3 pumps concurrently,
   longest-first (LPT) scheduling to minimize pour time
6. Status feedback — busy/pour state, live progress bar + time remaining
7. Per-pump calibration (`ml_per_s`) — calibrate each pump with its actual liquid,
   which captures both pump variance and viscosity
8. Size selector — Small / Regular / Large scales the whole recipe
9. Prime All / Rinse All (`/test`)
10. WiFi provisioning (`/network`) + hotspot fallback when no known network
11. Auto-start on boot (systemd `drinkmachine`)
12. Remote access from any network (Tailscale)

## Backlog / Ideas
- **Boot-state safety (TODO):** add `gpio=4,17,18,22,23,24,25,27=op,dl` to
  `/boot/firmware/config.txt` so pumps are held OFF during the power-on window
  before software takes over
- Drink queue — guests line up orders, machine pours in sequence
- Party stats — drinks poured, most popular, live leaderboard
- Bottle-level tracking — subtract each pour, warn when a bottle runs low
- Freestyle mode — build-your-own drink, save it to the menu
- QR code onboarding (join WiFi + open the app in one scan)
- PWA manifest so it installs to the home screen like a real app
- LED strip / sound for showpiece feedback
