import asyncio
import heapq

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

# How many pumps may run at once during a pour. Sized for a 12V 5A supply
# (~3 pumps + relay coils stays well under 5A). Bump cautiously after a
# voltage-sag test. Starts are staggered to avoid simultaneous motor inrush.
MAX_CONCURRENT_POURS = 3
POUR_START_STAGGER_S = 0.25


def estimate_pour_seconds(step_seconds: list[float], concurrency: int = MAX_CONCURRENT_POURS) -> float:
    """Estimate total pour time given the concurrency cap, using LPT scheduling.

    Equals the makespan: max(longest single pour, total work / lanes), roughly.
    """
    if not step_seconds:
        return 0.0
    lanes = [0.0] * max(1, concurrency)
    for d in sorted(step_seconds, reverse=True):
        free = heapq.heappop(lanes)          # the lane that frees up soonest
        heapq.heappush(lanes, free + d)      # assign this pour to it
    return round(max(lanes), 1)


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
        """Pour a drink, running up to MAX_CONCURRENT_POURS pumps at once.

        Each step: {pump, seconds, ml, ingredient}. Pump starts are staggered so
        their motor inrush currents don't all land at the same instant.
        """
        # Longest pours first (LPT scheduling) packs the short ones into the gaps
        # and minimizes total pour time under the concurrency cap.
        steps = sorted(steps, key=lambda s: s["seconds"], reverse=True)
        self._pour = {"drink": drink_name, "active": []}
        sem = asyncio.Semaphore(MAX_CONCURRENT_POURS)
        workers: list[asyncio.Task] = []

        async def worker(step: dict) -> None:
            async with sem:
                if self._pour is not None:
                    self._pour["active"].append(step["ingredient"])
                try:
                    await self.run(step["pump"], step["seconds"])
                finally:
                    if self._pour is not None and step["ingredient"] in self._pour["active"]:
                        self._pour["active"].remove(step["ingredient"])

        try:
            for step in steps:
                workers.append(asyncio.create_task(worker(step)))
                await asyncio.sleep(POUR_START_STAGGER_S)
            await asyncio.gather(*workers)
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()
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
