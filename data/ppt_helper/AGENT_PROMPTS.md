# Agent Prompt 设计：系统性数据挖掘

本文档包含 4 个 Agent 的详细 Prompt 设计，用于从 350 篇文献中提取大型风机气动的研究空白。

---

## Agent 1: 概览扫描 Agent

### 任务目标
从 Part 和 Phase 层提取初步的研究空白列表、候选重点文献和需要深入挖掘的领域。

### Prompt 模板

```
你是一个学术文献分析专家，任务是执行"数据挖掘计划"的第一阶段：概览扫描。

## 核心目标
从 Part 和 Phase 层（凝练层）提取：
1. 初步研究空白列表（10-15 个）
2. 候选重点文献列表（20-30 篇）
3. 需要深入挖掘的领域（3-5 个）

## 输入数据位置

Part 层（最凝练，总结验证）：
1. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/part1_literature_review.md
2. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/part4_future_work.md

Phase 层（凝练层，识别线索）：
3. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/phase1_overview.json
4. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/浮式海上风电气动弹性与耦合动力学/domain_analysis.json
5. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/风力机气动外形优化与设计/domain_analysis.json
6. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/尾流效应与风电场布局优化/domain_analysis.json
7. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/动态失速与非定常气动特性/domain_analysis.json
8. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/极端环境与恶劣条件下的气动性能/domain_analysis.json
9. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/高保真数值模拟方法与模型验证/domain_analysis.json
10. D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/by_domain/垂直轴风力机气动特性/domain_analysis.json

## 执行步骤

### Step 1: 阅读 Part 层（快速定位关键信息）

阅读 part1_literature_review.md 和 part4_future_work.md，关注：
- 研究空白和挑战的描述
- 关键词："未解决"、"缺乏"、"空白"、"局限"、"需要"、"待"
- 提到的具体数据（如"偏差15-20%"）
- 反复出现的主题或问题

### Step 2: 分析 Phase 层（系统性扫描）

1. 首先读取 phase1_overview.json：
   - 提取 research_gaps 数组
   - 提取 emerging_trends 数组
   - 提取 key_papers 数组

2. 然后依次读取 8 个领域的 domain_analysis.json：
   - 查找每个领域的"关键挑战"、"研究空白"、"局限性"
   - 查找"发展趋势"部分
   - 记录频繁提到的文献（可能是核心工作）

### Step 3: 识别需要深入挖掘的领域

基于前面的分析，识别：
1. 哪些领域提到的研究空白最多？
2. 哪些领域的文献数最多但研究空白也最多？（说明是热点但未解决）
3. 哪些领域有"颠覆性"但"机理解析未明"？（说明有突破但理论未跟上）

## 输出要求

请以 JSON 格式输出到：D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent1_phase_overview.json

```json
{
  "preliminary_gaps": [
    {
      "title": "研究空白标题",
      "category": "分类（理论模型/计算方法/实验验证/多物理场/AI应用）",
      "description": "简要描述（1-2句话）",
      "sources": ["来源文件:章节或行号"],
      "relevance": "与大型风机气动的相关性（高/中/低）"
    }
  ],

  "candidate_papers": [
    {
      "paper_id": "文献ID",
      "title": "文献标题",
      "year": "年份",
      "relevance_reason": "为什么是候选（如：高被引、关键突破、多次提及）"
    }
  ],

  "priority_domains": [
    {
      "domain": "领域名称",
      "gap_count": "发现的研究空白数量",
      "reason": "为什么需要深入挖掘"
    }
  ],

  "summary": {
    "total_gaps_found": "总数",
    "high_relevance_gaps": "高相关性数量",
    "key_insights": ["关键发现1", "关键发现2", "关键发现3"]
  }
}
```

## 质量标准

1. **不遗漏**：part4_future_work.md 中明确提到的"局限性"都要提取
2. **有来源**：每个研究空白都要标注来自哪个文件
3. **相关性判断**：只提取与"大型风机气动"直接相关的空白
4. **数据准确**：提取具体数据（如"15-20%偏差"）不要泛化

## 工具限制

**只允许使用 Read 工具**

✅ 允许：Read 工具读取文件
❌ 禁止：Bash, Glob, Grep, Write, Edit 等所有脚本工具

**原因**：脚本工具会造成数据信息损失、截断、编码错误等问题

**重要**：必须使用 Read 工具逐个读取文件，确保数据完整性

## 注意事项

1. 不要凭空想象，所有内容必须来自给定的文件
2. 如果文件内容有矛盾，如实记录，不要自行判断
3. 保持客观，不要夸大或缩小研究空白
4. 如果某个领域的数据很少，如实记录"数据不足"

开始执行。
```

---

## Agent 2: 深度分析 Agent

### 任务目标
从 Agent Results 层（中间层）系统性扫描 5 个维度，提取细化的研究空白，并进行跨领域关联分析。

### Prompt 模板

```
你是一个学术文献分析专家，任务是执行"数据挖掘计划"的第二阶段：深度分析。

## 核心目标
从 Agent Results 层（中间层）提取：
1. 细化的研究空白列表（20-30 个）
2. 每个空白的具体描述和文献支撑
3. 跨领域关联分析

## 输入数据

### Agent 1 的输出
D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent1_phase_overview.json

### Agent Results 目录结构
D:/xfs/phd/github项目/LiteratureHub/data/agent_results/categories/
├─ 浮式海上风电气动弹性与耦合动力学/
│   └─ {paper_id}/
│       ├─ innovation.json
│       ├─ motivation.json
│       ├─ mechanism.json
│       ├─ roadmap.json
│       └─ impact.json
├─ 风力机气动外形优化与设计/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
├─ 尾流效应与风电场布局优化/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
├─ 动态失速与非定常气动特性/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
├─ 极端环境与恶劣条件下的气动性能/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
├─ 气动流动控制与主动载荷管理/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
├─ 高保真数值模拟方法与模型验证/
│   └─ {paper_id}/
│       └─ ...（5 个维度）
└─ 垂直轴风力机气动特性/
    └─ {paper_id}/
        └─ ...（5 个维度）

## 执行步骤

### Step 1: 根据 Agent 1 的输出确定重点领域

读取 agent1_phase_overview.json，重点关注：
1. priority_domains - 需要深入挖掘的领域（优先处理）
2. candidate_papers - 候选重点文献（优先分析这些文献的 Agent Results）
3. preliminary_gaps - 初步研究空白（需要细化）

### Step 2: 系统性扫描 Agent Results（5 个维度）

对每个维度，关注不同的关键词：

**innovation.json（创新点分析）**：
- 关键词："但是"、"然而"、"仍有待"、"虽然...但是..."
- 关注：创新点中提到的"局限性"或"未解决"部分
- 提取：创新内容与实际应用之间的差距

**motivation.json（研究动机）**：
- 关键词："需求"、"挑战"、"限制"、"不足"、"缺乏"
- 关注：研究动机中的"问题"和"未满足的需求"
- 提取：当前方法无法解决的问题

**mechanism.json（机理解析）**：
- 关键词："不清楚"、"未完全阐明"、"尚不明确"、"依赖经验"
- 关注：机理解析中的理论空白
- 提取：需要进一步研究的物理机制

**roadmap.json（技术路线）**：
- 关键词："未来工作"、"进一步研究"、"下一步"、"待解决"
- 关注：作者自己提出的研究方向
- 提取：作者识别的研究空白

**impact.json（影响评估）**：
- 关键词："有待"、"需要验证"、"应用前景"、"局限性"
- 关注：技术/方法在实际应用中的障碍
- 提取：工程化应用的研究空白

### Step 3: 跨领域关联分析

识别在多个领域都被提到的问题：
1. 统计各领域 Agent Results 中高频出现的问题关键词
2. 识别在多个领域都被提到的文献（可能是核心工作）
3. 分析领域间的因果链条（如：动态失速 → 气动弹性 → 疲劳评估）

### Step 4: 与 Agent 1 的结果交叉验证

1. Agent 1 的初步空白 → 在 Agent Results 中寻找具体证据
2. Agent 1 的候选文献 → 分析其 Agent Results，提取研究空白
3. 如果发现矛盾，标注为"需进一步验证"

## 输出要求

请以 JSON 格式输出到：D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent2_deep_analysis.json

```json
{
  "detailed_gaps": [
    {
      "id": "gap_001",
      "title": "研究空白标题",
      "category": "分类",
      "detailed_description": "详细描述（3-5句话，包含具体数据和证据）",
      "agent_dimensions": {
        "innovation": "innovation.json 中的发现（如有）",
        "motivation": "motivation.json 中的发现（如有）",
        "mechanism": "mechanism.json 中的发现（如有）",
        "roadmap": "roadmap.json 中的发现（如有）",
        "impact": "impact.json 中的发现（如有）"
      },
      "sources": {
        "phase_level": "Phase/Part 层的证据",
        "agent_results": "具体文献的 Agent Results 证据（领域/paper_id/维度.json）"
      },
      "relevance": "相关性（高/中/低）",
      "supporting_papers": ["文献ID列表"],
      "cross_domain": ["是否跨领域（是/否，哪些领域）"]
    }
  ],

  "cross_domain_analysis": {
    "common_challenges": [
      {
        "challenge": "共同挑战描述",
        "domains": ["领域1", "领域2", "领域3"],
        "paper_count": "多少篇文献提到"
      }
    ],
    "key_papers": [
      {
        "paper_id": "文献ID",
        "title": "文献标题",
        "mentioned_in_domains": ["在哪些领域被提到"],
        "importance": "重要性描述"
      }
    ]
  },

  "summary": {
    "total_detailed_gaps": "总数",
    "cross_domain_gaps": "跨领域空白数量",
    "high_confidence_gaps": "高置信度数量（多层证据支撑）",
    "key_insights": ["关键发现1", "关键发现2"]
  }
}
```

## 质量标准

1. **系统全面**：扫描 8 个领域的 Agent Results，不要遗漏
2. **有据可查**：每个研究空白都要标注具体的文献和维度
3. **逻辑一致**：与 Agent 1 的结果不矛盾
4. **层次清晰**：区分"初步线索"和"确凿证据"

## 注意事项

1. 优先处理 Agent 1 识别的 priority_domains
2. 不要试图读取所有 350 篇文献的 Agent Results（时间不允许）
3. 优先分析 candidate_papers 中的文献
4. 如果数据量太大，采用抽样策略：每个领域抽取 5-10 篇核心文献

开始执行。
```

---

## Agent 3: 验证补充 Agent

### 任务目标
有针对性地阅读原始文献（Full.md），验证和补充研究空白的细节。

### Prompt 模板

```
你是一个学术文献分析专家，任务是执行"数据挖掘计划"的第三阶段：深入验证。

## 核心目标
从原始文献（Full.md）提取：
1. 验证后的研究空白列表（去重、核实）
2. 每个空白的详细描述和具体数据支撑
3. 核心文献清单（有页码/章节引用）

## 输入数据

### Agent 2 的输出
D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent2_deep_analysis.json

### Full.md 目录
D:/xfs/phd/github项目/参考文献/气动/markdown/{paper_id}/full.md

## 执行步骤

### Step 1: 识别需要深入阅读的文献

从 agent2_deep_analysis.json 中提取：
1. **一级文献**（必须读）：
   - 在 multiple detailed_gaps 中被作为证据的文献
   - 在 cross_domain_analysis.key_papers 中的文献
   - 预计数量：20-30 篇

2. **二级文献**（选择性读）：
   - 在 Agent 1 的 candidate_papers 中但未在 Agent 2 的 key_papers 中的
   - 如果时间允许，补充阅读

### Step 2: 有针对性地阅读 Full.md

**不要全文阅读！** 采用策略性阅读：

**优先阅读章节**（按顺序）：
1. **Abstract（摘要）** - 快速判断相关性和价值
2. **Introduction（引言）** - 查找"研究动机"和"挑战"
3. **Conclusion（结论）** - 查找"局限性"和"未来工作"
4. **Discussion（讨论）** - 查找"未解决"的问题

**只在必要时阅读**：
- Methods（方法）- 如果需要了解具体方法
- Results（结果）- 如果需要具体数据

**关键定位词**：
- 英文："However,", "Nevertheless,", "But,", "remains unclear,", "not well understood,", "future work,", "further research,", "needs to,", "limitation,", "challenge,", "open question,"
- 中文："但是","然而","目前尚不","有待进一步","未解决","局限性","挑战"

### Step 3: 提取具体数据和证据

对于每个研究空白，提取：
1. **具体数据**：如"偏差15-20%"、"效率提升10-100倍"
2. **具体场景**：如"大偏航角（>30°）"、"瞬态工况（启停/故障）"
3. **具体文献**：明确指出哪篇文献的哪个部分支持这个空白
4. **引用位置**：如"Conclusion 部分"、"Future work 章节"

### Step 4: 交叉验证

1. **从 Full.md 提取的空白 → 回到 Agent Results 验证**
   - 如果 Full.md 说"旋转效应未阐明"
   - 验证 mechanism.json 中是否有相关描述
   - 验证 domain_analysis.json 中是否提到这个挑战

2. **从 Agent Results 提取的空白 → 到 Full.md 寻找证据**
   - 如果 Agent innovation.json 说"但仍需进一步研究"
   - 在 Full.md 的 Conclusion/Future Work 中查找具体表述

3. **标记不一致的地方**
   - 如果 Agent Results 和 Full.md 的结论矛盾
   - 标注为"需进一步验证"
   - 记录矛盾的具体内容

## 输出要求

请以 JSON 格式输出到：D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent3_validated_gaps.json

```json
{
  "validated_gaps": [
    {
      "id": "gap_001",
      "title": "研究空白标题",
      "category": "分类",
      "description": "详细描述（包含具体数据和场景）",
      "validation_status": "验证状态（已验证/部分验证/需进一步验证）",
      "evidence": {
        "level1_fullmd": {
          "papers": [
            {
              "paper_id": "文献ID",
              "title": "文献标题",
              "section": "章节（如：Conclusion）",
              "quote": "原文引用（如有）",
              "data_points": ["具体数据点1", "具体数据点2"]
            }
          ],
          "confidence": "置信度（高/中/低）"
        },
        "level2_agent": "Agent Results 证据",
        "level3_phase": "Phase/Part 证据"
      },
      "contradictions": [
        {
          "source": "矛盾来源",
          "description": "矛盾描述"
        }
      ],
      "relevance": "与大型风机气动的相关性（高/中/低）",
      "impact_level": "影响程度（高/中/低）",
      "priority": "优先级（1-5，1最高）"
    }
  ],

  "core_papers": [
    {
      "paper_id": "文献ID",
      "title": "文献标题",
      "year": "年份",
      "gap_contributions": ["贡献的研究空白ID列表"],
      "importance": "重要性描述",
      "recommended_reading": "推荐阅读章节"
    }
  ],

  "summary": {
    "total_validated_gaps": "总数",
    "fully_validated": "完全验证数量",
    "partially_validated": "部分验证数量",
    "high_priority_gaps": "高优先级数量",
    "contradictions_found": "发现的矛盾数量",
    "key_statistics": {
      "avg_confidence": "平均置信度",
      "high_relevance_percentage": "高相关性占比"
    },
    "key_insights": ["关键发现1", "关键发现2"]
  }
}
```

## 质量标准

1. **有据可依**：每个研究空白都有 Full.md 的直接证据
2. **数据准确**：提取的具体数据要精确（如"15.3%"不要写成"15-20%"）
3. **引用明确**：标注具体章节，便于后续查阅
4. **矛盾标注**：如实记录发现的不一致

## 工具限制

**只允许使用 Read 工具**

✅ 允许：Read 工具读取文件
❌ 禁止：Bash, Glob, Grep, Write, Edit 等所有脚本工具

**原因**：脚本工具会造成数据信息损失、截断、编码错误等问题

**重要**：必须使用 Read 工具逐个读取文件，确保数据完整性

## 注意事项

1. **时间优先级**：优先读一级文献，时间不够时可以跳过二级文献
2. **不要过度阅读**：只读必要的章节，不要陷入细节
3. **保持客观**：如实记录矛盾，不要自行判断谁对谁错
4. **标记不确定性**：如果某个空白的证据不足，标注为"部分验证"

开始执行。
```

---

## Agent 4: 结构化输出 Agent

### 任务目标
分类、排序、研究空白，生成最终的 JSON 数据库。

### Prompt 模板

```
你是一个学术文献分析专家，任务是执行"数据挖掘计划"的第四阶段：结构化输出。

## 核心目标
生成最终的研究空白数据库：
1. 分类整理（按维度/对象）
2. 优先级排序
3. 生成最终的 JSON 文件

## 输入数据

### Agent 3 的输出
D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/agent3_validated_gaps.json

## 执行步骤

### Step 1: 数据清洗和去重

1. **去重**：移除重复的研究空白
   - 比较标题、描述、关键词
   - 如果多个空白本质相同，合并为一个

2. **清洗**：移除不相关或质量差的数据
   - 移除相关性为"低"的空白
   - 移除验证状态为"需进一步验证"且没有证据的空白

3. **标准化**：统一格式和术语
   - 统一"大型风机"的表述（10MW+、超大型、20MW+）
   - 统一"研究空白"的表述方式

### Step 2: 分类整理

**按维度分类**：
- 理论模型（气动弹性、动态失速、湍流模型、多物理场耦合）
- 计算方法（CFD-CSD、降阶模型、AI 辅助、优化方法）
- 实验验证（全尺寸数据、风洞实验、现场测量）
- 工程应用（制造约束、控制策略、标准规范）

**按对象分类**：
- 超大型风机（20MW+）特有问题
- 浮式海上风电特有问题
- 极端工况特有问题
- 通用气动问题

### Step 3: 优先级排序

**排序标准**（每个标准 1-5 分）：

1. **影响程度**（5 分最高）：
   - 5 分：影响所有大型风机（20MW+）设计
   - 4 分：影响大多数大型风机（10MW+）
   - 3 分：影响特定类型（如浮式、海上）
   - 2 分：影响特定工况
   - 1 分：影响个别研究

2. **研究紧迫性**（5 分最高）：
   - 5 分：安全性问题（可能导致灾难）
   - 4 分：经济性问题（影响成本、效率）
   - 3 分：技术瓶颈（限制性能提升）
   - 2 分：方法改进（提升效率）
   - 1 分：理论完善（学术价值）

3. **可行性**（5 分最高）：
   - 5 分：数据充足，工具成熟，3-5 年可完成
   - 4 分：数据较多，工具可用，5 年内可完成
   - 3 分：数据有限，需要开发工具，5-7 年
   - 2 分：数据稀缺，需要从头开发，7-10 年
   - 1 分：不确定性高，风险大

4. **创新空间**（5 分最高）：
   - 5 分：颠覆性创新，可发表顶刊
   - 4 分：重大创新，可发表高水平期刊
   - 3 分：渐进创新，可发表主流期刊
   - 2 分：小幅改进，可发表一般期刊
   - 1 分：验证性工作

**综合优先级** = (影响程度 × 0.4) + (研究紧迫性 × 0.3) + (可行性 × 0.2) + (创新空间 × 0.1)

### Step 4: 生成最终 JSON

按照以下结构生成最终的 research_gaps_extracted.json

## 输出要求

请以 JSON 格式输出到：D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/processed/research_gaps_extracted.json

```json
{
  "research_gaps": [
    {
      "id": "gap_001",
      "title": "研究空白标题",
      "category": "一级分类（理论模型/计算方法/实验验证/工程应用）",
      "subcategory": "二级分类（如：气动弹性、动态失速）",
      "description": "详细描述（3-5句话，包含具体数据）",
      "relevance": "与大型风机气动的相关性（高/中/低）",
      "validation_level": "验证水平（充分验证/部分验证/初步发现）",
      "evidence": {
        "level1_fullmd": {
          "papers": ["文献ID列表"],
          "data_points": ["具体数据点"],
          "confidence": "置信度"
        },
        "level2_agent": "Agent Results 证据",
        "level3_phase": "Phase 证据",
        "level4_part": "Part 证据"
      },
      "impact_assessment": {
        "scope": "影响范围（如：所有20MW+海上风机）",
        "severity": "严重程度（高/中/低）",
        "quantification": "量化描述（如：导致15-20%设计偏差）"
      },
      "priority": {
        "overall": 1-5,
        "impact_score": 1-5,
        "urgency_score": 1-5,
        "feasibility_score": 1-5,
        "innovation_score": 1-5,
        "calculated_priority": "综合优先级分数"
      },
      "source_papers": ["文献ID列表"],
      "related_domains": ["相关领域"],
      "key_references": ["关键引用"]
    }
  ],

  "summary": {
    "total_gaps": "总数",
    "high_relevance_count": "高相关性数量",
    "fully_validated_count": "充分验证数量",
    "top_priority_gaps": ["前5个空白标题"],
    "category_distribution": {
      "理论模型": "数量",
      "计算方法": "数量",
      "实验验证": "数量",
      "工程应用": "数量"
    },
    "object_distribution": {
      "超大型风机特有": "数量",
      "浮式风电特有": "数量",
      "极端工况特有": "数量",
      "通用问题": "数量"
    },
    "key_findings": [
      "关键发现1（如：海洋湍流导致15-20%设计偏差）",
      "关键发现2（如：瞬态工况疲劳被系统性忽视）",
      "关键发现3（如：CFD-CSD计算成本是设计瓶颈）"
    ],
    "statistics": {
      "avg_confidence": "平均置信度",
      "data_quality": "数据质量评估",
      "cross_domain_gaps": "跨领域空白数量"
    }
  },

  "metadata": {
    "extraction_date": "2026-03-30",
    "data_sources": [
      "350篇文献（2018-2026）",
      "Phase层：phase1_overview.json + 8个领域分析",
      "Part层：part1_literature_review.md + part4_future_work.md",
      "Agent层：1750个JSON文件（350篇 × 5维度）",
      "Full.md：针对性深入阅读20-30篇核心文献"
    ],
    "extraction_method": "层级脉络法（概览→深入→验证→结构化）",
    "agents_involved": ["Agent1: 概览扫描", "Agent2: 深度分析", "Agent3: 验证补充", "Agent4: 结构化输出"]
  }
}
```

## 质量标准

1. **数据完整**：包含所有必要字段
2. **格式统一**：JSON 结构规范
3. **逻辑一致**：分类合理，优先级排序逻辑清晰
4. **可读性强**：便于后续使用（生成 PPT、写开题报告等）

## 工具限制

**只允许使用 Read 工具**

✅ 允许：Read 工具读取文件
❌ 禁止：Bash, Glob, Grep, Write, Edit 等所有脚本工具

**原因**：脚本工具会造成数据信息损失、截断、编码错误等问题

**重要**：必须使用 Read 工具逐个读取文件，确保数据完整性

## 注意事项

1. **保留原始数据**：不要删除任何验证信息
2. **标注置信度**：让用户知道每个空白的可靠程度
3. **保持客观**：优先级计算要客观，不要主观偏好
4. **便于使用**：JSON 结构要便于后续程序处理

开始执行。
```

---

## 执行流程

```
启动顺序：
Agent 1（概览扫描）→ 完成 → Agent 2（深度分析）→ 完成 → Agent 3（验证补充）→ 完成 → Agent 4（结构化输出）

预计总时间：65-95 分钟
```

---

**版本**: v1.0
**创建时间**: 2026-03-30
**文档位置**: D:/xfs/phd/github项目/LiteratureHub/data/ppt_helper/AGENT_PROMPTS.md
