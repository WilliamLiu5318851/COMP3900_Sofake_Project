import os
import random
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from run import run_simulation

app = FastAPI(title="SoFake Agent Service")


class SimulateRequest(BaseModel):
    ground_truth: str
    agent_count: int = 30
    steps: int = 60
    seed: int = 42
    role_mix: dict = {"spreader": 35, "commentator": 35, "verifier": 15, "bystander": 15}


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    log = run_simulation(
        n_agents=req.agent_count,
        n_steps=req.steps,
        seed=req.seed,
        out_dir="runs"
    )

    return {
        "log": log
    }
