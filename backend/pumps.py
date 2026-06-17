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

# Red "High/Low Level Trigger" board with jumpers set to HIGH -> triggers on HIGH.
# (This board's input runs off the 12V rail, so it must be in High-trigger mode to
#  work from the Pi's 3.3V GPIO; in Low-trigger mode 3.3V can't reach the off level.)
RELAY_ACTIVE_HIGH = True


class PumpController:
    def __init__(self):
        self._devices = {
            pump_id: OutputDevice(pin, active_high=RELAY_ACTIVE_HIGH, initial_value=False)
            for pump_id, pin in PUMP_PINS.items()
        }
        self._running: set[int] = set()
        self._pour = None  # dict describing the in-progress pour, or None
        self._pour_task = None

    def is_running(self, pump_id: int) -> bool:
        return pump_id in self._running

    def is_busy(self) -> bool:
        return self._pour is not None or bool(self._running)

    @property
    def pour_status(self):
        return self._pour

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

    def begin_pour(self, drink_name: str, steps: list[dict]) -> None:
        """Kick off a pour as a tracked background task so it can be cancelled."""
        self._pour_task = asyncio.create_task(self._pour_sequence(drink_name, steps))

    async def _pour_sequence(self, drink_name: str, steps: list[dict]) -> None:
        """Run a drink's pumps one after another. Each step: {pump, seconds, ml, ingredient}."""
        self._pour = {"drink": drink_name, "current": None}
        try:
            for step in steps:
                self._pour["current"] = step["ingredient"]
                await self.run(step["pump"], step["seconds"])
        finally:
            self._pour = None

    def stop_all(self) -> None:
        if self._pour_task is not None and not self._pour_task.done():
            self._pour_task.cancel()
        self._pour_task = None
        self._pour = None
        for dev in self._devices.values():
            dev.off()
        self._running.clear()

    def cleanup(self) -> None:
        self.stop_all()
        for dev in self._devices.values():
            dev.close()
