"""Inference interface for prompt scoring and routing."""

import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

import numpy as np
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier, XGBRegressor

from features import extract_text_features


ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


class PromptScorer:
    def __init__(self, models_dir: str = "models/"):
        base = Path(models_dir)
        self.scorer = XGBRegressor()
        self.scorer.load_model(str(base / "xgb_scorer.ubj"))
        self.router = XGBClassifier()
        self.router.load_model(str(base / "xgb_router.ubj"))
        self.embedder = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

    def _build_features(self, prompt: str) -> np.ndarray:
        embeddings = self.embedder.encode(
            [prompt],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)
        stats = extract_text_features(prompt)
        stats_arr = np.array([list(stats.values())], dtype=np.float32)
        return np.hstack([embeddings, stats_arr])

    def score(self, prompt: str) -> int:
        """Return predicted complexity score (1-10)."""
        X = self._build_features(prompt)
        raw = self.scorer.predict(X)[0]
        return int(np.clip(np.round(raw), 1, 10))

    def is_pro(self, prompt: str) -> bool:
        """Return True if prompt should be routed to pro model."""
        X = self._build_features(prompt)
        return bool(self.router.predict(X)[0])


if __name__ == "__main__":
    scorer = PromptScorer(str(MODELS_DIR))
    print("PromptScorer ready. Paste a prompt (Ctrl+D to quit):")
    while True:
        try:
            text = input("\n> ")
            if not text.strip():
                continue
            s = scorer.score(text)
            pro = scorer.is_pro(text)
            model = "deepseek-v4-pro" if pro else "deepseek-v4-flash"
            print(f"  Score: {s}/10  ->  {model}")
        except (EOFError, KeyboardInterrupt):
            print()
            break
