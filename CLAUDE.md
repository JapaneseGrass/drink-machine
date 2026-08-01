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
- 12V **10A** power supply
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
- Pours are capped at **6 concurrent pumps** (`MAX_CONCURRENT_POURS`) to stay well
  inside the 10A budget, with staggered starts to spread motor inrush.

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

## Current bottle loadout (Ugnar's Bar)
Chosen so the machine can pour Tokyo Teas, Adios Mfers, everything else those
ingredients reach, and straight shots — 23 drinks in all. Sprite, garnishes,
and salt rims are added by hand.

| Pump | Bottle |
|------|--------|
| 1 | Vodka |
| 2 | Gin |
| 3 | White Rum |
| 4 | Tequila |
| 5 | Midori |
| 6 | Sweet and Sour Mix |
| 7 | Blue Curacao |
| 8 | Lime Juice |

Ingredient names must match `recipes.json` exactly — the match is
case-insensitive but otherwise literal.

## Project Structure
- /backend - Python FastAPI code (runs on Pi)
- /frontend - Web app (HTML/CSS/JS) served by the Pi
  - `index.html` — drink menu, all three themes, host controls, swivel table
  - `styles.css` (base) · `birthday.css` (fiesta) · `desert.css` (Ugnar's Bar)
  - `fonts/` — self-hosted pixel fonts, so the theme survives the offline hotspot

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
- From any network (Tailscale): http://100.125.19.8:8000
- Pages: `/` (drinks) · `/setup` (pumps) · `/network` (WiFi) · `/test` (hardware, calibration, prime/rinse)
- The machine pages are reached through **Host Controls** on `/` — the `HOST`
  button in the bottom-right corner, which also holds the theme picker.

### Other
- Test pumps without the server: `cd backend && python pump_test.py`
- Install deps: `cd backend && pip install -r requirements.txt`

## Built
1. Pump configuration — assign ingredients to pumps (`/setup`, searchable combobox)
2. Recipe database — 54 drinks with ingredients, pour amounts (ml), glass art, history
3. "What can I make?" engine — matches loaded ingredients to recipes
4. Drink menu UI — 2-up tiles with SVG glass art, search, detail modal
5. Pour flow — ml → time via per-pump calibration, up to 6 pumps concurrently,
   longest-first (LPT) scheduling to minimize pour time
6. Status feedback — busy/pour state, live progress bar + time remaining
7. Per-pump calibration (`ml_per_s`) — calibrate each pump with its actual liquid,
   which captures both pump variance and viscosity
8. Strength selector — Regular / Light, where Light cuts the liquor only
9. Prime All / Rinse All (`/test`)
10. WiFi provisioning (`/network`) + hotspot fallback when no known network
11. Auto-start on boot (systemd `drinkmachine`)
12. Remote access from any network (Tailscale)
13. Party themes + host controls — see below
14. Potency meter — a 5-bar strength read-out under every drink name

## Themes
The front page wears one of three themes, picked in **Host Controls** (the
small `HOST` button, bottom-right of `/`):

| Key | What it is |
|-----|------------|
| `desert` | **Ugnar's Bar** — pixel desert ported from the party-invite repo |
| `fiesta` | Ivan's 28th — papel picado, confetti, El Paso sunset |
| `default` | Plain dark menu, no party dressing |

- The active theme lives **on the server** (`settings` table, `/api/theme`), not
  in each browser. The host picks it once and every phone already on the page
  follows within one status poll (~2s). This is the whole point — a per-browser
  toggle would only have changed the host's own screen.
- `?theme=desert|fiesta|default` forces a theme on **one** device without
  changing what anyone else sees (handy for a QR code). The old `?fiesta=1`
  still works.
- Copy for each theme is a single editable object at the top of the
  `<script>` in `frontend/index.html`: `PARTY` (fiesta) and `DESERT`.

### Ugnar's Bar (`frontend/desert.css`)
Matches https://github.com/JapaneseGrass/eremidis-party-invite — same palette,
same `Press Start 2P` / `VT323` pixel fonts, same crescent moon, same CRT
scanlines.
- The menu is a **swivel table**: one glass front and centre with its name
  right underneath, the rest receding upward into the background. Swipe, drag,
  arrow-tap, or arrow-key to spin; tap the front glass for the recipe and the
  pour button. Cards are placed on an ellipse from a *fractional* index
  (`swivelPos`), so a drag moves the table continuously and then snaps to the
  nearest seat. `(cos - 1)` rather than `cos` in the y term is what keeps the
  front seat dead centre.
- The front seat is **twice** the size of anything else — full size at centre,
  ~47% one seat out, tapering to ~31% at the back. That takes *two* curves,
  not one: `depth = cos(angle) ^ SWIVEL_FALLOFF` is the general falling-away
  into the distance, and `bump` is a smoothstepped bell one seat wide that
  lifts only whatever is at the front. A single exponent steep enough to double
  the front glass collapses every back seat onto the floor value, and puts all
  the growth in the last few pixels of a drag — which reads as a glitch rather
  than a glass arriving. With the bell, the two glasses either side of centre
  trade it smoothly, so the table still moves continuously under a finger.
- **The front glass grows out of its own box**, so `.swivel` is sized as
  `--card-h * 1.16` and never allowed to flex-shrink. The caption then butts
  straight up against it with no negative margin. Raise `SWIVEL_SCALE_FRONT`
  and that 1.16 has to come up with it, or the drink's name ends up underneath
  the glass — which is exactly what a 1.0 → 1.06 change did once already.
- Every seat the table passes fires a **detent** (`detent()`): a short
  `navigator.vibrate` *and* a 140 ms stepped twitch of the caption. The buzz is
  the bonus half — iPadOS Safari has no vibration API at all, and the party
  runs on an iPad — so the visual snap is what actually has to sell the click.
- Each glass **wobbles in zero gravity**. That animation lives on an inner
  `.swivel-float`, never on `.swivel-card` — `layoutSwivel()` rewrites the
  card's own transform on every drag frame and would wipe it out.
- **Fonts are served from `frontend/fonts/`, not Google Fonts.** The Pi runs
  its own hotspot at the party with no internet, so a CDN link would silently
  fall back to a system font.

### Kiosk
The party runs off **one iPad parked next to the machine** — not guests'
phones. So the desert theme sizes its type for reading at arm's length,
disables text selection and the long-press callout, and never scrolls the
page. The server-side theme still works as described above; it's just that
one device is usually the only one watching.

### Glass art
`glassSVG()` picks one of two renderers by theme, both drawing into the same
200x260 box, so *proportion* has to carry the meaning — a shot is short, squat
and thick-based, a highball is nearly full height, a rocks glass is wide and
full of ice, and stemware stands on a foot. Garnishes are parsed out of the
recipe's own `garnish` string (`garnishArt()`), so a salted rim, lime wheel or
cherry appears wherever the recipe actually calls for one.

- `vectorGlassSVG()` — the original smooth art. Fiesta and the classic menu
  keep it; they're past parties.
- `pixelGlassSVG()` — **desert only.** Neon pixel art on a 50x65 grid of
  4-unit blocks (`PX_U`), fine enough to hold a taper and a rounded bowl but
  still visibly pixel art. 4 is as fine as it goes: the divisors of both 200
  and 260 are 1, 2, 4, 5, 10 and 20, and at 2 the glasses stop reading as
  pixel art at all. The `<svg>` viewBox is derived from `PX_N * PX_U`, so the
  art box can't drift out of step with the cell size. Each glass is a
  run-length list of row half-widths in cells (`PIXEL_GLASS`), all ending on
  row 61 so they stand on one table line — which is what lets a single
  `::after` light-pool position serve all five. Walls are `PX_WALL` cells and
  the rim and liquid surface `PX_RIM` rows, so the ink weight stays put across
  resolution changes. **No straws**: a straw is a thin diagonal, the one shape
  a pixel grid can't draw without looking like a rendering bug. No sparkles
  either — floating pixels around the glass pulled the eye off the drink.
- The neon glow is a **CSS `drop-shadow` on the `<svg>`**, not an SVG filter.
  The swivel table animates up to seven glasses at once on the iPad and the
  compositor handles drop-shadow far better than `feGaussianBlur`. The colour
  comes from `--neon` (set on both the `<svg>` and the card, since
  `.swivel-card::after` pools the same colour on the table underneath).

### Potency meter
Five bars under every drink name — swivel caption, modal, and the classic
menu's tiles. `recipes.potency()` works the level out **server-side** and ships
it on every recipe as `potency` (and `potency_light`, so the modal's Light
button can redraw with no round trip; `/api/drinks` also returns
`light_strength` so the button and the meter can't drift from the pump).

The level blends *how much* alcohol is in the glass (standard drinks, weighted
0.6) with *how concentrated* it is (ABV, weighted 0.4). Neither alone works: a
straight shot and a vodka cranberry carry the same ounce of vodka and only one
of them is a sipping drink. `POTENCY_BANDS` is tuned against this recipe book
rather than to round numbers — most of the menu is one-shot highballs, so those
land mid-scale at MEDIUM and a neat shot tops out at ROCKET FUEL. Retune the
bands if the book gains a lot of drinks. `ABV` is also where `SPIRITS` now
comes from, so the Light pour and the meter can't disagree about what counts
as liquor.

### Pour strength
The modal offers **Regular** and **Light** (there is no longer a Double).
Light sends `strength: 0.6` to `/api/pour/{id}`, which scales back *only the
alcoholic ingredients* — `recipes.SPIRITS` (derived from `recipes.ABV`)
decides which those are. The mixers
stay at full measure, so the drink comes out genuinely weaker rather than
merely smaller: a Blue Margarita goes 75 ml → 45 ml of liquor while keeping
all 45 ml of lime and sour mix. Uniformly shrinking the recipe (what `scale`
does) would have produced a smaller drink of identical strength, which is not
what "light" means to anyone holding one. `scale` still exists in the API for
overall size and is currently always 1.

## Recipes
`backend/recipes.json` is a flat list; each drink has `id`, `name`, `category`,
`glass` (`highball` · `rocks` · `margarita` · `coupe` · `shot`), `color`,
`ingredients[]`, `garnish`, `history`.

An ingredient may carry **`"manual": true`** — the splash of Sprite, the float
of cola. Those are topped up by hand at the glass, so they never reach a pump:
`recipes.pumped_ingredients()` filters them out of both the availability check
and the pour plan, and the UI shows them under "Finish it yourself". Without
this flag, any recipe calling for soda could never be marked makeable.

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
