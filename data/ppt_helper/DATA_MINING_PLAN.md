# 数据挖掘计划：从 350 篇文献中提取大型风机气动研究空白

## 挖掘策略：层级脉络法

按照信息凝练程度，从**概览到深入**，有目的性地挖掘：

```
Level 4: Part（最凝练）→ 作为总结和验证，了解整体框架
Level 3: Phase（凝练层）→ 系统性扫描，识别关键线索
Level 2: Agent Results（中间层）→ 深入分析，提取具体空白
Level 1: Full.md（最底层）→ 有针对性地验证，补充细节
```

---

## 第一阶段：全局概览（Part + Phase）

**目标**：了解整体框架，识别 8 大领域的核心问题

### Step 1.1：阅读 Part 层（总结验证）
```
文件：
1. part1_literature_review.md - 领域发展脉络、研究热点
2. part4_future_work.md - 当前局限性、未来方向

关注点：
- 研究空白和挑战的描述
- "未解决"、"缺乏"、"空白"、"局限"等关键词
- 提到的文献数量级和具体数据
```

### Step 1.2：扫描 Phase 层（识别线索）
```
文件：
1. phase1_overview.json - 整体概览
   ├─ research_gaps（直接列出研究空白）
   ├─ emerging_trends（新兴趋势）
   └─ key_papers（高影响力文献）

2. 各领域 domain_analysis.json（8 个领域）
   ├─ 浮式海上风电气动弹性
   ├─ 风力机气动外形优化
   ├─ 动态失速与非定常气动特性
   └─ ... 其他 5 个领域

关注点：
- 每个领域的"关键挑战"、"研究空白"、"发展趋势"
- 频繁出现的文献（可能是核心工作）
- 领域间的关联关系
```

**输出**：
- 初步研究空白列表（10-15 个）
- 候选重点文献列表（20-30 篇）
- 需要深入挖掘的领域（3-5 个）

---

## 第二阶段：深度分析（Agent Results）

**目标**：从 5 个维度分析中提取具体的研究空白

### Step 2.1：系统性扫描 Agent Results
```
扫描路径：
data/agent_results/categories/
├─ 浮式海上风电气动弹性与耦合动力学/
│   └─ {paper_id}/
│       ├─ innovation.json（查找"但是"、"然而"、"未解决"）
│       ├─ motivation.json（查找"需求"、"挑战"、"限制"）
│       ├─ mechanism.json（查找"不清楚"、"未阐明"、"依赖经验"）
│       └─ impact.json（查找"影响"、"有待"、"需要"）
├─ 风力机气动外形优化与设计/
└─ ...（其他 6 个领域）

关注点：
1. Innovation.json：
   - 创新点中的"局限性"或"未解决"部分
   - "但仍需"、"进一步研究"、"未来工作"等表述

2. Motivation.json：
   - 研究动机中的"问题"和"挑战"
   - "为了解决"、"针对"、"目前缺乏"等表述

3. Mechanism.json：
   - 机理解析中的"不清楚"、"未完全阐明"
   - "尚待研究"、"有待深入"等表述

4. Impact.json：
   - 影响评估中的"局限性"、"有待改进"
   - "应用前景"、"需要验证"等表述
```

### Step 2.2：跨领域关联分析
```
任务：识别跨领域的共同问题

方法：
1. 统计各领域 Agent Results 中高频出现的问题
2. 识别在多个领域都被提到的文献
3. 分析领域间的因果链条

示例：
- 如果"旋转效应"在多个领域都被提到 → 可能是核心问题
- 如果"CFD 成本"在多个领域都是瓶颈 → 可能是关键空白
```

**输出**：
- 细化的研究空白列表（20-30 个）
- 每个空白的具体描述和文献支撑
- 跨领域关联图谱

---

## 第三阶段：深入验证（Full.md）

**目标**：针对性地阅读原始文献，验证和补充细节

### Step 3.1：识别需要深入阅读的文献
```
筛选标准：
1. 高频引用文献（在多个 Agent Results 中出现）
2. 关键空白的核心支撑文献
3. 最新进展文献（2024-2026 年）

优先级：
- 一级：Phase/Agent 中多次提到的文献
- 二级：Part 中明确指出的关键文献
- 三级：补充性文献
```

### Step 3.2：有针对性地阅读 Full.md
```
阅读策略：
不要全文阅读，而是针对性查找：

1. Abstract（摘要）- 快速判断相关性
2. Introduction（引言）- 查找"研究动机"和"挑战"
3. Conclusion（结论）- 查找"局限性"和"未来工作"
4. Discussion（讨论）- 查找"未解决"的问题

关键定位词：
- "However," "Nevertheless," "But,"
- "remains unclear," "not well understood,"
- "future work," "further research," "needs to,"
- "limitation," "challenge," "open question,"
- "目前尚不"、"有待进一步"、"未解决"
```

### Step 3.3：交叉验证
```
任务：确保研究空白的准确性

方法：
1. 从 Full.md 中提取的空白 → 回到 Agent Results 验证
2. 从 Agent Results 提取的空白 → 回到 Phase/Part 验证
3. 检查是否有矛盾或遗漏

示例：
- Full.md 中说"旋转效应未阐明"
  → 验证 Agent mechanism.json 是否有相关描述
  → 验证 Phase domain_analysis 是否提到这个挑战
```

**输出**：
- 验证后的研究空白列表（去重、核实）
- 每个空白的详细描述（有具体数据支撑）
- 核心文献清单（有页码/章节引用）

---

## 第四阶段：结构化输出

**目标**：生成可用的研究空白数据库

### Step 4.1：分类整理
```
按维度分类：
- 理论模型（气动弹性、动态失速、湍流模型）
- 计算方法（CFD-CSD、ROM、AI 辅助）
- 实验验证（全尺寸数据、风洞缩比）
- 工程应用（制造约束、控制鲁棒性）

按对象分类：
- 超大型风机（20MW+）特有问题
- 浮式海上风电特有问题
- 极端工况特有问题
```

### Step 4.2：优先级排序
```
排序标准：
1. 影响程度（影响多少风机/设计）
2. 研究紧迫性（安全性/经济性）
3. 可行性（数据/工具/时间）
4. 创新空间（发表论文潜力）
```

### Step 4.3：生成 JSON 数据库
```
输出格式：
{
  "research_gaps": [
    {
      "id": "gap_001",
      "title": "研究空白标题",
      "category": "分类",
      "description": "详细描述",
      "relevance": "与大型风机气动的相关性",
      "evidence": {
        "level2": "Agent Results 证据",
        "level3": "Phase 证据",
        "level4": "Part 证据",
        "level1": "Full.md 证据（如有）"
      },
      "impact": "影响程度",
      "priority": "优先级",
      "source_papers": ["文献ID列表"],
      "data_points": ["具体数据点"]
    }
  ]
}
```

---

## Agent 执行计划

### Agent 1：概览扫描 Agent
```
任务：扫描 Phase + Part 层

输入：
- phase1_overview.json
- part1_literature_review.md
- part4_future_work.md
- 8 个领域的 domain_analysis.json

输出：
- 初步研究空白列表
- 候选重点文献列表
- 需要深入挖掘的领域

时间：预计 10-15 分钟
```

### Agent 2：深度分析 Agent
```
任务：系统性扫描 Agent Results 层

输入：
- Agent 1 的输出
- 8 个领域的 agent_results/

输出：
- 细化的研究空白列表
- 每个空白的具体描述
- 跨领域关联分析

时间：预计 20-30 分钟
```

### Agent 3：验证补充 Agent
```
任务：有针对性地阅读 Full.md

输入：
- Agent 2 的输出
- 候选重点文献列表
- data/agent_results/ 目录结构

输出：
- 验证后的研究空白列表
- 每个空白的详细描述和数据支撑
- 核心文献清单

时间：预计 30-40 分钟（取决于需要阅读的文献数量）
```

### Agent 4：结构化输出 Agent
```
任务：分类、排序、生成 JSON

输入：
- Agent 3 的输出
- 分类标准
- 优先级标准

输出：
- research_gaps_extracted.json
- 研究空白总结报告

时间：预计 5-10 分钟
```

---

## 质量控制

### 检查点 1：数据完整性
- [ ] 每个研究空白都有明确的数据来源
- [ ] 数据来源至少包含 Level 2/3/4 中的两层
- [ ] 核心空白有 Level 1（Full.md）支撑

### 检查点 2：相关性验证
- [ ] 所有空白都与"大型风机气动"直接相关
- [ ] 排除了纯结构、纯控制、纯经济的问题
- [ ] 重点关注 10MW+、20MW+ 风机特有问题

### 检查点 3：逻辑一致性
- [ ] Part、Phase、Agent Results 的结论一致
- [ ] 没有矛盾的表述
- [ ] 数据点准确（不夸大、不缩小）

---

## 时间估算

| 阶段 | Agent | 预计时间 |
|-----|-------|---------|
| 阶段一 | 概览扫描 Agent | 10-15 分钟 |
| 阶段二 | 深度分析 Agent | 20-30 分钟 |
| 阶段三 | 验证补充 Agent | 30-40 分钟 |
| 阶段四 | 结构化输出 Agent | 5-10 分钟 |
| **总计** | | **65-95 分钟** |

---

## 执行指令

```bash
# 启动数据挖掘流程
python scripts/data_mining_coordinator.py \
  --mode systematic \
  --target "large_wind_turbine_aerodynamics" \
  --output data/ppt_helper/processed/research_gaps_extracted.json
```

---

**版本**: v1.0
**创建时间**: 2026-03-30
**核心理念**: 像人类研究者一样，从概览到深入，有目的性地挖掘数据
