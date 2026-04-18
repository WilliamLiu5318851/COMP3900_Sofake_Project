import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.db import init_db
from services.news_service import create_news, list_news

AGENT_URL = os.getenv("AGENT_URL", "http://agent:8001")
FUSE_URL = os.getenv("FUSE_URL", "http://fuse:8002")

app = FastAPI()

init_db()

origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:80",
    "http://127.0.0.1:80",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewsCreate(BaseModel):
    content: str


class SimulateRequest(BaseModel):
    ground_truth: str
    agent_count: int = 30
    steps: int = 60
    seed: int = 42
    intra_cluster_p: float = 0.5
    inter_cluster_m: int = 2
    agents_per_cluster: int = 10
    weak_tie_p: float = 0.05
    simulations: int = 1


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/news")
def submit_news(news: NewsCreate):
    try:
        return create_news(news.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/news")
def get_news():
    return list_news()


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        with httpx.Client(timeout=600.0) as client:
            response = client.post(
                f"{AGENT_URL}/api/simulate",
                json=req.model_dump(),
            )
            response.raise_for_status()
            sim_result = response.json()

        # Extract evolved posts from run_log
        run_log = sim_result.get("run_log", {})

        # Build a lookup of post_id -> text (includes ground_truth)
        post_texts: dict = {"ground_truth": req.ground_truth}
        evolved_posts = []
        for step in run_log.get("steps", []):
            for event in step.get("events", []):
                text = event.get("new_post_text")
                if text:
                    pid = event.get("new_post_id")
                    post_texts[pid] = text
                    evolved_posts.append({
                        "post_id": pid,
                        "author": event.get("agent_name"),
                        "action": event.get("action"),
                        "step": step.get("step"),
                        "text": text,
                        "source_post_id": event.get("source_post_id"),
                    })

        # Sample up to 20 posts evenly to limit FUSE API calls
        MAX_FUSE_EVALS = 20
        if len(evolved_posts) > MAX_FUSE_EVALS:
            step_size = len(evolved_posts) // MAX_FUSE_EVALS
            sampled = evolved_posts[::step_size][:MAX_FUSE_EVALS]
        else:
            sampled = evolved_posts

        # Call FUSE to score each sampled post vs ground truth AND vs parent post
        fuse_evaluations = []
        with httpx.Client(timeout=60.0) as client:
            for post in sampled:
                entry = {**post}
                try:
                    # Score vs ground truth
                    gt_resp = client.post(
                        f"{FUSE_URL}/api/evaluate",
                        json={"original": req.ground_truth, "evolved": post["text"]},
                    )
                    if gt_resp.status_code == 200:
                        entry["fuse_scores_vs_ground_truth"] = gt_resp.json()

                    # Score vs parent post (if parent exists and isn't the ground truth itself)
                    parent_id = post.get("source_post_id")
                    parent_text = post_texts.get(parent_id) if parent_id else None
                    entry["parent_text"] = parent_text
                    if parent_text and parent_id != "ground_truth":
                        parent_resp = client.post(
                            f"{FUSE_URL}/api/evaluate",
                            json={"original": parent_text, "evolved": post["text"]},
                        )
                        if parent_resp.status_code == 200:
                            entry["fuse_scores_vs_parent"] = parent_resp.json()

                    if "fuse_scores_vs_ground_truth" in entry:
                        fuse_evaluations.append(entry)
                except Exception:
                    pass

        return {**sim_result, "fuse_evaluations": fuse_evaluations}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Agent service timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))