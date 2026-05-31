#!/usr/bin/env python3
"""调用 deepseek-v4-pro 对每一条prompt进行复杂度评估修正。"""

import asyncio
import json
import os
import sys
import time
import aiohttp

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = "deepseek-v4-flash"
CONCURRENCY = 100
INPUT_FILE = "data/prompts_100k.jsonl"
OUTPUT_FILE = "data/prompts_100k_evaluated.jsonl"
CHECKPOINT_FILE = "data/eval_checkpoint.json"
SAVE_INTERVAL = 2000

EVAL_SYSTEM_PROMPT = """你是Prompt推理复杂度评估专家。你需要对给定的用户prompt从以下4个维度进行1-10分综合评分：

1. 推理链长度（1-10）：完成该任务需要几步逻辑推理？一步直接回答=1分，需要长篇多步推理链=10分
2. 知识深度（1-10）：是否需要深厚的领域专业知识？常识性问题=1分，需要博士级专业知识=10分
3. 步骤复杂度（1-10）：简单直接回答=1分，需要多步拆解、规划、验证=10分
4. 领域专业度（1-10）：日常通用问题=1分，需要特定领域专家知识=10分

综合4个维度给出一个最终的复杂度评分（1-10整数）：

评分参考：
1-2分：非常简单，一句话就能回答（如：问候、简单计算、常识问答）
3-4分：简单任务，需要少量推理（如：简短解释、简单翻译、基础代码）
5-6分：中等难度，需要多步推理或领域知识（如：分析问题、中等编程、专业解释）
7-8分：困难任务，需要深度推理和专业知识（如：复杂证明、系统设计、专业分析）
9-10分：极难任务，需要多领域综合、前沿知识、创造性专家级思维（如：研究级问题、大型系统架构）

只输出严格JSON，不要包含```json标记或任何其他文本：
{"complexity_score": <整数1-10>, "reason": "<一句话评分理由，20字以内>"}"""


def load_prompts(path: str, checkpoint: set) -> list[dict]:
    """加载所有prompt，跳过已评估的。"""
    prompts = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            if d["id"] not in checkpoint:
                prompts.append(d)
    return prompts


def load_checkpoint() -> set:
    """返回已完成的prompt id集合。"""
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    with open(CHECKPOINT_FILE, "r") as f:
        return set(json.load(f))


def save_checkpoint(ids: set):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(ids), f)


async def evaluate_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    prompt_data: dict,
    retries: int = 3,
) -> dict | None:
    """对一条prompt调用API评估。"""
    url = f"{BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_data["prompt"]},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
    }

    for attempt in range(retries):
        try:
            async with sem:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        # 解析JSON响应
                        content = content.removeprefix("```json").removesuffix("```").strip()
                        result = json.loads(content)
                        return {
                            "score": int(result["complexity_score"]),
                            "reason": result.get("reason", ""),
                        }
                    elif resp.status == 429:
                        # rate limit — 指数退避
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                        continue
                    else:
                        text = await resp.text()
                        print(f"  API错误 {resp.status}: {text[:200]}")
                        await asyncio.sleep(2 ** attempt)
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
            print(f"  请求异常 (尝试{attempt+1}/{retries}): {e}")
            await asyncio.sleep(2 ** attempt)

    return None


async def evaluate_batch(
    prompts: list[dict],
    checkpoint: set,
    processed_count: int = 0,
):
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY + 20, limit_per_host=CONCURRENCY + 10, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for p in prompts:
            tasks.append(evaluate_one(session, sem, p))

        # 批量执行
        results = []
        batch_size = 500
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

            # 将结果写回prompt数据并追加到输出文件
            batch_prompts = prompts[i : i + batch_size]
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                for j, (p, r) in enumerate(zip(batch_prompts, batch_results)):
                    if r is None:
                        # 评估失败，使用原始评分
                        p["model_evaluated_score"] = p["complexity_score"]
                        p["model_evaluation_reason"] = "评估失败，使用原始评分"
                    else:
                        p["model_evaluated_score"] = r["score"]
                        p["model_evaluation_reason"] = r["reason"]

                    # 根据新评分重新判定模型
                    new_score = p["model_evaluated_score"]
                    if new_score <= 4:
                        p["recommended_model"] = "deepseek-v4-flash"
                        p["model_reason"] = "经pro模型评估为低复杂度，快速响应即可"
                    else:
                        p["recommended_model"] = "deepseek-v4-pro"
                        if new_score <= 7:
                            p["model_reason"] = "经pro模型评估为中高复杂度，需要较强推理能力"
                        else:
                            p["model_reason"] = "经pro模型评估为高复杂度，需要深度推理"

                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
                    checkpoint.add(p["id"])

            processed_count += len(batch_prompts)
            if processed_count % SAVE_INTERVAL < batch_size or processed_count == len(prompts):
                save_checkpoint(checkpoint)
                progress = processed_count / len(prompts) * 100
                print(f"  进度: {processed_count}/{len(prompts)} ({progress:.1f}%) — 已保存checkpoint")


def main():
    if len(sys.argv) >= 2:
        global INPUT_FILE, OUTPUT_FILE, CHECKPOINT_FILE
        INPUT_FILE = sys.argv[1]
        OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else INPUT_FILE.replace(".jsonl", "_evaluated.jsonl")
        CHECKPOINT_FILE = sys.argv[3] if len(sys.argv) > 3 else INPUT_FILE.replace(".jsonl", "_checkpoint.json")

    if not API_KEY:
        print("错误: 请设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    print(f"API: {BASE_URL}")
    print(f"模型: {MODEL}")
    print(f"并发数: {CONCURRENCY}")

    checkpoint = load_checkpoint()
    print(f"已评估: {len(checkpoint)} 条")

    prompts = load_prompts(INPUT_FILE, checkpoint)
    total = len(prompts)
    print(f"待评估: {total} 条")

    if total == 0:
        print("所有prompt已评估完成！")
        return

    start = time.time()
    asyncio.run(evaluate_batch(prompts, checkpoint))
    elapsed = time.time() - start
    print(f"\n评估完成！总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"输出文件: {OUTPUT_FILE}")

    # 统计
    from collections import Counter
    flash = pro = 0
    score_dist = Counter()
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            if p["recommended_model"] == "deepseek-v4-flash":
                flash += 1
            else:
                pro += 1
            score_dist[p["model_evaluated_score"]] += 1

    print(f"\n=== 评估后分布 ===")
    print(f"flash: {flash} ({flash/(flash+pro)*100:.1f}%)")
    print(f"pro:   {pro} ({pro/(flash+pro)*100:.1f}%)")
    print(f"评分分布:")
    for s in sorted(score_dist):
        print(f"  {s}分: {score_dist[s]}条 ({score_dist[s]/(flash+pro)*100:.1f}%)")


if __name__ == "__main__":
    main()
