# LiteratureHub - 统一学术文献研究与汇报系统

**版本**: v1.0.0-alpha
**状态**: ✅ 核心功能已完成，可正常使用
**创建日期**: 2026-03-27
**最后更新**: 2026-03-30
**基于**: [Eigent](https://github.com/eigent-ai/eigent) Multi-Agent 架构设计

---

## 📋 项目简介

LiteratureHub 是一个面向博士研究的全流程文献管理与智能汇报系统，集成了文献搜索、智能分析、PPT 生成等功能，基于 **Eigent Multi-Agent 架构** 设计。

### 核心特性

✅ **类型安全的 Agent 系统**：基于枚举的 Agent 类型定义（8种专业化Agent）
✅ **多源文献搜索**：支持 Elsevier、arXiv、IEEE、Springer 等多个数据库
✅ **智能下载系统**：Unpaywall（合法）优先 + SciHub 备用
✅ **AI 深度分析**：6维度分析（创新点/动机/机理/影响/脉络/路线）
✅ **智能分类系统**：10大技术领域，AI自动分类
✅ **中文友好界面**：完整的 GUI 系统，支持中文关键词
✅ **MinerU 集成**：PDF 转 Markdown，保留公式、图表、结构

---

## 🏗️ 架构设计

### Agent 类型系统

LiteratureHub 基于 Eigent Multi-Agent 架构实现了 **8 种专业化 Agent**：

| # | Agent 类型 | 中文名称 | 图标 | 颜色 | 核心职责 | 状态 |
|---|-----------|---------|------|------|---------|------|
| 1 | `LITERATURE_SEARCH` | 文献搜索代理 | 🔍 | `#3B82F6` | 搜索学术数据库 | ✅ 已实现 |
| 2 | `LITERATURE_DOWNLOAD` | 文献下载代理 | ⬇️ | `#10B981` | 批量下载PDF | ✅ 已实现 |
| 3 | `LITERATURE_PARSE` | 文献解析代理 | 📄 | `#F59E0B` | PDF → Markdown | ✅ 已实现 |
| 4 | `LITERATURE_ANALYZE` | 文献分析代理 | 🧠 | `#8B5CF6` | AI深度分析 | ✅ 已实现 |
| 5 | `LITERATURE_CLASSIFY` | 文献分类代理 | 🏷️ | `#EC4899` | AI智能分类 | ✅ 已实现 |
| 6 | `KNOWLEDGE_GRAPH` | 知识图谱代理 | 🕸️ | `#14B8A6` | 构建知识图谱 | 🚧 计划中 |
| 7 | `PPT_GENERATE` | PPT生成代理 | 📊 | `#EF4444` | 生成PPT | 🚧 计划中 |
| 8 | `CITATION_MANAGE` | 引用管理代理 | 💬 | `#F97316` | 管理引用 | 🚧 计划中 |

### 项目结构

```
LiteratureHub/
├── 启动GUI.bat              # Windows 双击启动
├── launch_gui.py            # GUI 启动器
├── requirements.txt         # 依赖列表
├── config/                  # 配置文件
│   ├── api_keys.yaml        # API 密钥配置
│   ├── workflow.yaml        # 工作流配置
│   ├── analysis_agents_config.yaml  # 分析 Agent 配置
│   └── analysis_keywords.yaml       # 技术领域关键词
├── scripts/                 # 运行脚本
│   ├── page1_gui.py         # Page 1 GUI（完整中文界面）
│   └── test_mineru_api.py   # MinerU API 测试
├── src/
│   ├── core/                # 核心模块
│   │   ├── agents/          # Agent 类型系统
│   │   ├── factory/         # Agent 工厂模式
│   │   ├── queue/           # GLM-5 串行队列
│   │   ├── tools/           # 工具集系统
│   │   └── workflow/        # 工作流引擎
│   ├── search/              # 文献搜索
│   │   ├── elsevier_searcher.py
│   │   ├── arxiv_searcher.py
│   │   ├── ieee_searcher.py
│   │   ├── springer_searcher.py
│   │   ├── multi_source_searcher.py
│   │   └── keyword_translator.py
│   ├── download/            # 文献下载
│   │   ├── multi_source_downloader.py
│   │   ├── unpaywall_client.py
│   │   ├── scihub_downloader.py
│   │   ├── proxy_manager.py
│   │   └── vpn_detector.py
│   ├── analysis/            # AI 分析
│   │   ├── ai_analyzer.py
│   │   ├── classifier.py
│   │   ├── scoring.py
│   │   └── manager.py
│   ├── api/                 # API 客户端
│   │   ├── glm_client.py
│   │   └── mineru_client.py
│   ├── workflow/            # 工作流脚本
│   │   ├── page1_workflow.py    # Page 1 完整工作流
│   │   ├── batch_classify.py    # 批量分类
│   │   ├── orchestrator.py      # 编排器
│   │   ├── executor.py          # 执行器
│   │   └── state_tracker.py     # 状态追踪
│   ├── gui/                 # GUI 组件
│   ├── prompts/             # System Prompt 模板
│   └── utils/               # 工具函数
├── data/                    # 数据目录
│   └── projects/            # 项目数据
│       └── wind_aero/       # 示例项目
├── docs/                    # 文档
└── logs/                    # 日志目录
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd LiteratureHub
pip install -r requirements.txt
```

### 2. 配置 API 密钥

编辑 `config/api_keys.yaml`：

```yaml
# Unpaywall 邮箱（用于开放获取文献下载）
unpaywall:
  email: "your-email@example.com"

# Elsevier API（用于文献搜索）
elsevier:
  api_key: "YOUR_ELSEVIER_API_KEY"
  inst_token: ""

# GLM API（用于关键词翻译和 AI 分析）
glm:
  api_keys:
    - "YOUR_GLM_API_KEY"
```

### 3. 启动 GUI

```bash
# 方式1：双击启动（Windows）
启动GUI.bat

# 方式2：命令行启动
python launch_gui.py
```

### 4. GUI 功能流程

1. **Elsevier 搜索** → 输入关键词，支持中文自动翻译
2. **SciHub 下载** → 自动下载 PDF（Unpaywall 优先，SciHub 备用）
3. **处理临时文件** → 处理手动下载的 PDF
4. **文献分类** → AI 智能分类到 10 大技术领域
5. **MinerU 转换** → PDF 转 Markdown（保留公式、图表、结构）

---

## 🎯 功能详解

### 1. 多源文献搜索

支持多个学术数据库：

- ✅ **Elsevier (Scopus)** - 最大的学术数据库之一
- ✅ **arXiv** - 预印本论文库
- ✅ **IEEE Xplore** - 工程技术文献
- ✅ **Springer** - 科学技术期刊
- ✅ **关键词翻译** - 中文关键词自动翻译为英文

### 2. 智能下载系统

多源下载策略：

- ✅ **Unpaywall 优先**（约 20-30% 成功率，合法、免费）
- ✅ **SciHub 备用**（需要 VPN，自动启动 Mihomo）
- ✅ **智能代理管理**（并发测试延迟，自动选择最优）
- ✅ **支持 2024+ 新格式**（已修复 SciHub 新格式支持）

### 3. AI 深度分析

6 个维度的深度分析：

| 维度 | 说明 | 状态 |
|------|------|------|
| 创新点分析 | 创新点三元组（问题+方法+效果） | ✅ 已实现 |
| 研究动机 | 研究动机五问 | ✅ 已实现 |
| 技术路线 | 方法演进、关键技术 | ✅ 已实现 |
| 机理解析 | 物理机制、数学原理 | ✅ 已实现 |
| 影响评估 | 学术影响、工程应用 | ✅ 已实现 |
| 历史脉络 | 领域发展、关键节点 | ✅ 已实现 |

### 4. 智能分类系统

10 大技术领域，AI 自动分类：

1. Aerodynamic Optimization（气动优化）
2. Wind Turbine Control（风机控制）
3. Wind Farm Layout（风电场布局）
4. Materials and Structures（材料与结构）
5. Offshore Wind（海上风电）
6. Icing and Anti-Icing（结冰与防冰）
7. Wind Resource Assessment（风资源评估）
8. Aeroelasticity（气动弹性）
9. Noise and Acoustics（噪声与声学）
10. Small Wind Turbines（小型风机）

### 5. MinerU 集成

PDF 转 Markdown，完整保留文档结构：

- ✅ 支持三种模型版本：pipeline、vlm（推荐）、MinerU-HTML
- ✅ 保留公式、图表、表格
- ✅ 支持批量解析
- ✅ 实时进度显示

---

## 📊 技术栈

- **语言**: Python 3.10+
- **AI 模型**: GLM-4 Plus（智谱 AI）、DeepSeek
- **文献搜索**: pybliometrics (Elsevier Scopus API)
- **文献下载**: Unpaywall（开放获取）、SciHub（备用）
- **浏览器自动化**: Selenium + Chrome DevTools Protocol
- **PDF 解析**: MinerU API（在线服务）
- **配置管理**: PyYAML
- **GUI**: Tkinter
- **开发工具**: black, flake8, mypy

---

## 🔧 配置说明

### API 密钥配置

编辑 `config/api_keys.yaml`：

```yaml
# GLM API（关键词翻译、AI 分析）
glm:
  api_keys:
    - "YOUR_GLM_API_KEY"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  model: "glm-4-plus"

# Elsevier API（文献搜索）
elsevier:
  api_key: "YOUR_ELSEVIER_API_KEY"
  inst_token: ""

# Unpaywall（开放获取文献下载）
unpaywall:
  email: "your-email@example.com"

# DeepSeek API（可选）
deepseek:
  api_key: "YOUR_DEEPSEEK_API_KEY"
  base_url: "https://api.deepseek.com"
```

### 工作流配置

编辑 `config/workflow.yaml`：

```yaml
search:
  databases:
    - "elsevier"
    - "arxiv"
    - "ieee"
  max_results: 100
  year_range:
    start: 2020
    end: 2024

download:
  delay_range:
    min: 1.0
    max: 3.0

analysis:
  dimensions:
    - "innovation"
    - "motivation"
    - "roadmap"
    - "mechanism"
    - "impact"
    - "history"
```

---

## 📝 开发指南

### 添加新的 Agent

1. 在 `src/core/agents/types.py` 中添加新的 `AgentType`
2. 在 `AGENT_REGISTRY` 中配置显示信息
3. 在 `src/core/factory/` 中创建对应的工厂类
4. 在 `src/prompts/agent_prompts.py` 中添加 System Prompt

### 代码风格

- **格式化**: `black src/ scripts/`
- **代码检查**: `flake8 src/ scripts/`
- **类型检查**: `mypy src/`

---

## 🚧 已知限制

1. **SciHub 依赖**：需要 VPN，系统自动启动 Mihomo
2. **MinerU API**：需要网络连接，可能不稳定
3. **GLM API 配额**：需要配置有效的 API 密钥
4. **数据库**：尚未实现，目前使用 JSON 文件存储
5. **知识图谱**：尚未实现（计划使用 LightRAG）
6. **PPT 生成**：尚未实现

---

## 📊 数据资产与 PPT 内容生成

### 信息层级架构

本项目采用**多级信息精炼架构**，从原始 PDF 到最终 PPT 内容共 5 个层级：

```
Level 0: PDF 文献（最原始）
    ↓ MinerU 解析
Level 1: Markdown 全文（full.md）
    ↓ Claude Code Agent 分析
Level 2: Agent 深度分析（innovation, motivation, roadmap, mechanism, impact）
    ↓ 综合提炼
Level 3: Phase 精炼分析（phase1_overview, 8个领域深度分析）
    ↓ 总结生成
Level 4: Part 综合分析（part1-4 对应科研汇报4部分）
    ↓ 最终输出
Level 5: HTML PPT 内容（10 页）
```

### 大型风力机气动研究数据

**研究课题**: 大型风力机气动
**文献基础**: 350 篇核心文献（2018-2026）
**核心领域**: 8 大研究领域
**分析维度**: 5 个（创新点、动机、路线、机理、影响）

#### 八大核心研究领域

| 领域 | 文献数 | 关键问题 |
|-----|-------|---------|
| 浮式海上风电气动弹性与耦合动力学 | 78 篇 | 平台运动-载荷耦合机制 |
| 风力机气动外形优化与设计 | 65 篇 | AI 驱动优化方法 |
| 尾流效应与风电场布局优化 | 52 篇 | 高保真尾流模拟 |
| 动态失速与非定常气动特性 | 48 篇 | 三维旋转效应修正 |
| 极端环境与恶劣条件下的气动性能 | 42 篇 | 结冰/台风工况 |
| 气动流动控制与主动载荷管理 | 38 篇 | 智能载荷控制 |
| 高保真数值模拟方法与模型验证 | 35 篇 | CFD-CSD 紧耦合 |
| 垂直轴风力机气动特性 | 28 篇 | 模块化设计创新 |

#### 五大颠覆性创新

1. **垂直轴"块状"叶片布局** - 效率提升 70%，影响度 98%
2. **海洋湍流 Syed-Mann 模型** - 修正 20% 载荷偏差
3. **AI 驱动多保真度优化** - 效率提升 10-100 倍
4. **平台运动-载荷调制效应** - 改变设计范式
5. **瞬态工况疲劳累积** - 范式转变

### 博士论文汇报PPT生成系统（18页）

**更新日期**: 2026-03-30

基于深度文献分析（578篇，2018-2026），生成符合博士论文汇报标准的高质量HTML PPT。

#### 最新生成成果

**输出位置**: `data/ppt_helper/processed/ppt_slides/`

**18页完整结构**:

1. **封面** - 大型风力机气动相关问题研究进展
2. **研究背景** - 超大型风机4大核心气动挑战
3. **文献分析概况** - 578篇文献筛选标准与核心发现
4. **领域概览** - 5大气动相关领域（动态失速、浮式风电、高保真方法、气动优化、流动控制）
5. **重点论文分析(1)** - 动态失速（B-L模型修正 vs 三维旋转效应）
6. **重点论文分析(2)** - 浮式风电（纵荡-俯仰耦合 vs 大偏航阻尼反转）
7. **重点论文分析(3)** - AI代理模型（POD/DMD与PINN前沿）
8. **研究空白(1)** - 高紧迫性空白（GA-001至GA-004）
9. **研究空白(2)** - 中紧迫性空白（GA-005至GA-008）
10. **候选方向D-001** - 三维旋转修正的工程动态失速模型
11. **候选方向D-002** - 浮式风电全耦合动态失速分析
12. **候选方向D-003** - 物理信息驱动的AI代理模型
13. **候选方向D-004** - 海洋大气湍流建模
14. **4方向对比分析** - 9维度客观对比（学术创新性、工程价值、可行性等）
15. **技术路线** - 5步研究流程
16. **5年研究计划** - 年度里程碑
17. **预期成果** - 论文、开源工具、标准修订
18. **总结与展望** - 致谢导师

#### 数据来源与质量保证

**文献基础**:
- 总量: 578篇（2018-2026）
- 深度分析: 35篇高质量文献（年份≥2020, Q1期刊优先）
- 筛选标准: 影响分数>60, 严格质量控制

**核心数据亮点**:
- 三维旋转效应: 升力+4-6%、迟滞-61%
- B-L模型修正: 法向力误差15%→5%
- 海洋湍流影响: 22MW风机疲劳+24.42%
- 大偏航角: 30°阻尼符号反转

**设计风格**:
- 严格遵循参考格式（`D:\xfs\phd\汇报\入学前第二次汇报\PPT\图片\*.html`）
- 渐变背景、深蓝色主色调、卡片式布局
- 每页都有具体数据支撑和文献引用
- 客观呈现对比分析，不做方向推荐

#### 使用方式

```bash
# 1. 打开PPT
cd data/ppt_helper/processed/ppt_slides/
# 在浏览器中打开任意HTML文件

# 2. PDF导出
浏览器"打印"功能 → 另存为PDF

# 3. 演示模式
全屏（F11）→ 适合汇报
```

#### 相关文件

- `deep_analysis_recent_papers.md` - 50,000字深度分析报告（35篇核心论文）
- `aerodynamics_related_analysis.json` - 研究空白与候选方向分析
- `ppt_slides/README.md` - PPT详细说明文档

---

### PPT 内容生成（15-20 页）

基于 `part1-4` 综合分析结果，生成符合博士研究进展汇报标准的 HTML 内容：

#### 页面结构

**Part 1: 课题研究综述（4-5 页）**
- Page 1: 研究背景与意义
- Page 2: 八大核心研究领域概览
- Page 3: 技术发展脉络（2018-2026）
- Page 4: 研究热点与高影响力文献
- Page 5: 文献年份分布与统计

**Part 2: 课题创新性（5-6 页）**
- Page 6: 新现象发现（一）- 平台运动-载荷调制
- Page 7: 新现象发现（二）- 海洋湍流偏差
- Page 8: 新现象发现（三）- "块状"布局突破
- Page 9: 新方法与新技术
- Page 10: 新对象与新挑战
- Page 11: 创新性总结

**Part 3: 思路及方法（3-4 页）**
- Page 12: 主流研究方法分类
- Page 13: 方法对比与评估
- Page 14: 技术路线对比
- Page 15: 工具和算法生态

**Part 4: 后续工作完成（3-5 页）**
- Page 16: 当前研究局限性
- Page 17: 短期研究计划（1-3 年）
- Page 18: 中期研究计划（3-5 年）
- Page 19: 长期愿景与跨学科融合（5-10 年）
- Page 20: 总结与展望

#### HTML/CSS 格式规范

**参考风格**: `D:\xfs\phd\汇报\入学前第二次汇报\PPT\图片\page*.html`

**设计特点**:
- 渐变背景: `linear-gradient(135deg, #eef4ff, #f9fbff)`
- 主色调: `#124b93`, `#2f80ed`
- 卡片样式: 圆角 20-22px，阴影 `0 8-10px 20-24px rgba(0,0,0,0.06-0.08)`
- 网格布局: 根据内容自适应调整
- 字体: "Microsoft YaHei", Arial, sans-serif

### 数据位置索引

```bash
# 原始数据
参考文献/气动/
├── pdf/                    # Level 0: 原始 PDF
└── markdown/{paper_id}/    # Level 1: Markdown 全文
    └── full.md

# 分析结果
data/agent_results/categories/{领域}/{paper_id}/  # Level 2: Agent 分析
data/ppt_helper/processed/                         # Level 3-5
├── phase1_overview.json                           # Phase 1 概览
├── by_domain/{领域}/domain_analysis.json          # Phase 2 领域分析
├── aerodynamics_related_analysis.json             # 气动相关问题分析（8空白+4方向）
├── deep_analysis_recent_papers.md                 # 深度分析报告（50,000字）
├── ppt_slides/                                    # 18页博士论文汇报PPT HTML
│   ├── page01_cover.html ~ page18_summary.html   # PPT页面
│   └── README.md                                  # PPT详细说明
├── part1_literature_review.md                     # Part 1 课题综述
├── part2_innovation_points.md                     # Part 2 创新性
├── part3_methodology.md                           # Part 3 方法论
└── part4_future_work.md                           # Part 4 未来工作
```

### 文档说明

详细的数据使用说明请参考：
- [PRD: 博士研究方向调研汇报](data/ppt_helper/PRD_PHD_RESEARCH_PROPOSAL.md) - 开题汇报产品需求文档 ⭐
- [数据层级与信息流转指南](data/ppt_helper/DATA_HIERARCHY_GUIDE.md) - 数据架构详解

**应用场景**: 博一研究生向导师汇报领域调研结果，确定研究方向

---

## 📚 相关文档

### 用户文档
- [GUI使用说明](docs/GUI使用说明.md)
- [多源下载系统使用指南](docs/多源下载系统使用指南.md)
- [分类系统实现说明](docs/CLASSIFICATION_SYSTEM.md)
- [系统完成报告](docs/系统完成报告.md)

### 数据文档
- [PRD: PPT 内容生成系统](data/ppt_helper/PRD_PPT_CONTENT_GENERATION.md)
- [数据层级与信息流转指南](data/ppt_helper/DATA_HIERARCHY_GUIDE.md)

---

## 🤝 参考

本项目的架构设计受到以下项目的启发：

- [Eigent](https://github.com/eigent-ai/eigent) - Multi-Agent Cowork Desktop App
- [CAMEL-AI](https://www.camel-ai.org/) - Communicative Agents for Mind Exploration and Learning

---

## 📄 许可证

Apache License 2.0

---

**最后更新**: 2026-03-30
**当前状态**: ✅ 核心功能已完成，可正常使用
**项目规模**: 102 个 Python 文件，约 15,000+ 行代码

**最新更新** (2026-03-30):
- ✅ 清理旧版HTML文件（page01-20.html）
- ✅ 使用Claude Code Agent完成气动相关问题深度分析
- ✅ 生成18页高质量博士论文汇报PPT HTML
- ✅ 创建50,000字深度分析报告（35篇核心论文）

---

*本文档由 **哈雷酱（傲娇大小姐工程师）** 基于 Eigent Multi-Agent 架构设计编写* ✨
