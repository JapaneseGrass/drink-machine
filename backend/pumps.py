import asyncio
from gpiozero import OutputDevice

PUMP_PINS = {
    1: 17,
    2: 18,
    3: 27,
    4: 22,
    5: 23,
    6: 24,
    7: 25,
    8: 4,
}

# Most relay modules trigger on LOW; set True if yours triggers on HIGH
RELAY_ACTIVE_HIGH = False


class PumpController:
    def __init__(self):
        self._devices = {
            pump_id: OutputDevice(pin, active_high=RELAY_ACTIVE_HIGH, initial_value=False)
            for pump_id, pin in PUMP_PINS.items()
        }
        self._running: set[int] = set()

    def is_running(self, pump_id: int) -> bool:
        return pump_id in self._running

    def on(self, pump_id: int) -> None:
        self._devices[pump_id].on()

    def off(self, pump_id: int) -> None:
        self._devices[pump_id].off()
        self._running.discard(pump_id)

    async def run(self, pump_id: int, seconds: float) -> None:
        if pump_id not in self._devices:
            raise ValueError(f"Invalid pump ID: {pump_id}")
        if pump_id in self._running:
            return
        self._running.add(pump_id)
        try:
            self._devices[pump_id].on()
            await asyncio.sleep(seconds)
        finally:
            self._devices[pump_id].off()
            self._running.discard(pump_id)

    def stop_all(self) -> None:
        for dev in self._devices.values():
            dev.off()
        self._running.clear()

    def cleanup(self) -> None:
        self.stop_all()
        for dev in self._devices.values():
            dev.close()
