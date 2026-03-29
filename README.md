# LiteratureHub - 统一学术文献研究与汇报系统

**版本**: v1.0.0-alpha
**状态**: ✅ 核心功能已完成，可正常使用
**创建日期**: 2026-03-27
**最后更新**: 2026-03-29
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

## 📚 相关文档

- [GUI使用说明](docs/GUI使用说明.md)
- [多源下载系统使用指南](docs/多源下载系统使用指南.md)
- [分类系统实现说明](docs/CLASSIFICATION_SYSTEM.md)
- [系统完成报告](docs/系统完成报告.md)

---

## 🤝 参考

本项目的架构设计受到以下项目的启发：

- [Eigent](https://github.com/eigent-ai/eigent) - Multi-Agent Cowork Desktop App
- [CAMEL-AI](https://www.camel-ai.org/) - Communicative Agents for Mind Exploration and Learning

---

## 📄 许可证

Apache License 2.0

---

**最后更新**: 2026-03-29
**当前状态**: ✅ 核心功能已完成，可正常使用
**项目规模**: 102 个 Python 文件，约 15,000+ 行代码

---

*本文档由 **哈雷酱（傲娇大小姐工程师）** 基于 Eigent Multi-Agent 架构设计编写* ✨
