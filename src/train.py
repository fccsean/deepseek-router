"""Train XGBoost scorer (regression) and router (binary classifier)."""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from xgboost import XGBClassifier, XGBRegressor


ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
FEAT_PATH = PROCESSED_DIR / "features.npy"
LABEL_PATH = PROCESSED_DIR / "labels.npy"


def load_data():
    X = np.load(FEAT_PATH)
    y = np.load(LABEL_PATH).astype(int)
    return X, y


def train_scorer(X_train, y_train) -> XGBRegressor:
    param_grid = {
        "max_depth": [4, 6, 8],
        "learning_rate": [0.05, 0.1, 0.2],
        "n_estimators": [100, 200, 300],
    }
    model = XGBRegressor(
        objective="reg:squarederror",
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    gs = GridSearchCV(model, param_grid, cv=3, scoring="neg_mean_absolute_error", n_jobs=1, verbose=1)
    gs.fit(X_train, y_train)
    print(f"Scorer best params: {gs.best_params_}")
    print(f"Scorer best CV MAE: {-gs.best_score_:.4f}")
    return gs.best_estimator_


def train_router(X_train, y_train_bin) -> XGBClassifier:
    param_grid = {
        "max_depth": [4, 6, 8],
        "learning_rate": [0.05, 0.1, 0.2],
        "n_estimators": [100, 200, 300],
    }
    model = XGBClassifier(
        objective="binary:logistic",
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    gs = GridSearchCV(model, param_grid, cv=3, scoring="accuracy", n_jobs=1, verbose=1)
    gs.fit(X_train, y_train_bin)
    print(f"Router best params: {gs.best_params_}")
    print(f"Router best CV accuracy: {gs.best_score_:.4f}")
    return gs.best_estimator_


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data ...")
    X, y = load_data()
    print(f"  X: {X.shape}, y: {y.shape}")

    y_bin = (y >= 5).astype(int)
    print(f"  Flash (<=4): {(y_bin == 0).sum()}, Pro (>=5): {y_bin.sum()}")

    X_train, X_val, y_train, y_val, y_train_bin, y_val_bin = train_test_split(
        X, y, y_bin, test_size=0.15, random_state=42, stratify=y_bin
    )
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

    print("\n=== Training scorer (regression) ===")
    scorer = train_scorer(X_train, y_train)

    print("\n=== Training router (binary) ===")
    router = train_router(X_train, y_train_bin)

    print("\n=== Validation ===")
    y_pred_reg = scorer.predict(X_val)
    y_pred_reg_rounded = np.clip(np.round(y_pred_reg).astype(int), 1, 10)
    mae = mean_absolute_error(y_val, y_pred_reg_rounded)
    acc_exact = accuracy_score(y_val, y_pred_reg_rounded)
    acc_pm1 = np.mean(np.abs(y_val - y_pred_reg_rounded) <= 1)
    print(f"Scorer MAE: {mae:.4f}")
    print(f"Scorer exact accuracy: {acc_exact:.4f}")
    print(f"Scorer ±1 accuracy: {acc_pm1:.4f}")

    y_pred_bin = router.predict(X_val)
    print(f"Router accuracy: {accuracy_score(y_val_bin, y_pred_bin):.4f}")
    print(f"Router precision: {precision_score(y_val_bin, y_pred_bin):.4f}")
    print(f"Router recall: {recall_score(y_val_bin, y_pred_bin):.4f}")

    scorer_path = MODELS_DIR / "xgb_scorer.ubj"
    router_path = MODELS_DIR / "xgb_router.ubj"
    scorer.save_model(str(scorer_path))
    router.save_model(str(router_path))
    print(f"\nSaved: {scorer_path}, {router_path}")


if __name__ == "__main__":
    main()
