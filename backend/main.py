import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import recipes
import storage
from pumps import PumpController, estimate_pour_seconds

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
    seconds: float | None = None
    ml: float | None = None


class AssignRequest(BaseModel):
    ingredient: str = ""


class CalibrateRequest(BaseModel):
    # Either set the rate directly, or provide a run time + measured output to derive it.
    ml_per_second: float | None = None
    seconds: float | None = None
    measured_ml: float | None = None


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


@app.get("/test")
def hardware_test():
    return FileResponse(os.path.join(FRONTEND, "test.html"))


@app.post("/api/pump/{pump_id}/run")
async def run_pump(pump_id: int, req: RunRequest):
    if not 1 <= pump_id <= 8:
        raise HTTPException(400, "Pump ID must be 1–8")
    if req.ml is not None:
        rate = storage.get_flow_rate(pump_id)
        seconds = req.ml / rate
    elif req.seconds is not None:
        seconds = req.seconds
    else:
        seconds = 3.0
    asyncio.create_task(controller.run(pump_id, seconds))
    return {"status": "ok", "pump": pump_id, "seconds": round(seconds, 2), "ml": req.ml}


@app.post("/api/stop")
def stop_all():
    controller.stop_all()
    return {"status": "stopped"}


@app.post("/api/pump/{pump_id}/calibrate")
def calibrate_pump(pump_id: int, req: CalibrateRequest):
    if not 1 <= pump_id <= 8:
        raise HTTPException(400, "Pump ID must be 1–8")
    if req.ml_per_second is not None:
        rate = req.ml_per_second
    elif req.seconds and req.measured_ml:
        rate = req.measured_ml / req.seconds
    else:
        raise HTTPException(400, "Provide ml_per_second, or seconds + measured_ml")
    if rate <= 0:
        raise HTTPException(400, "Flow rate must be positive")
    storage.set_flow_rate(pump_id, round(rate, 4))
    return {"status": "ok", "pump": pump_id, "ml_per_s": round(rate, 4)}


@app.post("/api/pump/{pump_id}/assign")
def assign_pump(pump_id: int, req: AssignRequest):
    if not 1 <= pump_id <= 8:
        raise HTTPException(400, "Pump ID must be 1–8")
    storage.set_assignment(pump_id, req.ingredient)
    return {"status": "ok", "pump": pump_id, "ingredient": req.ingredient.strip()}


@app.post("/api/pour/{drink_id}")
async def pour(drink_id: str):
    drink = next((d for d in recipes.all_recipes() if d["id"] == drink_id), None)
    if drink is None:
        raise HTTPException(404, "Unknown drink")
    if controller.is_busy():
        raise HTTPException(409, "Machine is busy")

    assignments = storage.get_assignments()
    rates = storage.get_flow_rates()
    name_to_pump = {
        name.strip().lower(): pid for pid, name in assignments.items() if name.strip()
    }

    steps = []
    for ing in drink["ingredients"]:
        pid = name_to_pump.get(ing["name"].strip().lower())
        if pid is None:
            raise HTTPException(400, f"No pump loaded with {ing['name']}")
        seconds = ing["ml"] / rates.get(pid, storage.DEFAULT_ML_PER_S)
        steps.append(
            {"pump": pid, "ingredient": ing["name"], "ml": ing["ml"], "seconds": round(seconds, 2)}
        )

    controller.begin_pour(drink["name"], steps)
    return {
        "status": "pouring",
        "drink": drink["name"],
        "steps": steps,
        "estimated_seconds": estimate_pour_seconds([s["seconds"] for s in steps]),
        "sequential_seconds": round(sum(s["seconds"] for s in steps), 1),
    }


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
    flow_rates = storage.get_flow_rates()
    return {
        "busy": controller.is_busy(),
        "pour": controller.pour_status,
        "pumps": {
            i: {
                "running": controller.is_running(i),
                "ingredient": assignments.get(i, ""),
                "ml_per_s": flow_rates.get(i, storage.DEFAULT_ML_PER_S),
            }
            for i in range(1, 9)
        }
    }
