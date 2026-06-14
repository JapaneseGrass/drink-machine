import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pumps import PumpController

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
controller: PumpController


@asynccontextmanager
async def lifespan(app: FastAPI):
    global controller
    controller = PumpController()
    yield
    controller.cleanup()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


class RunRequest(BaseModel):
    seconds: float = 3.0


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


@app.post("/api/pump/{pump_id}/run")
async def run_pump(pump_id: int, req: RunRequest):
    if not 1 <= pump_id <= 8:
        raise HTTPException(400, "Pump ID must be 1–8")
    asyncio.create_task(controller.run(pump_id, req.seconds))
    return {"status": "ok", "pump": pump_id, "seconds": req.seconds}


@app.post("/api/stop")
def stop_all():
    controller.stop_all()
    return {"status": "stopped"}


@app.get("/api/status")
def status():
    return {
        "pumps": {
            i: {"running": controller.is_running(i)}
            for i in range(1, 9)
        }
    }
