#!/bin/bash
cd "$(dirname "$0")"
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000
