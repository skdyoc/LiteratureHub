"""
综合总结 Agent（Phase 3: 总）

职责：将多个领域的分析结果综合成完整的博士论文汇报 PPT
输入：Phase 1 概览 + Phase 2 领域分析 + 重点论文 agent_results
输出：4 部分 PPT 内容（Literature Review, Innovation Points, Methodology, Future Work）

⚠️ 关键要求：必须充分利用 Phase 1 的 research_hotspots, time_trends, top_papers
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from .base_agent import BaseAgent
from ..prompts import SUMMARY_PROMPT


class SummaryAgent(BaseAgent):
    """综合总结 Agent - Phase 3 总"""

    def __init__(self, keys_file: str, model: str = "glm-5"):
        super().__init__(keys_file, model)
        self.agent_name = "SummaryAgent"

    def _load_phase1_overview(self, phase1_path: str) -> Dict[str, Any]:
        """
        加载 Phase 1 概览结果

        Args:
            phase1_path: Phase 1 结果文件路径

        Returns:
            Phase 1 概览数据
        """
        try:
            with open(phase1_path, 'r', encoding='utf-8') as f:
                phase1_data = json.load(f)

            self.log_progress(f"✅ Phase 1 概览加载成功")
            self.log_progress(f"   - 识别领域: {len(phase1_data.get('domains', []))}")
            self.log_progress(f"   - 研究热点: {len(phase1_data.get('research_hotspots', []))}")
            self.log_progress(f"   - Top 文献: {len(phase1_data.get('top_papers', []))}")

            return phase1_data

        except Exception as e:
            self.log_progress(f"❌ Phase 1 概览加载失败: {e}")
            return {}

    def _load_domain_analyses(self, domain_results_dir: str) -> List[Dict[str, Any]]:
        """
        加载所有领域的分析结果

        Args:
            domain_results_dir: 领域分析结果目录

        Returns:
            领域分析列表
        """
        domain_analyses = []
        domain_dir = Path(domain_results_dir)

        if not domain_dir.exists():
            self.log_progress(f"❌ 领域分析目录不存在: {domain_results_dir}")
            return domain_analyses

        # 遍历所有领域目录
        for domain_subdir in domain_dir.iterdir():
            if not domain_subdir.is_dir():
                continue

            analysis_file = domain_subdir / "domain_analysis.json"

            if not analysis_file.exists():
                continue

            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    domain_data = json.load(f)

                domain_analyses.append(domain_data)
                self.log_progress(f"✅ 加载领域: {domain_data.get('domain_name', 'Unknown')}")

            except Exception as e:
                self.log_progress(f"⚠️ 领域分析加载失败 {analysis_file}: {e}")
                continue

        self.log_progress(f"✅ 共加载 {len(domain_analyses)} 个领域的分析")
        return domain_analyses

    def _load_key_papers_agent_results(
        self,
        agent_results_path: str,
        paper_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        加载重点论文的 agent_results

        Args:
            agent_results_path: agent_results 目录
            paper_ids: 重点论文明细

        Returns:
            论文 agent_results 字典 {paper_id: {analyzer: result}}
        """
        agent_results = {}
        agent_dir = Path(agent_results_path)

        if not agent_dir.exists():
            self.log_progress(f"⚠️ agent_results 目录不存在: {agent_results_path}")
            return agent_results

        self.log_progress(f"开始加载 {len(paper_ids)} 篇重点论文的 agent_results...")

        for paper_id in paper_ids:
            paper_dir = agent_dir / paper_id

            if not paper_dir.exists():
                self.log_progress(f"⚠️ 论文目录不存在: {paper_id}")
                continue

            # 读取 5 个子智能体的分析结果
            paper_results = {}

            for analyzer_name in ["innovation", "motivation", "mechanism", "impact", "roadmap"]:
                analyzer_file = paper_dir / f"{analyzer_name}.json"

                if not analyzer_file.exists():
                    continue

                try:
                    with open(analyzer_file, 'r', encoding='utf-8') as f:
                        analyzer_result = json.load(f)

                    paper_results[analyzer_name] = analyzer_result

                except Exception as e:
                    self.log_progress(f"⚠️ 读取失败 {analyzer_file}: {e}")
                    continue

            if paper_results:
                agent_results[paper_id] = paper_results
                self.log_progress(f"✅ {paper_id}: {len(paper_results)} 个分析器")

        self.log_progress(f"✅ 共加载 {len(agent_results)} 篇论文的 agent_results")
        return agent_results

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行综合总结分析（Phase 3）

        ⚠️ 关键：必须充分利用 Phase 1/2 的输出和智能加载的 agent_results

        Args:
            input_data: 包含以下字段
                - phase1_path: Phase 1 结果文件路径（或 phase1_overview 直接传数据）
                - domain_results_dir: Phase 2 领域分析结果目录（或 domain_analyses 直接传数据）
                - agent_results_path: agent_results 目录（用于加载重点论文）
                - max_key_papers: 最大重点论文数量（可选，默认20）

        Returns:
            4 部分 PPT 内容框架：
                - part1_literature_review: 文献综述
                - part2_innovation_points: 创新点分析
                - part3_methodology: 方法论
                - part4_future_work: 未来工作
        """
        self.log_progress("开始 Phase 3 综合总结...")

        # 支持两种输入方式：文件路径或已加载的数据
        # 方式1：从文件路径加载（推荐）
        if "phase1_path" in input_data:
            phase1_data = self._load_phase1_overview(input_data["phase1_path"])
            if not phase1_data:
                self.log_progress("❌ Phase 1 数据加载失败")
                return self._get_empty_result()
        else:
            # 方式2：直接使用传入的数据
            phase1_data = input_data.get("phase1_overview", {})
            if not phase1_data:
                self.log_progress("❌ 缺少 Phase 1 数据")
                return self._get_empty_result()

        # 加载 Phase 2 领域分析
        if "domain_results_dir" in input_data:
            domain_analyses_list = self._load_domain_analyses(input_data["domain_results_dir"])
            if not domain_analyses_list:
                self.log_progress("❌ Phase 2 领域分析加载失败")
                return self._get_empty_result()
            # 转换为字典格式（兼容旧代码）
            domain_analyses = {
                d.get("domain_name", "Unknown"): d
                for d in domain_analyses_list
            }
        else:
            domain_analyses = input_data.get("domain_analyses", {})
            if not domain_analyses:
                self.log_progress("❌ 缺少 Phase 2 领域分析数据")
                return self._get_empty_result()

        # 提取重点论文 ID 并加载 agent_results
        agent_results_json = input_data.get("agent_results_json", {})
        max_key_papers = input_data.get("max_key_papers", 20)

        if not agent_results_json and "agent_results_path" in input_data:
            # 从 Phase 1 Top 文献中提取重点论文 ID
            top_papers = phase1_data.get("top_papers", [])
            key_paper_ids = [p.get("paper_id") for p in top_papers[:max_key_papers] if p.get("paper_id")]

            # 加载 agent_results
            if key_paper_ids:
                agent_results_json = self._load_key_papers_agent_results(
                    input_data["agent_results_path"],
                    key_paper_ids
                )

        self.log_progress(f"  - 领域数量: {len(domain_analyses)}")
        self.log_progress(f"  - agent_results JSON: {len(agent_results_json)} 篇")

        # 准备领域分析文本
        domain_analyses_text = self._prepare_domain_analyses(domain_analyses)
        self.log_progress(f"  - 领域分析内容: {len(domain_analyses_text)} 字符")

        # 准备 Phase 1 概览文本
        phase1_overview_text = self._prepare_phase1_overview(phase1_data)
        self.log_progress(f"  - Phase 1 概览: {len(phase1_overview_text)} 字符")

        # 准备 agent_results 文本（智能加载的重点内容）
        agent_results_text = self._prepare_agent_results_text(agent_results_json)
        self.log_progress(f"  - agent_results 内容: {len(agent_results_text)} 字符")

        # 构造 Prompt
        prompt = SUMMARY_PROMPT.format(
            domain_analyses=domain_analyses_text,
            phase1_overview=phase1_overview_text,
            agent_results=agent_results_text
        )

        # 检查 Prompt 长度
        prompt_length = len(prompt)
        self.log_progress(f"  - Prompt 长度: {prompt_length} 字符")

        estimated_tokens = int(prompt_length / 2)
        self.log_progress(f"  - 预估 token 数: ~{estimated_tokens}")

        if estimated_tokens > 150000:
            self.log_progress(f"⚠️ 警告：Prompt 预估 {estimated_tokens} tokens")
            self.log_progress(f"💡 建议：减少重点论文数量")

        self.log_progress(f"调用 {self.model} API...")

        # 调用 API（超时设置为 18000 秒 = 5 小时）
        response = self._call_glm_api(prompt, timeout=18000)

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

        self.log_progress("✅ Phase 3 综合总结完成")
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
                    # ⭐ 检查 data 是否为 None
                    if data is None:
                        continue
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
                "part1_research_review": {
                    "title": "01 课题研究综述（包含国内外研究现状）",
                    "slides": []
                },
                "part2_innovation": {
                    "title": "02 课题创新性",
                    "slides": []
                },
                "part3_methodology": {
                    "title": "03 思路及方法",
                    "slides": []
                },
                "part4_future_work": {
                    "title": "04 后续工作完成",
                    "slides": []
                }
            },
            "summary": "综合总结失败"
        }


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import sys
    import io

    # Windows UTF-8 支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    # 使用示例
    try:
        agent = SummaryAgent(keys_file="config/api_keys.txt", model="glm-5")

        # 方式1：从文件路径加载（推荐）
        input_data = {
            "phase1_path": "data/ppt_helper/processed/phase1_overview.json",
            "domain_results_dir": "data/ppt_helper/processed/by_domain",
            "agent_results_path": "data/agent_results",
            "max_key_papers": 20,
        }

        # 方式2：直接传入数据（用于测试）
        # input_data = {
        #     "phase1_overview": {...},
        #     "domain_analyses": {...},
        #     "agent_results_json": {...},
        # }

        # 执行分析
        result = agent.analyze(input_data)

        print(f"\n📊 Phase 3 分析结果:")
        ppt_content = result.get("ppt_content", {})

        # 按照博士论文汇报框架显示
        part_mapping = {
            "part1_research_review": "01 课题研究综述",
            "part2_innovation": "02 课题创新性",
            "part3_methodology": "03 思路及方法",
            "part4_future_work": "04 后续工作完成"
        }

        for part_key, part_name in part_mapping.items():
            if part_key in ppt_content:
                slides = ppt_content[part_key].get("slides", [])
                print(f"  {part_name}: {len(slides)} 页")

        # 保存结果
        output_path = "data/ppt_helper/processed/final_ppt_content.json"
        agent.save_result(result, output_path)
        print(f"\n✅ 结果已保存到: {output_path}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()

