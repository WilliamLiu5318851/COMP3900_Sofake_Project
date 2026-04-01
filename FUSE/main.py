import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from evaluation.fuse_scorer import FUSEScoringSystem

app = FastAPI(title="FUSE Scoring Service")

_api_key = os.getenv("ANTHROPIC_API_KEY")
_scorer = FUSEScoringSystem(api_key=_api_key) if _api_key else None


class EvaluateRequest(BaseModel):
    original: str
    evolved: str


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy", "scorer_ready": _scorer is not None}


@app.post("/api/evaluate")
def evaluate(req: EvaluateRequest):
    if _scorer is None:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")
    result = _scorer.evaluate_news(req.original, req.evolved)
    if not result:
        raise HTTPException(status_code=500, detail="Evaluation failed")
    return result
