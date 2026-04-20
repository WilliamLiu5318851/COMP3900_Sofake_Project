import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from run import run_simulation

app = FastAPI(title="SoFake Agent Service")


class SimulateRequest(BaseModel):
    ground_truth: str
    news_id: int
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

def run_single(index: int, req_dict: dict, api_keys: List[str]):
    # assign API Key
    current_key = api_keys[index % len(api_keys)]
    os.environ["GROQ_API_KEY"] = current_key
    
    #child_seed = (req_dict['seed'] + index) if req_dict['seed'] is not None else None
    child_seed = req_dict['seed']

    # Call run_simulation
    run_log, signal_drift = run_simulation(
        n_agents=req_dict['agent_count'],
        n_steps=req_dict['steps'],
        seed=child_seed,
        out_dir="runs",
        ground_truth=req_dict['ground_truth'],
        run_identifier=f"run{index:02d}", # generate run00, run01 files
        intra_cluster_p=req_dict['intra_cluster_p'],
        inter_cluster_m=req_dict['inter_cluster_m'],
        agents_per_cluster=req_dict['agents_per_cluster'],
        weak_tie_p=req_dict['weak_tie_p']
    )
    return run_log, signal_drift


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        # 1. take all API Keys from .evn
        keys_str = os.getenv("GROQ_API_KEYS", "")
        if not keys_str:
            keys_str = os.getenv("GROQ_API_KEY", "")

        api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        if not api_keys:
            raise ValueError("No API Keys found in environment variables.")

        all_results = []

        req_dict = req.dict()

        # 2. run simulations sequentially to avoid multiprocessing issues in Docker
        for i in range(req.simulations):
            all_results.append(run_single(i, req_dict, api_keys))

        # 3. return all runs; expose first run at top level for backward compat
        runs = [{"run_log": log, "signal_drift": drift} for log, drift in all_results]
        first_log, first_drift = all_results[0]

        return {
            "run_log": first_log,
            "signal_drift": first_drift,
            "runs": runs,
        }

    except Exception as e:
        import traceback
        traceback.print_exc() # debug in the terminal
        raise HTTPException(status_code=500, detail=str(e))
    
