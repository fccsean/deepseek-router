"""Feature extraction and embedding generation for prompt scoring."""

import json
import os
import re
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "prompts_100k_evaluated.jsonl"
PROCESSED_DIR = ROOT / "data" / "processed"

CODE_PATTERN = re.compile(r"```|\bdef\b|\bclass\b|\bfunction\b|\bimport\b|#include|<script|<html")
MATH_PATTERN = re.compile(
    r"[∑∫∏√∞∂∇∈∀∃]|\\frac|\\sum|\\int|\\alpha|\\beta|\\theta|"
    r"\d+\s*[+\-*/=]\s*\d+|\\begin\{|\\end\{"
)
LIST_PATTERN = re.compile(r"^\s*(?:\d+[.、)]|[-*+•])\s", re.MULTILINE)

# Simple Chinese word segmentation by regex: split on non-Chinese boundaries
_WORD_RE = re.compile(r"[一-鿿]+|[a-zA-Z]+|\d+|[^\s]")


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: Chinese chars grouped per word, ASCII words, digits."""
    return _WORD_RE.findall(text)


def extract_text_features(text: str) -> dict:
    """Extract lightweight statistical features from prompt text."""
    words = _tokenize(text)
    lines = text.splitlines()
    char_count = len(text)
    word_count = len(words)
    line_count = len([l for l in lines if l.strip()])

    return {
        "char_count": char_count,
        "word_count": word_count,
        "line_count": line_count,
        "avg_word_len": char_count / max(word_count, 1),
        "has_code": int(bool(CODE_PATTERN.search(text))),
        "has_math": int(bool(MATH_PATTERN.search(text))),
        "has_list": int(bool(LIST_PATTERN.search(text))),
        "question_count": text.count("?") + text.count("？"),
        "punctuation_ratio": sum(1 for c in text if c in "，。！？、；：""''（）《》【】,.!?;:()[]{}\"'") / max(char_count, 1),
        "chinese_ratio": sum(1 for c in text if "一" <= c <= "鿿") / max(char_count, 1),
        "vocab_richness": len(set(words)) / max(word_count, 1),
    }


def load_prompts(path: str | Path) -> list[dict]:
    prompts = []
    with open(path) as f:
        for line in f:
            prompts.append(json.loads(line))
    return prompts


def compute_embeddings(
    texts: list[str],
    model_name: str = "BAAI/bge-small-zh-v1.5",
    device: str = "mps",
    batch_size: int = 256,
) -> np.ndarray:
    """Compute sentence embeddings. Use MPS for bulk, CPU for single."""
    model = SentenceTransformer(model_name, device=device)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def build_feature_matrix(prompts: list[dict], embeddings: np.ndarray) -> np.ndarray:
    """Combine text statistical features with embeddings."""
    stats = [extract_text_features(p["prompt"]) for p in prompts]
    stats_df = pd.DataFrame(stats)
    stats_arr = stats_df.values.astype(np.float32)
    return np.hstack([embeddings, stats_arr])


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {RAW_PATH} ...")
    prompts = load_prompts(RAW_PATH)
    texts = [p["prompt"] for p in prompts]
    scores = np.array([p["model_evaluated_score"] for p in prompts], dtype=np.float32)
    print(f"  Loaded {len(prompts)} prompts, score range [{scores.min():.0f}, {scores.max():.0f}]")

    print("Computing embeddings (MPS batch) ...")
    embeddings = compute_embeddings(texts, device="mps")
    print(f"  Embeddings shape: {embeddings.shape}")

    print("Building feature matrix ...")
    X = build_feature_matrix(prompts, embeddings)
    print(f"  Feature matrix shape: {X.shape}")

    emb_path = PROCESSED_DIR / "embeddings.npy"
    feat_path = PROCESSED_DIR / "features.npy"
    label_path = PROCESSED_DIR / "labels.npy"
    np.save(emb_path, embeddings)
    np.save(feat_path, X)
    np.save(label_path, scores)
    print(f"Saved: {emb_path}, {feat_path}, {label_path}")


if __name__ == "__main__":
    main()
