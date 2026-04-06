import os
import random
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- 新增代码开始 ---
# 导入所需的类型提示，并从你的 run.py 引入封装好的核心引擎
from typing import List, Dict, Any
from run import run_simulation
# --- 新增代码结束 ---


app = FastAPI(title="SoFake Agent Service")


class SimulateRequest(BaseModel):
    ground_truth: str
    agent_count: int = 30
    steps: int = 60
    seed: int = 42
    role_mix: dict = {"spreader": 35, "commentator": 35, "verifier": 15, "bystander": 15}


# --- 修改代码开始 ---
# 契约更新：原本只返回 posts 和 summary，现在要严格匹配 Gardner 引擎返回的 "满汉全席" (run_log)
class SimulateResponse(BaseModel):
    run_id: str
    timestamp: str
    config: Dict[str, Any]
    agents: List[Dict[str, Any]]
    network: Dict[str, Any]
    ground_truth: Dict[str, Any]
    steps: List[Dict[str, Any]]
# --- 修改代码结束 ---

@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
 # --- 修改代码开始 ---
    # 【核心逻辑替换】：这里删除了原本 第33行及之后 的所有建人、建群、手写 for 循环的代码。
    # 那些逻辑已经被 Gardner 完美封装在 run.py 里了，我们直接当“包工头”呼叫它干活就行。

    # 定义本地存 log 文件的文件夹（与 run.py 需求保持一致）
    out_dir = "runs"
    os.makedirs(out_dir, exist_ok=True)

    # 呼叫 Gardner 的模拟引擎，把前端传进来的参数全喂给它
    log_data = run_simulation(
        n_agents=req.agent_count,
        n_steps=req.steps,
        seed=req.seed,
        out_dir=out_dir,
        ground_truth_text=req.ground_truth
    )

    # 引擎跑完后会 return 一个叫 run_log 的超级大字典，我们直接丢给前端
    return log_data
    # --- 修改代码结束 ---
