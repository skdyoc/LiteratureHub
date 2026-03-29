"""
领域分析 Agent（Phase 2 核心）

职责：针对特定领域深度分析，必须读取原始 full.md
输入：原始 full.md + agent_results
输出：领域详细分析（有理有据，引用原文）

⚠️ 关键要求：必须读取原始 full.md 文件，所有结论必须有原文支持！
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..prompts import DOMAIN_ANALYZER_PROMPT


class DomainAnalyzerAgent(BaseAgent):
    """领域分析 Agent - Phase 2 分（核心）"""

    def __init__(self, keys_file: str, model: str = "glm-4.7"):
        super().__init__(keys_file, model)
        self.agent_name = "DomainAnalyzerAgent"

    def _prepare_paper_list(
        self, paper_ids: List[str], full_md_contents: Dict[str, str]
    ) -> str:
        """
        准备文献列表信息

        Args:
            paper_ids: 论文 ID 列表
            full_md_contents: full.md 内容映射

        Returns:
            格式化的文献列表字符串
        """
        formatted = []
        for i, paper_id in enumerate(paper_ids, 1):
            full_md = full_md_contents.get(paper_id, "")

            # 提取标题（从 full.md 第一行）
            title = "Unknown"
            if full_md:
                lines = full_md.split("\n")
                if lines and lines[0].startswith("# "):
                    title = lines[0][2:].strip()

            # 统计字符数
            char_count = len(full_md)

            text = f"""
[{i}] {paper_id}
    - 标题: {title}
    - 内容长度: {char_count} 字符
"""
            formatted.append(text)

        return "\n".join(formatted)

    def _prepare_full_md_contents(
        self, paper_ids: List[str], full_md_contents: Dict[str, str], max_chars: int = 300000
    ) -> str:
        """
        准备 full.md 内容（限制总长度）

        Args:
            paper_ids: 论文 ID 列表
            full_md_contents: full.md 内容映射
            max_chars: 最大字符数（默认 300000，GLM-5 可支持约 400-600K 字符）

        Returns:
            格式化的 full.md 内容字符串
        """
        formatted = []
        total_chars = 0

        for paper_id in paper_ids:
            full_md = full_md_contents.get(paper_id, "")

            # 如果内容太长，截断（单篇限制 100K 字符）
            if len(full_md) > 100000:
                full_md = full_md[:100000] + "\n\n[单篇内容过长，已截断...]"

            text = f"""
=====================================================================
[{paper_id}]
=====================================================================

{full_md}

"""
            # 检查是否超过限制
            if total_chars + len(text) > max_chars:
                self.log_progress(f"⚠️ 内容过长，已截断到 {max_chars} 字符")
                break

            formatted.append(text)
            total_chars += len(text)

        return "\n".join(formatted)

    def _prepare_agent_results_json(
        self, paper_ids: List[str], agent_results_json: Dict[str, Dict[str, Any]], max_chars: int = 150000
    ) -> str:
        """
        准备 agent_results JSON 内容（5 个子智能体的输出）

        Args:
            paper_ids: 论文 ID 列表
            agent_results_json: agent_results JSON 映射
            max_chars: 最大字符数（默认 150000，防止过长）

        Returns:
            格式化的 agent_results 内容
        """
        if not agent_results_json:
            return "\n## 原系统智能体分析结果\n（无）"

        formatted = []
        formatted.append("## 原系统 5 个子智能体的深度分析结果")
        formatted.append("")

        total_chars = len("\n".join(formatted))

        for i, paper_id in enumerate(paper_ids, 1):
            if paper_id not in agent_results_json:
                continue

            paper_results = agent_results_json[paper_id]

            # 提取标题（从 innovation 的第一个 new_phenomenon 或 new_method）
            title = paper_id
            if "innovation" in paper_results:
                innovation = paper_results["innovation"]
                if isinstance(innovation, dict):
                    new_phenomena = innovation.get("new_phenomena", [])
                    new_methods = innovation.get("new_methods", [])
                    if new_phenomena and len(new_phenomena) > 0:
                        title = new_phenomena[0].get("name", paper_id)
                    elif new_methods and len(new_methods) > 0:
                        title = new_methods[0].get("name", paper_id)

            paper_formatted = []
            paper_formatted.append(f"### [{i}] {title}")
            paper_formatted.append("")

            # 1. Motivation（研究动机）
            if "motivation" in paper_results:
                motivation = paper_results["motivation"]
                if isinstance(motivation, dict):
                    problem = motivation.get("问题陈述", motivation.get("problem_statement", ""))
                    if problem:
                        paper_formatted.append("**研究动机**:")
                        if isinstance(problem, str):
                            paper_formatted.append(f"  - 问题: {problem[:200]}...")
                        paper_formatted.append("")

            # 2. Innovation（创新点）- 最重要的！
            if "innovation" in paper_results:
                innovation = paper_results["innovation"]
                if isinstance(innovation, dict):
                    # 新现象
                    new_phenomena = innovation.get("new_phenomena", [])
                    if new_phenomena:
                        paper_formatted.append(f"**新现象**（共 {len(new_phenomena)} 个）:")
                        for j, phen in enumerate(new_phenomena[:2], 1):  # 限制前2个
                            name = phen.get("name", "")
                            detailed = phen.get("detailed_description", "")
                            paper_formatted.append(f"  {j}. {name}")
                            if detailed:
                                paper_formatted.append(f"     {detailed[:150]}...")
                        paper_formatted.append("")

                    # 新方法
                    new_methods = innovation.get("new_methods", [])
                    if new_methods:
                        paper_formatted.append(f"**新方法**（共 {len(new_methods)} 个）:")
                        for j, meth in enumerate(new_methods[:2], 1):  # 限制前2个
                            name = meth.get("name", "")
                            detailed = meth.get("detailed_description", "")
                            paper_formatted.append(f"  {j}. {name}")
                            if detailed:
                                paper_formatted.append(f"     {detailed[:150]}...")
                        paper_formatted.append("")

                    # 新对象
                    new_objects = innovation.get("new_objects", [])
                    if new_objects:
                        paper_formatted.append(f"**新对象**（共 {len(new_objects)} 个）:")
                        for j, obj in enumerate(new_objects[:2], 1):  # 限制前2个
                            name = obj.get("name", "")
                            detailed = obj.get("detailed_description", "")
                            paper_formatted.append(f"  {j}. {name}")
                            if detailed:
                                paper_formatted.append(f"     {detailed[:150]}...")
                        paper_formatted.append("")

            # 3. Mechanism（物理机制）
            if "mechanism" in paper_results:
                mechanism = paper_results["mechanism"]
                if isinstance(mechanism, dict):
                    core_mechanism = mechanism.get("核心机制", mechanism.get("core_mechanism", ""))
                    if core_mechanism:
                        paper_formatted.append("**物理机制**:")
                        if isinstance(core_mechanism, str):
                            paper_formatted.append(f"  {core_mechanism[:200]}...")
                        paper_formatted.append("")

            # 4. Impact（影响力）
            if "impact" in paper_results:
                impact = paper_results["impact"]
                if isinstance(impact, dict):
                    academic = impact.get("学术影响", impact.get("academic_impact", ""))
                    if academic:
                        paper_formatted.append("**学术影响**:")
                        if isinstance(academic, str):
                            paper_formatted.append(f"  {academic[:150]}...")
                        paper_formatted.append("")

            # 5. Roadmap（技术路线）
            if "roadmap" in paper_results:
                roadmap = paper_results["roadmap"]
                if isinstance(roadmap, dict):
                    methodology = roadmap.get("方法论", roadmap.get("methodology", ""))
                    if methodology:
                        paper_formatted.append("**技术路线**:")
                        if isinstance(methodology, str):
                            paper_formatted.append(f"  {methodology[:150]}...")
                        paper_formatted.append("")

            paper_formatted.append("-" * 60)
            paper_formatted.append("")

            # 检查是否超过限制
            paper_text = "\n".join(paper_formatted)
            if total_chars + len(paper_text) > max_chars:
                self.log_progress(f"⚠️ agent_results JSON 过长，已截断到 {max_chars} 字符")
                break

            formatted.extend(paper_formatted)
            total_chars += len(paper_text)

        return "\n".join(formatted)

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行领域深度分析

        ⚠️ 关键：必须读取原始 full.md 和 agent_results JSON，引用原文支持结论！

        Args:
            input_data: 包含以下字段
                - domain_name: 领域名称
                - domain_description: 领域描述
                - paper_ids: 该领域的论文 ID 列表
                - full_md_contents: 原始 full.md 内容 {paper_id: content}
                - agent_results_json: 完整的 agent_results JSON（5 个子智能体输出）
                - phase1_context: Phase 1 的上下文数据（research_hotspots, time_trends, top_papers）

        Returns:
            领域详细分析，包含：
                - development_history: 发展历程
                - research_directions: 研究方向
                - innovations: 创新点分析
                - technical_routes: 技术路线对比
                - key_scientific_questions: 关键科学问题
        """
        domain_name = input_data.get("domain_name", "")
        domain_description = input_data.get("domain_description", "")
        paper_ids = input_data.get("paper_ids", [])
        full_md_contents = input_data.get("full_md_contents", {})
        agent_results_json = input_data.get("agent_results_json", {})  # ⭐ 新增
        phase1_context = input_data.get("phase1_context", {})

        self.log_progress(f"开始 Phase 2 领域分析: {domain_name}")
        self.log_progress(f"  - 文献数量: {len(paper_ids)}")
        self.log_progress(f"  - agent_results JSON: {len(agent_results_json)} 篇")  # ⭐ 新增

        # 准备文献列表
        paper_list = self._prepare_paper_list(paper_ids, full_md_contents)
        self.log_progress(f"  - 文献列表准备完成")

        # 准备 full.md 内容
        full_md_text = self._prepare_full_md_contents(paper_ids, full_md_contents)
        total_chars = len(full_md_text)
        self.log_progress(f"  - 原文内容长度: {total_chars} 字符")

        # ⭐ 准备 agent_results JSON 内容
        agent_results_text = self._prepare_agent_results_json(paper_ids, agent_results_json)
        self.log_progress(f"  - agent_results JSON 长度: {len(agent_results_text)} 字符")

        # ⭐ 准备 Phase 1 上下文数据
        phase1_context_text = self._prepare_phase1_context(phase1_context)
        self.log_progress(f"  - Phase 1 上下文: {len(phase1_context_text)} 字符")

        # ⭐ 检查内容长度
        if total_chars > 200000:
            self.log_progress(f"⚠️ 警告：原文内容过长（{total_chars} 字符），可能导致 API 响应缓慢")
        elif total_chars > 400000:
            self.log_progress(f"❌ 错误：原文内容太长（{total_chars} 字符），建议减少文献数量")
            return self._get_empty_result(domain_name, paper_ids)

        # 构造 Prompt
        prompt = DOMAIN_ANALYZER_PROMPT.format(
            domain_name=domain_name,
            domain_description=domain_description,
            paper_count=len(paper_ids),
            paper_list=paper_list,
            full_md_contents=full_md_text,
            agent_results_json=agent_results_text,  # ⭐ 添加 agent_results JSON
            phase1_context=phase1_context_text,  # ⭐ 添加 Phase 1 上下文
        )

        # 检查 Prompt 长度
        prompt_length = len(prompt)
        self.log_progress(f"  - Prompt 长度: {prompt_length} 字符")

        if prompt_length > 250000:
            self.log_progress(f"⚠️ 警告：Prompt 过长（{prompt_length} 字符）")
        elif prompt_length > 500000:
            self.log_progress(f"❌ 错误：Prompt 太长（{prompt_length} 字符）")
            return self._get_empty_result(domain_name, paper_ids)

        self.log_progress(f"调用 {self.model} API...")

        # 调用 API
        response = self._call_glm_api(prompt)

        if not response:
            self.log_progress("API 调用失败，返回空结果")
            return self._get_empty_result(domain_name, paper_ids)

        # 解析响应
        result = self._parse_json_response(response)

        if not result:
            self.log_progress("JSON 解析失败")
            return self._get_empty_result(domain_name, paper_ids)

        # 验证结果
        required_fields = ["phase", "domain_name", "analysis"]
        if not self.validate_result(result, required_fields):
            self.log_progress("结果验证失败")
            return self._get_empty_result(domain_name, paper_ids)

        self.log_progress("领域分析完成")
        return result

    def _prepare_phase1_context(self, phase1_context: Dict[str, Any]) -> str:
        """
        准备 Phase 1 上下文数据文本

        Args:
            phase1_context: Phase 1 的上下文数据
                - related_hotspots: 相关研究热点
                - time_trends: 时间趋势分析
                - top_papers: 高影响力文献

        Returns:
            格式化的上下文字符串
        """
        if not phase1_context:
            return "\n## Phase 1 上下文信息\n（无）"

        formatted = []
        formatted.append("## Phase 1 概览分析结果")
        formatted.append("")  # 空行

        # ⭐ Research Hotspots（研究热点）
        hotspots = phase1_context.get("related_hotspots", [])
        if hotspots:
            formatted.append("### 相关研究热点")
            formatted.append("")
            for hs in hotspots:
                topic = hs.get("topic", "")
                frequency = hs.get("frequency", 0)
                description = hs.get("description", "")
                trend = hs.get("trend", "")
                papers = hs.get("papers", [])

                formatted.append(f"**{topic}**")
                formatted.append(f"  - 描述: {description}")
                formatted.append(f"  - 频次: {frequency}")
                formatted.append(f"  - 趋势: {trend}")
                formatted.append(f"  - 相关文献数: {len(papers)} 篇")
                formatted.append("")

        # ⭐ Time Trends（时间趋势）
        trends = phase1_context.get("time_trends", {})
        if trends:
            formatted.append("### 时间趋势分析")
            formatted.append("")
            for period, data in trends.items():
                themes = data.get("themes", [])
                description = data.get("description", "")

                formatted.append(f"**{period}**")
                formatted.append(f"  - 主题: {', '.join(themes)}")
                formatted.append(f"  - 描述: {description}")
                formatted.append("")

        # ⭐ Top Papers（高影响力文献）
        top_papers = phase1_context.get("top_papers", [])
        if top_papers:
            formatted.append("### 高影响力文献")
            formatted.append("")
            for paper in top_papers[:10]:  # 限制前10篇
                paper_id = paper.get("paper_id", "")
                title = paper.get("title", "")
                year = paper.get("year", 0)
                score = paper.get("score", 0.0)
                reason = paper.get("reason", "")

                # 标题可能很长，截断到80字符
                title_short = title[:80] + "..." if len(title) > 80 else title

                formatted.append(f"- **[{year}]** {title_short}")
                formatted.append(f"  - 评分: {score:.2f}")
                formatted.append(f"  - 入选理由: {reason}")
                formatted.append("")

        return "\n".join(formatted)

    def _get_empty_result(
        self, domain_name: str, paper_ids: List[str]
    ) -> Dict[str, Any]:
        """返回空结果（失败时使用）"""
        return {
            "phase": "domain_analysis",
            "domain_name": domain_name,
            "analysis": {
                "development_history": {
                    "early_2018_2020": {"summary": "分析失败", "key_papers": []},
                    "middle_2021_2022": {"summary": "分析失败", "key_papers": []},
                    "recent_2023_2026": {"summary": "分析失败", "key_papers": []},
                },
                "research_directions": [],
                "innovations": {
                    "new_phenomena": [],
                    "new_methods": [],
                    "new_objects": [],
                },
                "technical_routes": [],
                "key_scientific_questions": [],
            },
            "summary": "分析失败",
        }


# ============================================================================
# Prompt 模板（关键！强调引用原文）
# ============================================================================

DOMAIN_ANALYZER_PROMPT_TEMPLATE = """
你是一个风能气动领域的专家，需要针对特定领域进行深度分析。

## ⚠️ 核心要求

**所有结论必须引用原文（full.md）支持，禁止编造！**

每个分析结论必须包含：
1. 结论本身
2. 原文引用（精确到段落或章节）
3. 引用位置（例如："Introduction 第 3 段"）

## 输入数据

**领域名称**: {domain_name}

**原始文献**（full.md 完整内容）:
{full_md_contents}

**初步分析结果**（agent_results）:
{agent_results}

## 任务

### 1. 领域概览
总结该领域的研究目标、主要问题、解决思路

### 2. 关键创新点（必须引用原文）
从文献中提取：
- 新现象（New Phenomena）
- 新方法（New Methods）
- 新对象（New Objects）

每个创新点格式：
```json
{{
  "type": "new_method",
  "description": "方法描述",
  "evidence": "原文引用（精确文本）",
  "location": "Abstract 第 2 段",
  "paper_id": "2026_Paper_ID"
}}
```

### 3. 方法总结（必须引用原文）
总结主要研究方法、技术路线、工具

### 4. 技术挑战（必须引用原文）
总结当前技术瓶颈、未解决的问题

### 5. 代表性文献
选择 2-3 篇最代表性的文献进行详细分析

## 输出格式（JSON）

```json
{{
  "domain_overview": "领域概览（200-300字）",
  "key_innovations": [
    {{
      "type": "new_method|new_phenomenon|new_object",
      "description": "创新点描述",
      "evidence": "原文引用（精确文本）",
      "location": "章节位置",
      "paper_id": "论文ID",
      "year": 年份
    }}
  ],
  "methodology_summary": "方法总结（300-400字）",
  "technical_challenges": [
    {{
      "challenge": "挑战描述",
      "evidence": "原文引用",
      "location": "章节位置",
      "paper_id": "论文ID"
    }}
  ],
  "representative_papers": [
    {{
      "paper_id": "论文ID",
      "title": "标题",
      "reason": "代表性理由",
      "key_contribution": "关键贡献"
    }}
  ],
  "evidence_chain": {{
    "结论1": {{
      "evidence": "原文引用",
      "location": "位置",
      "paper_id": "论文ID"
    }}
  }}
}}
```

## ⚠️ 禁止事项

1. **禁止编造**：所有结论必须有原文支持
2. **禁止断章取义**：引用要完整、准确
3. **禁止过度推断**：基于原文合理推断，不要夸大
4. **禁止抄袭**：引用要注明出处和位置

## 示例

**好的引用**：
```json
{{
  "description": "提出了一种基于遗传算法的叶片优化方法",
  "evidence": "我们提出了一种改进的遗传算法（IGA），结合了自适应交叉变异策略...",
  "location": "Abstract 第 2 段",
  "paper_id": "2026_Author_1"
}}
```

**不好的引用**：
```json
{{
  "description": "提出了一种优化方法",
  "evidence": "论文中提到了优化",  # ❌ 太模糊
  "location": "不知道",
  "paper_id": "2026_Author_1"
}}
```
"""


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 使用示例
    agent = DomainAnalyzerAgent(keys_file="config/api_keys.txt", model="glm-5")

    # 模拟输入数据
    input_data = {
        "domain_name": "Aerodynamic Optimization",
        "paper_ids": ["2026_Paper_1", "2026_Paper_2"],
        "full_md_contents": {
            "2026_Paper_1": "# Paper Title\n\nFull content...",
            "2026_Paper_2": "# Another Paper\n\nFull content...",
        },
        "agent_results": {
            "2026_Paper_1": {"innovation": {...}},
            "2026_Paper_2": {"innovation": {...}},
        },
    }

    # 执行分析
    result = agent.analyze(input_data)

    print(f"领域分析结果: {result['domain_overview']}")
    print(f"关键创新点: {len(result['key_innovations'])}")
