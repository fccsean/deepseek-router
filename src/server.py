"""Web API for prompt scoring and routing."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from fastapi import FastAPI
from pydantic import BaseModel

from inference import PromptScorer

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

app = FastAPI(title="Prompt Scorer API", version="1.0.0")

scorer = PromptScorer(str(MODELS_DIR))


class ScoreRequest(BaseModel):
    prompt: str


class ScoreResponse(BaseModel):
    score: int
    model: str  # "deepseek-v4-pro" or "deepseek-v4-flash"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score_prompt(req: ScoreRequest):
    s = scorer.score(req.prompt)
    m = "deepseek-v4-pro" if scorer.is_pro(req.prompt) else "deepseek-v4-flash"
    return ScoreResponse(score=s, model=m)
