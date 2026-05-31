# Prompt Scorer & Router

一个基于 **XGBoost + BGE 语义嵌入** 的 prompt 评分与路由系统。给定任意中文/英文 prompt，返回一个 **1-10 的复杂度评分**，并自动判断应路由到简单模型（`deepseek-v4-flash`）还是高级模型（`deepseek-v4-pro`）。

## 核心能力

- **复杂度评分**：对 prompt 进行 1-10 分打分（回归模型，MAE ≈ 0.9，±1 容错率 > 80%）
- **模型路由**：自动判断 prompt 是否应升级到 pro 模型（二分类，准确率 ≈ 84%）
- **多语义支持**：基于 `BAAI/bge-small-zh-v1.5` 的 512 维文本嵌入，同时提取字符统计、代码/数学符号检测等轻量文本特征
- **高性能推理**：单次推理 < 15ms（CPU），支持批量评估
- **开箱即用 API**：FastAPI + uvicorn 部署，标准 REST 接口

## 项目结构

```
.
├── src/
│   ├── server.py        # FastAPI 服务入口
│   ├── inference.py     # 推理接口（打分 + 路由）
│   ├── features.py      # 特征工程（文本统计 + BGE 嵌入）
│   ├── train.py         # XGBoost 模型训练
│   └── evaluate.py      # 模型评估与测试
├── models/
│   ├── xgb_scorer.ubj   # 评分模型（XGBoost 回归）
│   └── xgb_router.ubj   # 路由模型（XGBoost 分类）
├── data/
│   ├── raw/             # 原始标注数据（100k 条, jsonl）
│   ├── processed/       # 预处理后的特征与标签（.npy）
│   └── evaluated/       # 评估用测试集（1k 条）
├── requirements.txt     # Python 依赖
├── serve.sh             # 启动 API 服务
├── score.sh             # 命令行交互式打分
└── score_test.js        # API 接口测试脚本（Node.js, 50 条用例）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 API 服务

```bash
./serve.sh
```

服务将在 `http://localhost:8000` 启动。

### 3. 调用打分接口

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"prompt": "用 Python 写一个快速排序算法并分析时间复杂度"}'
```

返回示例：

```json
{
  "score": 6,
  "model": "deepseek-v4-pro"
}
```

### 4. 命令行交互式打分

```bash
./score.sh
```

输入 prompt 即可查看评分与推荐模型。

## API 说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/score` | POST | 对 prompt 打分与路由 |

### POST /score

请求：
```json
{ "prompt": "你的 prompt 文本" }
```

响应：
```json
{
  "score": 5,                    // 复杂度评分 1-10
  "model": "deepseek-v4-pro"     // 推荐模型: pro 或 flash
}
```

## 模型架构

```
prompt 文本
    │
    ├─→ BGE-small-zh-v1.5 嵌入 (512维)
    │
    ├─→ 文本统计特征 (11维)
    │     · 字符数/词数/行数
    │     · 平均词长 / 词汇丰富度
    │     · 代码符号检测 / 数学符号检测
    │     · 列表标记 / 问号计数
    │     · 标点比例 / 中文比例
    │
    └─→ [522维特征向量] → XGBoost Scorer → Score (1-10)
                      └→ XGBoost Router  → Flash / Pro
```

## 训练数据

- **规模**：约 99,000 条 prompt，覆盖多种领域和难度
- **标注**：每条 prompt 附带 `model_evaluated_score`（1-10 分）和 `recommended_model`
- **训练策略**：85% 训练集 / 15% 验证集，3 折 GridSearchCV 调参

## 模型性能

| 指标 | Scorer | Router |
|------|--------|--------|
| MAE | 0.89 | - |
| 准确率 (exact) | 29.4% | 83.8% |
| ±1 容错率 | 83.4% | - |
| Precision | - | 94.6% |
| Recall | - | 82.5% |
| 推理延迟 (CPU) | < 15ms | < 15ms |

## 测试

运行 API 接口测试（需要 Node.js）：

```bash
node score_test.js
```

测试脚本生成 50 条不同难度等级的 prompt，对接口进行完整评测并生成报告：
- Spearman 秩相关系数：0.95（排序一致性极好）
- ±2 容忍匹配率：86%
- 评分实际输出范围：3-8（中间段 ±1 匹配率 100%）

## 依赖

- Python ≥ 3.10
- `sentence-transformers` ≥ 3.0（BGE 文本嵌入）
- `xgboost` ≥ 2.0（评分与路由模型）
- `scikit-learn` ≥ 1.5（数据分割与评估）
- `fastapi` + `uvicorn`（API 服务）
- `numpy` / `pandas`（数据处理）

## License

Internal Research — All rights reserved.
