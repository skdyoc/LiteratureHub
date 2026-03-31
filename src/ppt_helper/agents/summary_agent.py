"""
综合总结 Agent（Phase 3）

职责：跨领域综合，生成 4 部分 PPT 内容框架
输入：Phase 2 的所有领域分析结果 + Phase 1 概览
输出：4 部分 PPT 内容（Literature Review, Innovation, Methodology, Future Work）

⚠️ 关键要求：必须充分利用 Phase 1 的 research_hotspots, time_trends, top_papers
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..prompts import SUMMARY_PROMPT


class SummaryAgent(BaseAgent):
    """综合总结 Agent - Phase 3 总"""

    def __init__(self, keys_file: str, model: str = "glm-4.7"):
        super().__init__(keys_file, model)
        self.agent_name = "SummaryAgent"

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行综合总结

        ⚠️ 关键：必须充分利用 Phase 1/2 的输出和智能加载的 agent_results

        Args:
            input_data: 包含以下字段
                - domain_analyses: Phase 2 的所有领域分析 {domain_name: analysis_result}
                - phase1_overview: Phase 1 的概览分析（包含 research_hotspots, time_trends, top_papers）
                - agent_results_json: 智能加载的 agent_results（根据 Phase 1/2 判断重点）

        Returns:
            4 部分 PPT 内容框架：
                - part1_literature_review: 文献综述
                - part2_innovation_points: 创新点分析
                - part3_methodology: 方法论
                - part4_future_work: 未来工作
        """
        domain_analyses = input_data.get("domain_analyses", {})
        phase1_overview = input_data.get("phase1_overview", {})
        agent_results_json = input_data.get("agent_results_json", {})  # ⭐ 新增

        self.log_progress("开始 Phase 3 综合总结...")
        self.log_progress(f"  - 领域数量: {len(domain_analyses)}")
        self.log_progress(f"  - agent_results JSON: {len(agent_results_json)} 篇")  # ⭐ 新增

        # 准备领域分析文本
        domain_analyses_text = self._prepare_domain_analyses(domain_analyses)
        self.log_progress(f"  - 领域分析内容: {len(domain_analyses_text)} 字符")

        # 准备 Phase 1 概览文本
        phase1_overview_text = self._prepare_phase1_overview(phase1_overview)
        self.log_progress(f"  - Phase 1 概览: {len(phase1_overview_text)} 字符")

        # ⭐ 准备 agent_results 文本（智能加载的重点内容）
        agent_results_text = self._prepare_agent_results_text(agent_results_json)
        self.log_progress(f"  - agent_results 内容: {len(agent_results_text)} 字符")

        # 构造 Prompt
        prompt = SUMMARY_PROMPT.format(
            domain_analyses=domain_analyses_text,
            phase1_overview=phase1_overview_text,
            agent_results=agent_results_text  # ⭐ 添加 agent_results
        )

        # 检查 Prompt 长度
        prompt_length = len(prompt)
        self.log_progress(f"  - Prompt 长度: {prompt_length} 字符")

        if prompt_length > 400000:
            self.log_progress(f"⚠️ 警告：Prompt 过长（{prompt_length} 字符），可能需要截断")
        elif prompt_length > 800000:
            self.log_progress(f"❌ 错误：Prompt 太长（{prompt_length} 字符）")
            return self._get_empty_result()

        self.log_progress(f"调用 {self.model} API...")

        # 调用 API
        response = self._call_glm_api(prompt)

        if not response:
            self.log_progress("API 调用失败，返回空结果")
            return self._get_empty_result()

        # 解析响应
        result = self._parse_json_response(response)

        if not result:
            self.log_progress("JSON 解析失败")
            return self._get_empty_result()

        # 验证结果
        required_fields = ["phase", "ppt_content"]
        if not self.validate_result(result, required_fields):
            self.log_progress("结果验证失败")
            return self._get_empty_result()

        self.log_progress("综合总结完成")
        return result

    def _prepare_domain_analyses(self, domain_analyses: Dict[str, Any]) -> str:
        """
        准备领域分析文本

        Args:
            domain_analyses: 领域分析结果映射 {domain_name: analysis_result}

        Returns:
            格式化的领域分析文本
        """
        if not domain_analyses:
            return "## 领域分析结果\n（无）"

        formatted = []
        formatted.append("## Phase 2 领域分析结果")
        formatted.append("")

        for domain_name, result in domain_analyses.items():
            formatted.append(f"### {domain_name}")
            formatted.append("")

            # 提取关键信息
            analysis = result.get("analysis", {})

            # 发展历程
            dev_history = analysis.get("development_history", {})
            if dev_history:
                formatted.append("**发展历程**:")
                for period, data in dev_history.items():
                    summary = data.get("summary", "")
                    if summary:
                        formatted.append(f"- {period}: {summary[:100]}...")
                formatted.append("")

            # 研究方向
            directions = analysis.get("research_directions", [])
            if directions:
                formatted.append(f"**研究方向**（共 {len(directions)} 个）:")
                for direction in directions[:5]:  # 限制前5个
                    name = direction.get("name", "")
                    description = direction.get("description", "")
                    formatted.append(f"- {name}: {description[:80]}...")
                formatted.append("")

            # 创新点
            innovations = analysis.get("innovations", {})
            if innovations:
                new_methods = innovations.get("new_methods", [])
                new_phenomena = innovations.get("new_phenomena", [])
                new_objects = innovations.get("new_objects", [])

                formatted.append("**核心创新点**:")
                formatted.append(f"  - 新方法: {len(new_methods)} 个")
                formatted.append(f"  - 新现象: {len(new_phenomena)} 个")
                formatted.append(f"  - 新对象: {len(new_objects)} 个")
                formatted.append("")

            # 技术路线
            tech_routes = analysis.get("technical_routes", [])
            if tech_routes:
                formatted.append(f"**技术路线**（共 {len(tech_routes)} 条）:")
                for route in tech_routes[:3]:  # 限制前3条
                    name = route.get("name", "")
                    formatted.append(f"- {name}")
                formatted.append("")

            formatted.append("-" * 60)
            formatted.append("")

        return "\n".join(formatted)

    def _prepare_phase1_overview(self, phase1_overview: Dict[str, Any]) -> str:
        """
        准备 Phase 1 概览文本

        Args:
            phase1_overview: Phase 1 概览结果

        Returns:
            格式化的 Phase 1 概览文本
        """
        if not phase1_overview:
            return "## Phase 1 概览\n（无）"

        formatted = []
        formatted.append("## Phase 1 整体概览")
        formatted.append("")

        # 领域分类
        domains = phase1_overview.get("domains", [])
        if domains:
            formatted.append(f"### 领域分类（共 {len(domains)} 个）")
            for domain in domains:
                name = domain.get("name", "")
                description = domain.get("description", "")
                paper_count = domain.get("paper_count", 0)
                formatted.append(f"- **{name}**（{paper_count} 篇）: {description[:80]}...")
            formatted.append("")

        # 研究热点
        hotspots = phase1_overview.get("research_hotspots", [])
        if hotspots:
            formatted.append(f"### 研究热点（共 {len(hotspots)} 个）")
            for hotspot in hotspots[:10]:  # 限制前10个
                topic = hotspot.get("topic", "")
                frequency = hotspot.get("frequency", 0)
                description = hotspot.get("description", "")
                trend = hotspot.get("trend", "")
                formatted.append(f"- **{topic}**（频次: {frequency}, 趋势: {trend}）")
                formatted.append(f"  {description[:100]}...")
            formatted.append("")

        # 时间趋势
        time_trends = phase1_overview.get("time_trends", {})
        if time_trends:
            formatted.append("### 时间趋势分析")
            for period, data in time_trends.items():
                themes = data.get("themes", [])
                description = data.get("description", "")
                formatted.append(f"- **{period}**")
                formatted.append(f"  - 主题: {', '.join(themes)}")
                formatted.append(f"  - 描述: {description[:100]}...")
            formatted.append("")

        # Top 论文
        top_papers = phase1_overview.get("top_papers", [])
        if top_papers:
            formatted.append(f"### 高影响力文献（Top {len(top_papers)}）")
            for paper in top_papers[:20]:  # 限制前20篇
                paper_id = paper.get("paper_id", "")
                title = paper.get("title", "")
                year = paper.get("year", 0)
                score = paper.get("score", 0.0)
                reason = paper.get("reason", "")

                # 标题可能很长，截断到60字符
                title_short = title[:60] + "..." if len(title) > 60 else title

                formatted.append(f"- **[{year}]** {title_short}")
                formatted.append(f"  - 评分: {score:.2f}")
                formatted.append(f"  - 入选理由: {reason[:80]}...")
            formatted.append("")

        return "\n".join(formatted)

    def _prepare_agent_results_text(self, agent_results_json: Dict[str, Dict[str, Any]]) -> str:
        """
        准备 agent_results 文本（智能加载的重点内容）

        Args:
            agent_results_json: agent_results JSON 映射

        Returns:
            格式化的 agent_results 文本
        """
        if not agent_results_json:
            return "## 智能加载的重点论文分析\n（无）"

        formatted = []
        formatted.append("## 智能加载的重点论文分析（基于 Phase 1/2 判断）")
        formatted.append("")

        for paper_id, paper_results in agent_results_json.items():
            # 提取标题
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

            formatted.append(f"### {title}")
            formatted.append("")

            # 只显示最关键的部分：innovation 和 mechanism
            if "innovation" in paper_results:
                innovation = paper_results["innovation"]
                if isinstance(innovation, dict):
                    # 新现象
                    new_phenomena = innovation.get("new_phenomena", [])
                    if new_phenomena:
                        formatted.append(f"**新现象**（{len(new_phenomena)} 个）:")
                        for phen in new_phenomena[:3]:  # 前3个
                            name = phen.get("name", "")
                            detailed = phen.get("detailed_description", "")
                            formatted.append(f"  - {name}")
                            if detailed:
                                formatted.append(f"    {detailed[:200]}...")
                        formatted.append("")

                    # 新方法
                    new_methods = innovation.get("new_methods", [])
                    if new_methods:
                        formatted.append(f"**新方法**（{len(new_methods)} 个）:")
                        for meth in new_methods[:3]:  # 前3个
                            name = meth.get("name", "")
                            detailed = meth.get("detailed_description", "")
                            formatted.append(f"  - {name}")
                            if detailed:
                                formatted.append(f"    {detailed[:200]}...")
                        formatted.append("")

            # 物理机制（关键）
            if "mechanism" in paper_results:
                mechanism = paper_results["mechanism"]
                if isinstance(mechanism, dict):
                    core = mechanism.get("核心机制", "")
                    if core:
                        formatted.append("**物理机制**:")
                        formatted.append(f"  {core[:300]}...")
                        formatted.append("")

            formatted.append("")

        return "\n".join(formatted)

    def _get_empty_result(self) -> Dict[str, Any]:
        """返回空结果（失败时使用）"""
        return {
            "phase": "summary",
            "ppt_content": {
                "part1_literature_review": {
                    "title": "Literature Review",
                    "slides": [],
                    "summary": "生成失败"
                },
                "part2_innovation_points": {
                    "title": "Innovation Points",
                    "slides": [],
                    "summary": "生成失败"
                },
                "part3_methodology": {
                    "title": "Methodology",
                    "slides": [],
                    "summary": "生成失败"
                },
                "part4_future_work": {
                    "title": "Future Work",
                    "slides": [],
                    "summary": "生成失败"
                }
            },
            "summary": "综合总结失败"
        }

    def generate_literature_review(
        self, domain_analyses: List[Dict], overview: Dict
    ) -> Dict[str, Any]:
        """
        生成 Part 1: Literature Review

        Args:
            domain_analyses: 领域分析结果列表
            overview: Phase 1 概览

        Returns:
            文献综述内容
        """
        # TODO: AI 调用
        return {"title": "Literature Review", "slides": []}

    def generate_innovation_points(self, domain_analyses: List[Dict]) -> Dict[str, Any]:
        """
        生成 Part 2: Innovation Points

        Args:
            domain_analyses: 领域分析结果列表

        Returns:
            创新点分析内容
        """
        # TODO: AI 调用
        return {"title": "Innovation Points", "slides": []}

    def generate_methodology(self, domain_analyses: List[Dict]) -> Dict[str, Any]:
        """
        生成 Part 3: Methodology

        Args:
            domain_analyses: 领域分析结果列表

        Returns:
            方法论内容
        """
        # TODO: AI 调用
        return {"title": "Methodology", "slides": []}

    def generate_future_work(
        self, domain_analyses: List[Dict], overview: Dict
    ) -> Dict[str, Any]:
        """
        生成 Part 4: Future Work

        Args:
            domain_analyses: 领域分析结果列表
            overview: Phase 1 概览

        Returns:
            未来工作内容
        """
        # TODO: AI 调用
        return {"title": "Future Work", "slides": []}


# ============================================================================
# Prompt 模板
# ============================================================================

SUMMARY_PROMPT_TEMPLATE = """
你是一个学术写作专家，需要将多个领域的分析结果综合成一份完整的博士论文汇报 PPT。

## 输入数据

**Phase 1 概览**:
{overview}

**Phase 2 领域分析**:
{domain_analyses}

## 任务

生成 4 部分 PPT 内容框架，每部分包含多个 PPT 页面。

### Part 1: Literature Review（文献综述）

**目标**：建立领域研究的整体认知

**内容要求**：
- 领域整体发展脉络（2018-2026）
- 主要研究方向和子领域
- 研究热点的演变趋势
- 高影响力文献和作者

### Part 2: Innovation Points（创新点分析）

**目标**：提炼领域核心创新贡献

**内容要求**：
- 新现象（New Phenomena）
- 新方法（New Methods）
- 新对象（New Objects）
- 每个创新点要有原文引用

### Part 3: Methodology（方法论与技术路线）

**目标**：总结领域研究方法和工具

**内容要求**：
- 主流研究方法分类
- 关键技术路线对比
- 工具和算法的发展
- 方法的优缺点评估

### Part 4: Future Work（未来研究方向）

**目标**：指明领域发展方向和研究空白

**内容要求**：
- 当前研究的局限性
- 未来发展的关键问题
- 有潜力的研究方向
- 跨学科融合机会

## 输出格式（JSON）

```json
{{
  "part1_literature_review": {{
    "title": "Literature Review",
    "slides": [
      {{
        "slide_number": 1,
        "title": "页面标题",
        "content": ["要点1", "要点2", "要点3"],
        "notes": "演讲者备注"
      }}
    ],
    "summary": "部分总结"
  }},
  "part2_innovation_points": {{...}},
  "part3_methodology": {{...}},
  "part4_future_work": {{...}},
  "overall_summary": "整体总结（用于开场或结尾）"
}}
```

## PPT 设计原则

1. **每页 3-5 个要点**：不要堆砌内容
2. **图文并茂**：为图表、流程图预留空间
3. **逻辑清晰**：每页之间有清晰的逻辑递进
4. **突出重点**：用加粗、颜色等方式突出关键信息
5. **引用准确**：每个关键结论都要有文献引用

## 示例 PPT 页面

```json
{{
  "slide_number": 1,
  "title": "研究背景与意义",
  "content": [
    "风能是全球重要的可再生能源",
    "风力发电效率提升 15% 可带来显著经济效益",
    "气动优化是提升风机效率的关键技术"
  ],
  "notes": "开场白要简明扼要，快速切入主题",
  "visual_suggestions": "建议添加风能发电趋势图"
}}
```
"""


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 使用示例
    agent = SummaryAgent(keys_file="config/api_keys.txt", model="glm-4.7")

    # 模拟输入数据
    input_data = {
        "domain_analyses": [
            {"domain_name": "Aerodynamic Optimization", "data": "..."},
            {"domain_name": "CFD Simulation", "data": "..."},
        ],
        "overview": {"domains": [], "data": "..."},
    }

    # 执行分析
    result = agent.analyze(input_data)

    print(f"PPT 内容框架:")
    print(f"  Part 1: {len(result['part1_literature_review']['slides'])} 页")
    print(f"  Part 2: {len(result['part2_innovation_points']['slides'])} 页")
    print(f"  Part 3: {len(result['part3_methodology']['slides'])} 页")
    print(f"  Part 4: {len(result['part4_future_work']['slides'])} 页")
