# Drink Machine Project

## Overview
A smart drink dispensing machine controlled by a Raspberry Pi 4.
Users select drinks via an iOS/iPadOS SwiftUI app, which sends
orders to the Pi over local WiFi. The Pi then triggers peristaltic
pumps via GPIO pins to dispense the correct ingredients.

## Tech Stack
- Raspberry Pi 4
- Python + FastAPI + Uvicorn (backend API)
- gpiozero (GPIO/pump control)
- SQLite (drink recipes and ingredients)
- SwiftUI (iOS/iPadOS frontend)
- REST API over local WiFi

## Hardware
- 8 channel 12V relay module (JESSINIE, 12V, optocoupler isolated)
- 8 peristaltic pumps (12V DC, Kamoer NKP, 3mm ID x 5mm OD tubing)
- Raspberry Pi 4 GPIO pins control relay channels

## Project Structure
- /backend - Python FastAPI code (runs on Pi)
- /ios - SwiftUI Xcode project

## Developer Notes
- Backend is developed via Remote SSH in VS Code
- iOS app is developed locally in Xcode on Mac
- Pi is accessible at 192.168.1.208
- SSH user: japanesegrass
- GitHub repo: https://github.com/JapaneseGrass/drink-machine