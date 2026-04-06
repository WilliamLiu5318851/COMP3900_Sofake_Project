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
    agent_count: int = 20
    steps: int = 7
    seed: int = 42


class SimulateResponse(BaseModel):
    run_log: dict
    signal_drift: dict


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    try:
        run_log, signal_drift = run_simulation(
            n_agents=req.agent_count,
            n_steps=req.steps,
            seed=req.seed,
            out_dir="runs",
            ground_truth=req.ground_truth,
        )
        return SimulateResponse(run_log=run_log, signal_drift=signal_drift)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
