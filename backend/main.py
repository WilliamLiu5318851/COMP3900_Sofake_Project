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
    role_mix: dict = {"spreader": 35, "commentator": 35, "verifier": 15, "bystander": 15}


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
        evolved_posts = []
        for step in run_log.get("steps", []):
            for event in step.get("events", []):
                text = event.get("new_post_text")
                if text:
                    evolved_posts.append({
                        "post_id": event.get("new_post_id"),
                        "author": event.get("agent_name"),
                        "action": event.get("action"),
                        "step": step.get("step"),
                        "text": text,
                    })

        # Sample up to 20 posts evenly to limit FUSE API calls
        MAX_FUSE_EVALS = 20
        if len(evolved_posts) > MAX_FUSE_EVALS:
            step_size = len(evolved_posts) // MAX_FUSE_EVALS
            sampled = evolved_posts[::step_size][:MAX_FUSE_EVALS]
        else:
            sampled = evolved_posts

        # Call FUSE to score each sampled post against the ground truth
        fuse_evaluations = []
        with httpx.Client(timeout=60.0) as client:
            for post in sampled:
                try:
                    fuse_resp = client.post(
                        f"{FUSE_URL}/api/evaluate",
                        json={"original": req.ground_truth, "evolved": post["text"]},
                    )
                    if fuse_resp.status_code == 200:
                        fuse_evaluations.append({**post, "fuse_scores": fuse_resp.json()})
                except Exception:
                    pass

        return {**sim_result, "fuse_evaluations": fuse_evaluations}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Agent service timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))