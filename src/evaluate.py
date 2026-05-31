"""Evaluate trained models on validation set and held-out test set."""

import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    mean_absolute_error,
    precision_score,
    recall_score,
)
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier, XGBRegressor

from features import extract_text_features


ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
TEST_PATH = ROOT / "data" / "evaluated" / "eval_prompts_1000.jsonl"
FEAT_PATH = PROCESSED_DIR / "features.npy"
LABEL_PATH = PROCESSED_DIR / "labels.npy"


def load_test_data():
    prompts = []
    with open(TEST_PATH) as f:
        for line in f:
            prompts.append(json.loads(line))
    return prompts


def build_features_for_test(prompts, embedder):
    texts = [p["prompt"] for p in prompts]
    embeddings = embedder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=128,
    ).astype(np.float32)
    stats = [extract_text_features(p["prompt"]) for p in prompts]
    stats_arr = np.array([list(s.values()) for s in stats], dtype=np.float32)
    return np.hstack([embeddings, stats_arr])


def evaluate_by_dimension(prompts, y_true, y_pred_bin, dimension: str):
    groups = defaultdict(list)
    for i, p in enumerate(prompts):
        key = p.get(dimension, "unknown")
        groups[key].append((y_true[i], y_pred_bin[i]))
    print(f"\n--- Model vs ground-truth accuracy by {dimension} ---")
    for key in sorted(groups.keys()):
        trues, preds = zip(*groups[key])
        acc = accuracy_score(trues, preds)
        prec = precision_score(trues, preds, zero_division=0)
        rec = recall_score(trues, preds, zero_division=0)
        print(f"  {key:20s}: acc={acc:.3f}  prec={prec:.3f}  rec={rec:.3f}  n={len(trues)}")


def main():
    print("Loading models ...")
    scorer = XGBRegressor()
    scorer.load_model(str(MODELS_DIR / "xgb_scorer.ubj"))
    router = XGBClassifier()
    router.load_model(str(MODELS_DIR / "xgb_router.ubj"))
    embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")

    print("Loading validation data ...")
    X_val = np.load(FEAT_PATH)
    y_val = np.load(LABEL_PATH).astype(int)
    y_val_bin = (y_val >= 5).astype(int)

    y_pred_reg = scorer.predict(X_val)
    y_pred_reg_rounded = np.clip(np.round(y_pred_reg).astype(int), 1, 10)
    mae = mean_absolute_error(y_val, y_pred_reg_rounded)
    acc_exact = accuracy_score(y_val, y_pred_reg_rounded)
    acc_pm1 = np.mean(np.abs(y_val - y_pred_reg_rounded) <= 1)
    y_pred_bin = router.predict(X_val)

    print(f"\n=== Validation Set ({len(X_val)} samples) ===")
    print(f"Scorer MAE: {mae:.4f}")
    print(f"Scorer exact accuracy: {acc_exact:.4f}")
    print(f"Scorer ±1 accuracy: {acc_pm1:.4f}")
    print(f"Router accuracy: {accuracy_score(y_val_bin, y_pred_bin):.4f}")
    print(f"Router precision: {precision_score(y_val_bin, y_pred_bin):.4f}")
    print(f"Router recall: {recall_score(y_val_bin, y_pred_bin):.4f}")

    cm = confusion_matrix(y_val_bin, y_pred_bin)
    print(f"\nConfusion Matrix (Flash=0, Pro=1):")
    print(f"  TN={cm[0][0]:5d}  FP={cm[0][1]:5d}")
    print(f"  FN={cm[1][0]:5d}  TP={cm[1][1]:5d}")

    print(f"\n=== Error Distribution (regression) ===")
    errors = y_pred_reg_rounded - y_val
    for e in range(-3, 4):
        count = np.sum(errors == e)
        pct = count / len(errors) * 100
        bar = "#" * int(pct)
        print(f"  {e:+2d}: {count:5d} ({pct:5.1f}%) {bar}")

    print(f"\n=== Test Set: eval_prompts_1000.jsonl ===")
    test_prompts = load_test_data()
    print(f"  Test prompts: {len(test_prompts)}")

    print("  Building features for test set ...")
    X_test = build_features_for_test(test_prompts, embedder)
    y_test = np.array([p["model_evaluated_score"] for p in test_prompts], dtype=int)
    y_test_bin = (y_test >= 5).astype(int)

    y_pred_test_reg = scorer.predict(X_test)
    y_pred_test_rounded = np.clip(np.round(y_pred_test_reg).astype(int), 1, 10)
    y_pred_test_bin = router.predict(X_test)

    test_mae = mean_absolute_error(y_test, y_pred_test_rounded)
    test_acc_exact = accuracy_score(y_test, y_pred_test_rounded)
    test_acc_pm1 = np.mean(np.abs(y_test - y_pred_test_rounded) <= 1)
    test_router_acc = accuracy_score(y_test_bin, y_pred_test_bin)
    test_router_prec = precision_score(y_test_bin, y_pred_test_bin, zero_division=0)
    test_router_rec = recall_score(y_test_bin, y_pred_test_bin, zero_division=0)

    print(f"\n  Scorer MAE: {test_mae:.4f}")
    print(f"  Scorer exact accuracy: {test_acc_exact:.4f}")
    print(f"  Scorer ±1 accuracy: {test_acc_pm1:.4f}")
    print(f"  Router accuracy: {test_router_acc:.4f}")
    print(f"  Router precision: {test_router_prec:.4f}")
    print(f"  Router recall: {test_router_rec:.4f}")

    # Compare model routing vs heuristic routing
    match_model = 0
    match_heuristic = 0
    for i, p in enumerate(test_prompts):
        heuristic_is_pro = "pro" in p.get("recommended_model", "").lower()
        truth_is_pro = bool(y_test_bin[i])
        model_is_pro = bool(y_pred_test_bin[i])
        if truth_is_pro == model_is_pro:
            match_model += 1
        if truth_is_pro == heuristic_is_pro:
            match_heuristic += 1
    print(f"\n  Heuristic routing agreement: {match_heuristic}/{len(test_prompts)} ({match_heuristic/len(test_prompts)*100:.1f}%)")
    print(f"  Model routing agreement: {match_model}/{len(test_prompts)} ({match_model/len(test_prompts)*100:.1f}%)")

    evaluate_by_dimension(test_prompts, y_test_bin, y_pred_test_bin, "domain")
    evaluate_by_dimension(test_prompts, y_test_bin, y_pred_test_bin, "type")
    evaluate_by_dimension(test_prompts, y_test_bin, y_pred_test_bin, "difficulty")


if __name__ == "__main__":
    main()
