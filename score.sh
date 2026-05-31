#!/bin/bash
cd "$(dirname "$0")"
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
python3 -c "
import sys
sys.path.insert(0, 'src')
from inference import PromptScorer
scorer = PromptScorer('models/')
print('Prompt 打分器就绪，输入 prompt 查看评分 (Ctrl+C 退出)')
while True:
    try:
        t = input('\n> ')
        if not t.strip():
            continue
        s = scorer.score(t)
        m = 'pro' if scorer.is_pro(t) else 'flash'
        print(f'  {s}/10 -> {m}')
    except (EOFError, KeyboardInterrupt):
        print()
        break
"
