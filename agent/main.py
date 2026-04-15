import os
import sys
import uuid
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from run import run_simulation

app = FastAPI(title="SoFake Agent Service")


class SimulateRequest(BaseModel):
    ground_truth: str
    news_id: int
    agent_count: int = 20
    topology: str = "random"
    steps: int = 7
    seed: int = 42
    role_mix: dict = {
        "spreader": 35,
        "commentator": 35,
        "verifier": 15,
        "bystander": 15,
    }


class SimulateResponse(BaseModel):
    run_log: dict
    signal_drift: dict
    db_run_id: int | None = None


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        run_log, signal_drift, db_run_id = run_simulation(
            n_agents=req.agent_count,
            n_steps=req.steps,
            seed=req.seed,
            out_dir="runs",
            ground_truth=req.ground_truth,
            news_id=req.news_id,
            db_path="news.db",
            save_to_db=True,
            topology=req.topology,
            role_mix=req.role_mix,
        )
        return SimulateResponse(run_log=run_log, signal_drift=signal_drift, db_run_id=db_run_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
