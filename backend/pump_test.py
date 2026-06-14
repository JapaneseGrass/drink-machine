#!/usr/bin/env python3
"""Standalone wiring test — run directly on the Pi before starting the API."""
import time
import sys
from pumps import PumpController


def main():
    print("\nDrink Machine — Pump Test")
    print("=" * 32)
    print("  1-8   Run that pump for 2 seconds")
    print("  a     Run all pumps in sequence")
    print("  q     Quit")
    print()

    ctrl = PumpController()
    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "q":
                break
            elif cmd == "a":
                for i in range(1, 9):
                    print(f"  Pump {i}... ", end="", flush=True)
                    ctrl.on(i)
                    time.sleep(2)
                    ctrl.off(i)
                    time.sleep(0.3)
                    print("done")
            elif cmd.isdigit() and 1 <= int(cmd) <= 8:
                pump_id = int(cmd)
                print(f"  Running pump {pump_id} for 2 seconds...")
                ctrl.on(pump_id)
                time.sleep(2)
                ctrl.off(pump_id)
                print("  Done.")
            else:
                print("  Unknown command.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        ctrl.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    main()
