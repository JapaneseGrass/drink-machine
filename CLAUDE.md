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
- 8 channel 12V relay module (JESSINIE, 12V, optocoupler isolated)
- 8 peristaltic pumps (12V DC, Kamoer NKP, 3mm ID x 5mm OD tubing)
- Raspberry Pi 4 GPIO pins control relay channels

## GPIO Pin Mapping (BCM numbering)
| Pump | GPIO |
|------|------|
| 1    | 17   |
| 2    | 18   |
| 3    | 27   |
| 4    | 22   |
| 5    | 23   |
| 6    | 24   |
| 7    | 25   |
| 8    | 4    |

## Project Structure
- /backend - Python FastAPI code (runs on Pi)
- /frontend - Web app (HTML/CSS/JS) served by the Pi

## Developer Notes
- All development via Remote SSH in VS Code on Mac
- Pi is accessible at 192.168.1.208
- SSH user: japanesegrass
- GitHub repo: https://github.com/JapaneseGrass/drink-machine
- Run server: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
- Test pumps without server: `cd backend && python pump_test.py`
- Install deps: `cd backend && pip install -r requirements.txt`

## Core Features To Build
1. Pump configuration screen — assign ingredients to pumps
2. Recipe database — drinks with ingredients + pour amounts (ml)
3. "What can I make?" engine — match available ingredients to recipes
4. Drink menu UI — browse and select from available drinks
5. Pour flow — trigger pumps with correct timing per ingredient
6. Status feedback — show pour progress, machine busy/ready state

test
