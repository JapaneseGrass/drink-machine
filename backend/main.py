import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import recipes
import storage
from pumps import PumpController

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
controller: PumpController


@asynccontextmanager
async def lifespan(app: FastAPI):
    global controller
    storage.init_db()
    controller = PumpController()
    yield
    controller.cleanup()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


class RunRequest(BaseModel):
    seconds: float = 3.0


class AssignRequest(BaseModel):
    ingredient: str = ""


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


@app.post("/api/pump/{pump_id}/assign")
def assign_pump(pump_id: int, req: AssignRequest):
    if not 1 <= pump_id <= 8:
        raise HTTPException(400, "Pump ID must be 1–8")
    storage.set_assignment(pump_id, req.ingredient)
    return {"status": "ok", "pump": pump_id, "ingredient": req.ingredient.strip()}


@app.get("/api/drinks")
def drinks(q: str = ""):
    results = recipes.search(q)
    return {"count": len(results), "drinks": results}


@app.get("/api/drinks/available")
def available_drinks():
    assigned = [v for v in storage.get_assignments().values() if v.strip()]
    makeable = [d for d in recipes.annotate_availability(assigned) if d["available"]]
    return {"count": len(makeable), "drinks": makeable}


@app.get("/api/ingredients")
def ingredients():
    return {"ingredients": recipes.ingredient_vocabulary()}


@app.get("/api/status")
def status():
    assignments = storage.get_assignments()
    return {
        "pumps": {
            i: {
                "running": controller.is_running(i),
                "ingredient": assignments.get(i, ""),
            }
            for i in range(1, 9)
        }
    }
