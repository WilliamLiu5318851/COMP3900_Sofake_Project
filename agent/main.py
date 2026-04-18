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
    intra_cluster_p: float = 0.5
    inter_cluster_m: int = 2
    agents_per_cluster: int = 10
    weak_tie_p: float = 0.05
    simulations: int = 1


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        runs = []
        for i in range(max(1, req.simulations)):
            child_seed = (req.seed + i) if req.seed is not None else None
            run_log, signal_drift = run_simulation(
                n_agents=req.agent_count,
                n_steps=req.steps,
                seed=child_seed,
                out_dir="runs",
                ground_truth=req.ground_truth,
                intra_cluster_p=req.intra_cluster_p,
                inter_cluster_m=req.inter_cluster_m,
                agents_per_cluster=req.agents_per_cluster,
                weak_tie_p=req.weak_tie_p,
                run_identifier=f"run{i:02d}" if req.simulations > 1 else None,
            )
            runs.append({"run_log": run_log, "signal_drift": signal_drift})

        # backward-compat: expose first run at top level
        return {
            "run_log": runs[0]["run_log"],
            "signal_drift": runs[0]["signal_drift"],
            "runs": runs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
