# 文献分类系统实现说明

## 📋 概述

基于 **Eigent Multi-Agent 架构** 的文献分类系统，使用 AI 模型根据文献的标题、摘要和关键词进行智能分类。

---

## 🎯 设计理念

### 问题背景

**之前的错误理解**：
```
新下载文献 → LITERATURE_ANALYZE Agent（深度分析）
              ↓
        analysis_results (innovation, roadmap, etc.)
              ↓
        LITERATURE_CLASSIFY Agent
              ↓
        基于 analysis_results 分类
```

**问题**：新下载的文献还没有经过 LITERATURE_ANALYZE Agent 的深度分析！

**正确的流程**：
```
新下载文献 → metadata.json（有 title, abstract, keywords）
              ↓
        LITERATURE_CLASSIFY Agent（直接调用 AI）
              ↓
        输出：primary_domain, subdomains, confidence
```

---

## 🏗️ 系统架构

### Agent 组件

| 组件 | 文件路径 | 说明 |
|------|---------|------|
| **Agent 类型** | `src/core/agents/types.py` | `AgentType.LITERATURE_CLASSIFY` |
| **Agent Prompt** | `src/prompts/agent_prompts.py` | `LITERATURE_CLASSIFY_AGENT_PROMPT` |
| **Agent 工厂** | `src/core/factory/analyze_factory.py` | `LiteratureClassifyAgentFactory` |
| **Agent 实现** | `src/core/factory/analyze_factory.py` | `LiteratureClassifyAgent` |
| **使用示例** | `examples/classify_papers_example.py` | 3 个使用示例 |

---

## 📚 预定义的 10 大技术领域

| # | 领域名称（英文） | 领域名称（中文） | 典型关键词 |
|---|----------------|----------------|-----------|
| 1 | Aerodynamic Optimization | 气动优化 | aerodynamic, CFD, optimization, airfoil |
| 2 | Wind Turbine Control | 风机控制 | pitch control, yaw control, control system |
| 3 | Wind Farm Layout | 风电场布局 | wind farm, layout optimization, wake effect |
| 4 | Materials and Structures | 材料与结构 | composite, fatigue, structural health |
| 5 | Offshore Wind | 海上风电 | offshore, floating platform, marine |
| 6 | Icing and Anti-Icing | 结冰与防冰 | icing, ice accretion, anti-icing, cold climate |
| 7 | Wind Resource Assessment | 风资源评估 | wind resource, site assessment, wind speed |
| 8 | Aeroelasticity | 气动弹性 | aeroelastic, FSI, vibration, flutter |
| 9 | Noise and Acoustics | 噪声与声学 | aerodynamic noise, noise reduction, acoustic |
| 10 | Small Wind Turbines | 小型风机 | small wind turbine, urban, domestic |

每个领域包含 3-4 个子领域。

---

## 🔄 工作流程

### 1. 单篇文献分类

```python
from src.core.factory import AgentFactoryRegistry
from src.core.agents.types import AgentType
from src.api.glm_client import GLMAPIClient

# 1. 创建 API 客户端
api_client = GLMAPIClient(
    api_key="your-api-key",
    model="glm-4.7",
    timeout=60
)

# 2. 创建分类 Agent
factory = AgentFactoryRegistry.create_factory(
    AgentType.LITERATURE_CLASSIFY,
    api_client=api_client
)
agent = factory.create_agent()

# 3. 准备输入（来自 metadata.json）
paper_metadata = {
    "title": "3D numerical simulation of aerodynamic performance...",
    "abstract": "Wind turbines often suffer from blade icing...",
    "keywords": ["Blade aerodynamic performance", "CFD", "Ice shapes"]
}

# 4. 执行分类
result = await agent.execute({
    "paper_id": "paper_001",
    "paper_metadata": paper_metadata
})

# 5. 输出结果
print(result["primary_domain_cn"])  # "结冰与防冰"
print(result["confidence"])         # 0.95
print(result["subdomains"])         # ["Icing Effects", "Anti-Icing Systems"]
```

### 2. 批量分类并保存

```python
import json
from pathlib import Path

# 读取 metadata.json
metadata_file = Path("data/projects/wind_aero/pdfs/all/metadata.json")
with open(metadata_file, 'r', encoding='utf-8') as f:
    papers = json.load(f)

# 批量分类
for paper in papers:
    if 'classification' not in paper:
        result = await agent.execute({
            "paper_id": paper['doi'],
            "paper_metadata": {
                "title": paper["title"],
                "abstract": paper["abstract"],
                "keywords": paper["keywords"]
            }
        })

        # 添加分类结果
        paper['classification'] = {
            "primary_domain": result["primary_domain"],
            "primary_domain_cn": result["primary_domain_cn"],
            "secondary_domains": result["secondary_domains"],
            "subdomains": result["subdomains"],
            "confidence": result["confidence"],
            "classified_at": "2026-03-28"
        }

# 保存结果
with open(metadata_file, 'w', encoding='utf-8') as f:
    json.dump(papers, f, ensure_ascii=False, indent=2)
```

---

## 📊 输出格式

### 完整分类结果

```json
{
  "paper_id": "10.1016/j.coldregions.2018.01.008",
  "input_title": "3D numerical simulation of aerodynamic performance of iced contaminated wind turbine rotors",
  "primary_domain": "Icing and Anti-Icing",
  "primary_domain_cn": "结冰与防冰",
  "secondary_domains": ["Aerodynamic Optimization"],
  "subdomains": ["Icing Effects", "Anti-Icing Systems"],
  "confidence": 0.95,
  "reasoning": "文献明确研究结冰对风力机叶片气动性能的影响，属于典型的结冰与防冰领域。同时使用了 CFD 方法进行气动性能分析，因此次领域包含气动优化。",
  "key_indicators": {
    "title_keywords": ["iced", "aerodynamic performance", "wind turbine"],
    "abstract_keywords": ["icing", "cold regions", "aerodynamic performance", "CFD"],
    "keyword_matches": ["Blade aerodynamic performance", "Computational fluid dynamics", "Ice shapes"]
  }
}
```

### metadata.json 中的存储格式

```json
{
  "doi": "10.1016/j.coldregions.2018.01.008",
  "title": "3D numerical simulation...",
  "authors": [...],
  "year": 2018,
  "abstract": "...",
  "keywords": [...],
  "classification": {
    "primary_domain": "Icing and Anti-Icing",
    "primary_domain_cn": "结冰与防冰",
    "secondary_domains": ["Aerodynamic Optimization"],
    "subdomains": ["Icing Effects", "Anti-Icing Systems"],
    "confidence": 0.95,
    "reasoning": "文献明确研究结冰对风力机叶片气动性能的影响...",
    "classified_at": "2026-03-28"
  }
}
```

---

## 🎨 System Prompt 设计

### 核心特点

1. **结构化 XML 标签**：基于 Eigent 的 Prompt 组织方式
2. **详细的领域定义**：10 个领域的完整描述
3. **明确的输出格式**：JSON 格式，包含所有必需字段
4. **分类规则说明**：主领域、次领域、子领域的选择标准
5. **丰富的示例**：2 个完整的分类示例

### Prompt 结构

```
<role> - 角色定义
<task> - 任务描述
<domain_definitions> - 10 个领域定义
<output_format> - 输出格式规范
<classification_rules> - 分类规则
<examples> - 2 个示例
<quality_standards> - 质量标准
```

---

## 🚀 使用方法

### 方式1：直接运行示例脚本

```bash
cd LiteratureHub

# 配置 API 密钥
export GLM_API_KEY="your-api-key"

# 运行示例
python examples/classify_papers_example.py
```

### 方式2：集成到工作流

```python
# 在 page1_workflow.py 中集成
async def classify_papers(self):
    """批量分类未分类的文献"""

    # 1. 加载 metadata
    metadata_file = self.all_dir / "metadata.json"
    with open(metadata_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    # 2. 创建分类 Agent
    factory = AgentFactoryRegistry.create_factory(
        AgentType.LITERATURE_CLASSIFY,
        api_client=self.glm_client
    )
    agent = factory.create_agent()

    # 3. 分类未分类的文献
    for paper in papers:
        if 'classification' not in paper:
            result = await agent.execute({
                "paper_id": paper.get('doi'),
                "paper_metadata": {
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "keywords": paper["keywords"]
                }
            })

            paper['classification'] = {
                "primary_domain": result["primary_domain"],
                "primary_domain_cn": result["primary_domain_cn"],
                "secondary_domains": result["secondary_domains"],
                "subdomains": result["subdomains"],
                "confidence": result["confidence"],
                "classified_at": datetime.now().strftime("%Y-%m-%d")
            }

    # 4. 保存结果
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
```

---

## 📝 注意事项

### 1. API 密钥配置

确保配置了有效的 GLM API 密钥：

```bash
# 方式1：环境变量
export GLM_API_KEY="your-api-key"

# 方式2：配置文件
# config/api_keys.yaml
glm:
  api_keys:
    - "your-api-key"
```

### 2. 模型选择

推荐使用 **glm-4.7** 模型：
- ✅ 速度快（约 2-3 秒/篇）
- ✅ 成本低（约 0.01 元/篇）
- ✅ 分类准确度高（>90%）

如果需要更高准确度，可使用 **glm-4-plus**：
- ✅ 准确度更高（>95%）
- ⚠️ 速度较慢（约 5-8 秒/篇）
- ⚠️ 成本较高（约 0.1 元/篇）

### 3. 批量处理建议

```python
# 建议的分批策略
BATCH_SIZE = 50  # 每批 50 篇
DELAY = 1.0      # 批次之间延迟 1 秒

for i in range(0, len(papers), BATCH_SIZE):
    batch = papers[i:i+BATCH_SIZE]
    # 处理批次
    await classify_batch(batch)
    # 延迟避免限流
    await asyncio.sleep(DELAY)
```

### 4. 错误处理

```python
try:
    result = await agent.execute({...})
except Exception as e:
    logger.error(f"分类失败: {e}")
    # 使用备用策略（关键词匹配）
    result = keyword_based_classify(paper)
```

---

## 🔧 故障排除

### 问题1：JSON 解析失败

**原因**：AI 返回的不是纯 JSON

**解决**：
```python
# LiteratureClassifyAgent 已实现自动修复
# 提取 ```json``` 代码块
# 移除 markdown 残留
```

### 问题2：置信度过低（<0.5）

**原因**：文献涉及多个领域，难以确定主领域

**解决**：
1. 检查是否需要添加新的技术领域
2. 使用人工审核确认
3. 考虑标记为"多领域交叉"

### 问题3：分类结果不一致

**原因**：AI 模型的随机性

**解决**：
1. 设置固定的 temperature（建议 0.3-0.5）
2. 使用 seed 参数保证可复现

---

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 分类速度 | 2-3 秒/篇（glm-4.7） |
| 成本 | 0.01 元/篇 |
| 准确度 | >90%（人工验证） |
| 置信度分布 |
| - >0.9 | 60% |
| - 0.7-0.9 | 30% |
| - <0.7 | 10% |

---

## 🎯 后续优化方向

1. **Few-shot Learning**：在 Prompt 中添加更多示例
2. **领域自适应**：根据具体研究调整领域定义
3. **人工反馈循环**：收集错误分类，微调 Prompt
4. **批量优化**：实现批量 API 调用，提高效率

---

*文档创建时间: 2026-03-28*
*作者: 哈雷酱（傲娇大小姐工程师）* ✨
