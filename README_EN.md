# Prompt Scorer & Router

An **XGBoost + BGE semantic embeddings** based prompt scoring and routing system. Given any Chinese or English prompt, it returns a **complexity score from 1-10** and automatically determines whether to route to a lightweight model (`deepseek-v4-flash`) or an advanced model (`deepseek-v4-pro`).

## Core Capabilities

- **Complexity Scoring**: Rates prompts on a 1-10 scale (regression model, MAE ≈ 0.9, ±1 tolerance > 80%)
- **Model Routing**: Automatically decides whether a prompt should be upgraded to the pro model (binary classification, accuracy ≈ 84%)
- **Multi-semantic Features**: 512-dimensional text embeddings from `BAAI/bge-small-zh-v1.5`, combined with lightweight statistical features (character count, code/math symbol detection, etc.)
- **High-performance Inference**: < 15ms per inference (CPU), supports batch evaluation
- **Ready-to-use API**: FastAPI + uvicorn deployment with standard REST endpoints

## Project Structure

```
.
├── src/
│   ├── server.py        # FastAPI server entry point
│   ├── inference.py     # Inference interface (scoring + routing)
│   ├── features.py      # Feature engineering (text stats + BGE embeddings)
│   ├── train.py         # XGBoost model training
│   └── evaluate.py      # Model evaluation & testing
├── models/
│   ├── xgb_scorer.ubj   # Scoring model (XGBoost regression)
│   └── xgb_router.ubj   # Routing model (XGBoost classification)
├── data/
│   ├── raw/             # Raw labeled data (100k samples, jsonl)
│   ├── processed/       # Preprocessed features & labels (.npy)
│   └── evaluated/       # Evaluation test set (1k samples)
├── requirements.txt     # Python dependencies
├── serve.sh             # Start API server
├── score.sh             # Interactive CLI scoring
└── score_test.js        # API test script (Node.js, 50 test cases)
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start API Server

```bash
./serve.sh
```

The server starts at `http://localhost:8000`.

### 3. Call the Scoring Endpoint

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a quicksort algorithm in Python and analyze its time complexity"}'
```

Example response:

```json
{
  "score": 6,
  "model": "deepseek-v4-pro"
}
```

### 4. Interactive CLI Scoring

```bash
./score.sh
```

Enter a prompt to see its score and recommended model.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/score` | POST | Score and route a prompt |

### POST /score

Request:
```json
{ "prompt": "Your prompt text" }
```

Response:
```json
{
  "score": 5,                    // Complexity score 1-10
  "model": "deepseek-v4-pro"     // Recommended model: pro or flash
}
```

## Model Architecture

```
prompt text
    │
    ├─→ BGE-small-zh-v1.5 Embedding (512-dim)
    │
    ├─→ Statistical Features (11-dim)
    │     · char_count / word_count / line_count
    │     · avg_word_len / vocab_richness
    │     · code_pattern detection / math_pattern detection
    │     · list_detection / question_count
    │     · punctuation_ratio / chinese_ratio
    │
    └─→ [523-dim feature vector] → XGBoost Scorer → Score (1-10)
                                 └→ XGBoost Router  → Flash / Pro
```

## Training Data

- **Scale**: ~99,000 prompts covering diverse domains and difficulty levels
- **Labels**: Each prompt includes `model_evaluated_score` (1-10) and `recommended_model`
- **Training Strategy**: 85% train / 15% validation split, 3-fold GridSearchCV for hyperparameter tuning

## Model Performance

| Metric | Scorer | Router |
|--------|--------|--------|
| MAE | 0.89 | — |
| Accuracy (exact) | 29.4% | 83.8% |
| ±1 Tolerance | 83.4% | — |
| Precision | — | 94.6% |
| Recall | — | 82.5% |
| Inference Latency (CPU) | < 15ms | < 15ms |

## Testing

Run the API test suite (requires Node.js):

```bash
node score_test.js
```

The test script generates 50 prompts across 5 difficulty levels, calls the API, and produces a comprehensive report:
- Spearman rank correlation: 0.95 (excellent monotonicity)
- ±2 tolerance accuracy: 86%
- Actual output range: 3-8 (middle range ±1 match rate: 100%)

## Dependencies

- Python ≥ 3.10
- `sentence-transformers` ≥ 3.0 (BGE text embeddings)
- `xgboost` ≥ 2.0 (scoring & routing models)
- `scikit-learn` ≥ 1.5 (data splitting & evaluation)
- `fastapi` + `uvicorn` (API server)
- `numpy` / `pandas` (data processing)

## License

Internal Research — All rights reserved.
