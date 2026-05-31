#!/usr/bin/env node
/**
 * 评分接口测试脚本
 * 接口: POST /score  {"prompt": "..."}  →  {"score": N, "model": "..."}
 * Score 范围: 1-10
 * 
 * 生成 50 条不同难度的 prompt，测试接口返回的 score 是否合理。
 * 预期难度映射:
 *   等级1 (极简)   → expected 1-2
 *   等级2 (简单)   → expected 3-4
 *   等级3 (中等)   → expected 5-6
 *   等级4 (困难)   → expected 7-8
 *   等级5 (极难)   → expected 9-10
 */

const BASE_URL = "http://localhost:8000/score";

// ====== 50 条 Prompt，按预期难度分为 5 个等级，每个等级 10 条 ======

const prompts = [
  // ---------- 等级1: 极简单 (预期 score ≈ 1-2) ----------
  { id: "E1-01", expected: 1, prompt: "你好" },
  { id: "E1-02", expected: 1, prompt: "谢谢" },
  { id: "E1-03", expected: 1, prompt: "嗯" },
  { id: "E1-04", expected: 1, prompt: "好的" },
  { id: "E1-05", expected: 1, prompt: "再见" },
  { id: "E1-06", expected: 2, prompt: "你叫什么名字" },
  { id: "E1-07", expected: 2, prompt: "今天星期几" },
  { id: "E1-08", expected: 2, prompt: "1+1等于几" },
  { id: "E1-09", expected: 2, prompt: "苹果用英语怎么说" },
  { id: "E1-10", expected: 2, prompt: "说个笑话" },

  // ---------- 等级2: 简单 (预期 score ≈ 3-4) ----------
  { id: "E2-01", expected: 3, prompt: "介绍一下马斯克" },
  { id: "E2-02", expected: 3, prompt: "Python是什么语言" },
  { id: "E2-03", expected: 3, prompt: "简述光合作用的过程" },
  { id: "E2-04", expected: 3, prompt: "如何做西红柿炒鸡蛋" },
  { id: "E2-05", expected: 3, prompt: "什么是人工智能" },
  { id: "E2-06", expected: 4, prompt: "推荐三本好看的科幻小说并简单介绍" },
  { id: "E2-07", expected: 4, prompt: "全球变暖的主要原因有哪些" },
  { id: "E2-08", expected: 4, prompt: "写一篇200字的自我介绍" },
  { id: "E2-09", expected: 4, prompt: "有哪些高效学英语的方法" },
  { id: "E2-10", expected: 4, prompt: "对比一下淘宝和京东的区别" },

  // ---------- 等级3: 中等 (预期 score ≈ 5-6) ----------
  { id: "E3-01", expected: 5, prompt: "用Python写一个快速排序算法并分析时间复杂度" },
  { id: "E3-02", expected: 5, prompt: "比较React和Vue框架的优缺点和适用场景" },
  { id: "E3-03", expected: 5, prompt: "解释区块链的核心原理及其在供应链管理中的应用" },
  { id: "E3-04", expected: 5, prompt: "设计一个支持高并发访问的短链接系统的基本方案" },
  { id: "E3-05", expected: 5, prompt: "对比MySQL和PostgreSQL在大数据量下的性能差异" },
  { id: "E3-06", expected: 6, prompt: "分析当前中美贸易关系的核心矛盾和未来趋势" },
  { id: "E3-07", expected: 6, prompt: "写一篇500字关于量子计算发展现状的文章" },
  { id: "E3-08", expected: 6, prompt: "说明Kubernetes部署微服务的核心步骤和注意事项" },
  { id: "E3-09", expected: 6, prompt: "解释GPT中Transformer架构的自注意力机制" },
  { id: "E3-10", expected: 6, prompt: "设计一个电商推荐系统的技术方案和数据流" },

  // ---------- 等级4: 困难 (预期 score ≈ 7-8) ----------
  { id: "E4-01", expected: 7, prompt: "深入分析CAP理论在分布式数据库中的权衡，结合Spanner和DynamoDB的实际架构给出具体建议" },
  { id: "E4-02", expected: 7, prompt: "设计并实现一个支持LRU淘汰策略的线程安全缓存系统，支持百万级QPS，包含完整单元测试和基准测试分析" },
  { id: "E4-03", expected: 7, prompt: "从编译器原理角度分析Rust所有权系统如何消除数据竞争，追踪从MIR到LLVM IR的生命周期推导过程" },
  { id: "E4-04", expected: 7, prompt: "设计一个广告投放效果分析平台，支持多数据源实时聚合、10+维度OLAP查询、日均100亿事件处理" },
  { id: "E4-05", expected: 7, prompt: "从零推导Transformer注意力机制的数学原理，包括缩放点积注意力、多头并行计算复杂度和反向传播梯度路径" },
  { id: "E4-06", expected: 8, prompt: "构建面向LLM的端到端RAG系统：设计chunk策略、混合检索融合排序、引用追踪生成pipeline、大规模文档下的成本优化" },
  { id: "E4-07", expected: 8, prompt: "详细对比Linux内核5.x到6.x在CFS调度器、io_uring、BPF CO-RE和内存管理多代LRU方面的演进，附内核源码级解释" },
  { id: "E4-08", expected: 8, prompt: "为Web3社交平台设计完整通证经济模型：代币发行机制、创作者激励博弈论分析、治理数学建模、抗女巫攻击、Solidity核心合约" },
  { id: "E4-09", expected: 8, prompt: "从第一性原理推导半导体器件微型化极限：量子隧穿在3nm以下影响、TFET工作原理、光子计算可行性、2035年技术路线图" },
  { id: "E4-10", expected: 8, prompt: "实现面向超大规模图的分布式社区发现算法：十亿节点级Louvain的MPI/GPU加速、动态图增量计算、Graph500扩展性分析" },

  // ---------- 等级5: 极难 (预期 score ≈ 9-10) ----------
  { id: "E5-01", expected: 9, prompt: "设计AGI系统完整技术方案：多模态感知世界模型统一架构、因果推理长期规划、元学习持续学习框架、AI对齐价值加载方案" },
  { id: "E5-02", expected: 9, prompt: "设计全球气候变化应对协调系统：碳交易多主体博弈模型、强化学习电网调度、生态数字孪生、跨国治理法律框架" },
  { id: "E5-03", expected: 9, prompt: "构建人类基因编辑计算决策支持系统：CRISPR脱靶深度学习预测、多组学影响分析、群体遗传学风险评估、伦理数学化决策框架" },
  { id: "E5-04", expected: 9, prompt: "设计火星殖民地生命维持系统工程方案：封闭生态物质循环建模、辐射防护拓扑优化、ISRU化工流程、人工重力数值模拟" },
  { id: "E5-05", expected: 9, prompt: "提出统一场论假设：标准模型与广义相对论统一数学框架、可实验验证的新预言、LHC和CMB印记分析、暗物质暗能量解释" },
  { id: "E5-06", expected: 10, prompt: "设计下一代互联网基础协议：内容中心网络取代IP的扁平命名方案、抗量子密码路由集成、区块链自治域信任模型、行星际尺度扩展性验证" },
  { id: "E5-07", expected: 10, prompt: "开发全脑仿真平台技术路线图：突触级神经元并行计算架构、电子显微镜连接组自动重建、意识涌现检测指标、伦理与法律界定" },
  { id: "E5-08", expected: 10, prompt: "构建全球实时语言无损翻译系统：100+语言端到端语音翻译架构、文化语境跨语言保真度建模、百毫秒推理优化、同态加密隐私保护" },
  { id: "E5-09", expected: 10, prompt: "设计光年星际文明通信协议：量子纠缠超距通信理论极限、星际衰减模型与纠错码、未知文明首次接触通用语义编码、Great Filter风险对策" },
  { id: "E5-10", expected: 10, prompt: "提出人体衰老工程化逆转方案：端粒延长与表观遗传重编程精确调控、衰老细胞清除与再生时空控制、线粒体基因回路设计、免疫年轻化细胞治疗、FDA审批路径" },
];

async function testOne({ id, expected, prompt }) {
  const start = Date.now();
  try {
    const res = await fetch(BASE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
      signal: AbortSignal.timeout(30000),
    });
    const data = await res.json();
    const elapsed = Date.now() - start;
    return { id, expected, prompt: prompt.slice(0, 80), actual: data.score, model: data.model, match: data.score === expected, diff: data.score - expected, elapsed, error: null };
  } catch (e) {
    return { id, expected, prompt: prompt.slice(0, 80), actual: null, model: null, match: false, diff: null, elapsed: Date.now() - start, error: e.message };
  }
}

async function main() {
  console.log("=".repeat(70));
  console.log("评分接口测试报告");
  console.log(`接口: POST ${BASE_URL}`);
  console.log(`Score 范围: 1-10`);
  console.log(`测试时间: ${new Date().toISOString()}`);
  console.log(`测试用例数: ${prompts.length}`);
  console.log("=".repeat(70));
  console.log();

  // 串行调用
  const results = [];
  let i = 0;
  for (const p of prompts) {
    process.stdout.write(`\r测试进度: ${++i}/${prompts.length}`);
    const r = await testOne(p);
    results.push(r);
  }
  console.log("\n");

  // ===== 详细结果 =====
  console.log("-".repeat(100));
  console.log("ID      | 预期 | 实际 | 偏差 | 模型                     | 延迟  | Prompt(截断)");
  console.log("-".repeat(100));

  for (const r of results) {
    const id = r.id.padEnd(7);
    const exp = String(r.expected).padStart(2);
    const act = r.actual !== null ? String(r.actual).padStart(2) : "ER";
    const diff = r.diff !== null ? (r.diff > 0 ? "+" + r.diff : String(r.diff)).padStart(3) : " --";
    const model = (r.model || "ERROR").padEnd(24);
    const delay = String(r.elapsed).padStart(4) + "ms";
    const ptext = r.prompt.padEnd(40);
    const err = r.error ? ` [ERR] ${r.error}` : "";
    console.log(`${id} |  ${exp}  |  ${act} | ${diff}  | ${model} | ${delay} | ${ptext}${err}`);
  }
  console.log("-".repeat(100));
  console.log();

  // ===== 统计 =====
  const total = results.length;
  const errors = results.filter(r => r.error).length;
  const valid = results.filter(r => !r.error);
  const exactMatch = valid.filter(r => r.match).length;
  const withinOne = valid.filter(r => Math.abs(r.diff) <= 1).length;
  const withinTwo = valid.filter(r => Math.abs(r.diff) <= 2).length;
  const accuracy = valid.length > 0 ? ((exactMatch / valid.length) * 100).toFixed(1) : "N/A";
  const accuracyWithin1 = valid.length > 0 ? ((withinOne / valid.length) * 100).toFixed(1) : "N/A";
  const accuracyWithin2 = valid.length > 0 ? ((withinTwo / valid.length) * 100).toFixed(1) : "N/A";

  // 每个等级的准确率
  console.log("===== 分等级准确率 =====");
  for (let level = 1; level <= 5; level++) {
    const levelResults = results.filter(r => r.expected >= (level-1)*2+1 && r.expected <= level*2 && !r.error);
    const matchCount = levelResults.filter(r => r.match).length;
    const withinOneCount = levelResults.filter(r => Math.abs(r.diff) <= 1).length;
    const withinTwoCount = levelResults.filter(r => Math.abs(r.diff) <= 2).length;
    const avgScore = levelResults.length > 0 ? (levelResults.reduce((s, r) => s + r.actual, 0) / levelResults.length).toFixed(2) : "N/A";
    const avgDelay = levelResults.length > 0 ? Math.round(levelResults.reduce((s, r) => s + r.elapsed, 0) / levelResults.length) : "N/A";
    const expectedRange = `${(level-1)*2+1}-${level*2}`;
    console.log(
      `等级${level} (预期${expectedRange}, ${levelResults.length}题): 完全匹配=${matchCount}(${(matchCount/levelResults.length*100).toFixed(0)}%), ` +
      `±1=${withinOneCount}(${(withinOneCount/levelResults.length*100).toFixed(0)}%), ` +
      `±2=${withinTwoCount}(${(withinTwoCount/levelResults.length*100).toFixed(0)}%), ` +
      `均分=${avgScore}, 延迟=${avgDelay}ms`
    );
  }

  // ===== 混淆矩阵 =====
  console.log("\n===== 混淆矩阵 (预期 \\ 实际) =====");
  const allScores = [...new Set(valid.map(r => r.actual).sort((a,b)=>a-b))];
  const maxScore = Math.max(...allScores, 10);
  const minScore = Math.min(...allScores, 1);
  const scoreRange = maxScore - minScore + 1;
  const matrix = Array.from({ length: 10 }, () => Array(scoreRange).fill(0));
  for (const r of valid) {
    matrix[r.expected - 1][r.actual - minScore]++;
  }
  console.log("          实际分");
  const header = Array.from({ length: scoreRange }, (_, i) => String(i + minScore).padStart(4)).join("");
  console.log("      " + header);
  for (let i = 0; i < 10; i++) {
    const row = matrix[i].map(n => n > 0 ? String(n).padStart(4) : "    ").join("");
    console.log(`预${String(i+1).padStart(2)}  ` + row);
  }

  // ===== 汇总 =====
  console.log("\n===== 汇总 =====");
  console.log(`总测试数:       ${total}`);
  console.log(`成功调用:       ${total - errors}`);
  console.log(`失败调用:       ${errors}`);
  console.log(`完全匹配率:     ${accuracy}%`);
  console.log(`±1 容忍匹配率:  ${accuracyWithin1}%`);
  console.log(`±2 容忍匹配率:  ${accuracyWithin2}%`);
  console.log(`平均延迟:       ${Math.round(valid.reduce((s, r) => s + r.elapsed, 0) / valid.length)}ms`);
  console.log(`最高延迟:       ${Math.max(...valid.map(r => r.elapsed))}ms`);
  console.log(`最低延迟:       ${Math.min(...valid.map(r => r.elapsed))}ms`);

  const avgActual = valid.length > 0 ? (valid.reduce((s, r) => s + r.actual, 0) / valid.length).toFixed(2) : "N/A";
  const avgExpected = valid.length > 0 ? (valid.reduce((s, r) => s + r.expected, 0) / valid.length).toFixed(2) : "N/A";
  console.log(`预期平均分:     ${avgExpected}`);
  console.log(`实际平均分:     ${avgActual}`);

  // 偏差分析
  console.log("\n===== 偏差分析 =====");
  const diffs = valid.map(r => r.diff);
  console.log(`最大正向偏差:   +${Math.max(...diffs)}`);
  console.log(`最大负向偏差:   ${Math.min(...diffs)}`);
  console.log(`平均绝对偏差:   ${(diffs.reduce((s, d) => s + Math.abs(d), 0) / diffs.length).toFixed(2)}`);
  console.log(`标准差(偏差):   ${Math.sqrt(diffs.reduce((s, d) => s + d*d, 0) / diffs.length).toFixed(2)}`);

  // Spearman 秩相关系数 (评估单调性/排序一致性)
  const n = valid.length;
  const ranked = valid.map((r, i) => ({ ...r, idx: i }));
  const rankExp = [...ranked].sort((a, b) => a.expected - b.expected || a.idx - b.idx);
  const rankAct = [...ranked].sort((a, b) => a.actual - b.actual || a.idx - b.idx);
  const rankMapExp = {}; rankExp.forEach((r, i) => rankMapExp[r.id] = i);
  const rankMapAct = {}; rankAct.forEach((r, i) => rankMapAct[r.id] = i);
  let dSq = 0;
  for (const r of valid) dSq += (rankMapExp[r.id] - rankMapAct[r.id]) ** 2;
  const spearman = 1 - (6 * dSq) / (n * (n * n - 1));
  console.log(`Spearman秩相关:  ${spearman.toFixed(4)} (越接近1排序越一致)`);

  // 分数分布
  console.log("\n===== 分数分布 =====");
  const actualDist = {};
  for (const r of valid) {
    actualDist[r.actual] = (actualDist[r.actual] || 0) + 1;
  }
  for (let s = minScore; s <= maxScore; s++) {
    const count = actualDist[s] || 0;
    const bar = "#".repeat(count * 2);
    console.log(`  Score ${String(s).padStart(2)}: ${bar}${count > 0 ? " ("+count+")" : ""}`);
  }

  // 模型使用分析
  const modelCounts = {};
  for (const r of valid) {
    modelCounts[r.model] = (modelCounts[r.model] || 0) + 1;
  }
  console.log("\n===== 模型分布 =====");
  for (const [model, count] of Object.entries(modelCounts)) {
    const scores = valid.filter(r => r.model === model).map(r => r.actual);
    console.log(`  ${model}: ${count}次调用, 均分=${(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(2)}, 范围=${Math.min(...scores)}-${Math.max(...scores)}`);
  }

  // 结论
  console.log("\n===== 结论 =====");
  const within2Pct = parseFloat(accuracyWithin2);
  const within1Pct = parseFloat(accuracyWithin1);
  if (spearman > 0.9 && within2Pct >= 80) {
    console.log("✅ 优秀：接口评分排序一致性很高(Spearman>0.9)，±2容忍范围内匹配率高，能很好区分prompt难度。");
  } else if (spearman > 0.8 && within2Pct >= 60) {
    console.log("👍 良好：接口评分整体合理，排序一致性尚可，±2容忍范围表现不错。");
  } else if (spearman > 0.6) {
    console.log("⚠️ 一般：接口评分有一定区分度，排序方向基本正确但偏差较大，建议校准。");
  } else {
    console.log("❌ 较差：接口评分区分度不足，排序混乱或偏差严重，建议重新训练/校准评分模型。");
  }

  console.log("\n报告生成完毕。");
}

main().catch(console.error);
