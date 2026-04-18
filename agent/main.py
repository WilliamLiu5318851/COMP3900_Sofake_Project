import os
import sys
import uuid
import random
import concurrent.futures
from typing import List

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


class SimulateResponse(BaseModel):
    run_log: dict
    signal_drift: dict


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}

# 2. 定义跑一次模拟的“打工人”函数
def run_single(index: int, req_dict: dict, api_keys: List[str]):
    # 轮询分配 API Key
    current_key = api_keys[index % len(api_keys)]
    os.environ["GROQ_API_KEY"] = current_key
    
    # 稍微错开 seed，保证每次模拟结果不一样
    child_seed = (req_dict['seed'] + index) if req_dict['seed'] is not None else None
    
    # 调用你写好的 run_simulation
    run_log, signal_drift = run_simulation(
        n_agents=req_dict['agent_count'],
        n_steps=req_dict['steps'],
        seed=child_seed,
        out_dir="runs",
        ground_truth=req_dict['ground_truth'],
        run_identifier=f"run{index:02d}", # 会生成 run00, run01 文件夹
        intra_cluster_p=req_dict['intra_cluster_p'],
        inter_cluster_m=req_dict['inter_cluster_m'],
        agents_per_cluster=req_dict['agents_per_cluster'],
        weak_tie_p=req_dict['weak_tie_p']
    )
    return run_log, signal_drift


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        # 1. 抓取环境里的所有 API Keys
        keys_str = os.getenv("GROQ_API_KEYS", "")
        if not keys_str:
            keys_str = os.getenv("GROQ_API_KEY", "")

        api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        if not api_keys:
            raise ValueError("No API Keys found in environment variables.")

        all_results = []

        req_dict = req.dict()

        # 2. 启动并发引擎！
        with concurrent.futures.ProcessPoolExecutor(max_workers=req.simulations) as executor:
            # 现在我们把 index, req_dict, api_keys 都作为参数传给外面的 run_single
            futures = [executor.submit(run_single, i, req_dict, api_keys) for i in range(req.simulations)]
            for future in concurrent.futures.as_completed(futures):
                all_results.append(future.result())

        # 3. 关键：为了不弄崩队友写好的前端，我们只取第一个跑完的结果返回去画图
        first_log, first_drift = all_results[0]
        
        return SimulateResponse(run_log=first_log, signal_drift=first_drift)

    except Exception as e:
        import traceback
        traceback.print_exc() # 在终端打印完整报错，方便你 debug
        raise HTTPException(status_code=500, detail=str(e))
