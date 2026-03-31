"""
概览 Agent（Phase 1: 总）

职责：基于 agent_results 生成领域整体概览
输入：agent_results 汇总数据
输出：领域分类、研究热点、时间趋势
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from .base_agent import BaseAgent
from ..prompts import OVERVIEW_PROMPT


class OverviewAgent(BaseAgent):
    """概览 Agent - Phase 1 总"""

    def __init__(self, keys_file: str, model: str = "glm-4.7"):
        super().__init__(keys_file, model)
        self.agent_name = "OverviewAgent"

    def _prepare_summaries(
        self, agent_results_summaries: List[Dict[str, Any]], max_papers: int = 100
    ) -> str:
        """
        准备文献摘要信息（⭐ 读取完整的 agent_results）

        Args:
            agent_results_summaries: 文献摘要列表
                格式: [
                    {
                        "metadata": PaperMetadata 对象,
                        "innovation_summary": innovation.json 完整内容,
                        "paper_id": "完整ID"
                    },
                    ...
                ]
            max_papers: 最大文献数量

        Returns:
            格式化的摘要字符串
        """
        # ⭐ 安全字符串处理函数（处理特殊字符）
        def safe_str(s: str) -> str:
            """安全转换字符串，避免 GBK 编码错误"""
            try:
                # 尝试编码为 GBK，如果失败则替换不可编码字符
                return s.encode('gbk', errors='replace').decode('gbk')
            except:
                # 如果还是失败，返回简化版本
                return s.encode('ascii', errors='replace').decode('ascii')

        # 限制文献数量
        summaries = agent_results_summaries[:max_papers]

        formatted = []
        for i, summary in enumerate(summaries, 1):
            metadata = summary.get("metadata")
            innovation = summary.get("innovation_summary") or {}

            # metadata 是 PaperMetadata 对象，直接访问属性
            if not metadata:
                continue

            paper_id = metadata.paper_id if metadata.paper_id else "Unknown"
            title = metadata.title if metadata.title else "Unknown"
            year = metadata.year if metadata.year else 0
            authors = metadata.authors if metadata.authors else []
            journal = metadata.journal if metadata.journal else ""
            score = metadata.score if metadata.score else 0.0

            # ⭐ 安全处理所有可能包含特殊字符的字段
            title = safe_str(title)
            journal = safe_str(journal)
            author_str = safe_str(", ".join(authors[:3]))
            if len(authors) > 3:
                author_str += " et al."

            # ⭐ 提取完整的 innovation 内容（新现象、新方法、新对象）
            new_phenomena = innovation.get("new_phenomena", [])
            new_methods = innovation.get("new_methods", [])
            new_objects = innovation.get("new_objects", [])

            # ⭐ 统计数量
            np_count = len(new_phenomena) if isinstance(new_phenomena, list) else 0
            nm_count = len(new_methods) if isinstance(new_methods, list) else 0
            no_count = len(new_objects) if isinstance(new_objects, list) else 0

            # ⭐ 显示完整的 paper_id（重要！）
            text = f"""
[{i}] Paper ID: {paper_id}
   - 标题: {title}
   - 作者: {author_str}
   - 年份: {year}
   - 期刊: {journal}
   - 评分: {score:.2f}
   - 创新点统计: 现象 {np_count}, 方法 {nm_count}, 对象 {no_count}
"""

            # ⭐ 添加创新点详细信息（前2个，避免 Prompt 过长）
            if np_count > 0:
                text += f"   - 新现象（前2个）:\n"
                for j, phen in enumerate(new_phenomena[:2], 1):
                    if isinstance(phen, dict):
                        name = phen.get("name", "")
                        detailed = phen.get("detailed_description", "")
                        text += f"     {j}. {name}\n"
                        if detailed:
                            text += f"        {detailed[:100]}...\n"

            if nm_count > 0:
                text += f"   - 新方法（前2个）:\n"
                for j, meth in enumerate(new_methods[:2], 1):
                    if isinstance(meth, dict):
                        name = meth.get("name", "")
                        detailed = meth.get("detailed_description", "")
                        text += f"     {j}. {name}\n"
                        if detailed:
                            text += f"        {detailed[:100]}...\n"

            formatted.append(text)

        return "\n".join(formatted)

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行概览分析

        Args:
            input_data: 包含以下字段
                - agent_results_summaries: agent_results 汇总
                - paper_metadata: 文献元数据列表
                - min_domains: 最小领域数（可选，默认5）
                - max_domains: 最大领域数（可选，默认10）

        Returns:
            概览分析结果，包含：
                - domains: 领域列表（AI 推断）
                - research_hotspots: 研究热点
                - time_trends: 时间趋势分析
                - top_papers: Top 10 高影响力文献
        """
        self.log_progress("开始 Phase 1 概览分析...")

        # 提取参数
        agent_results_summaries = input_data.get("agent_results_summaries", [])
        min_domains = input_data.get("min_domains", 5)
        max_domains = input_data.get("max_domains", 10)

        # 准备摘要
        summaries_text = self._prepare_summaries(
            agent_results_summaries, max_papers=100
        )

        # 构造 Prompt
        prompt = OVERVIEW_PROMPT.format(
            agent_results_summaries=summaries_text,
            min_domains=min_domains,
            max_domains=max_domains,
        )

        # ⭐ 添加 Prompt 长度检查
        prompt_length = len(prompt)
        self.log_progress(f"Prompt 长度: {prompt_length} 字符")

        # ⭐ 估算 token 数量（1 token ≈ 2-3 字符）
        estimated_tokens = int(prompt_length / 2)  # 保守估计
        self.log_progress(f"预估 token 数: ~{estimated_tokens} (GLM-4.7 上下文限制: 200K)")

        if estimated_tokens > 150000:  # ⭐ 警告阈值（留 50K 余量给输出）
            self.log_progress(f"⚠️ 警告：Prompt 预估 {estimated_tokens} tokens，接近 GLM-4.7 上下文限制")
            self.log_progress(f"💡 建议：减少文献数量或缩短 Prompt")
        elif estimated_tokens > 180000:  # ⭐ 错误阈值（留 20K 余量）
            self.log_progress(f"❌ 错误：Prompt 预估 {estimated_tokens} tokens，超过安全限制")
            self.log_progress(f"💡 必须：减少文献数量到 {int(180000 * 2 / 1000)} 篇以下")
            return self._get_empty_result()

        self.log_progress(f"调用 {self.model} API...")  # ⭐ 显示实际使用的模型

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
        required_fields = [
            "phase",
            "domains",
            "research_hotspots",
            "time_trends",
            "top_papers",
        ]
        if not self.validate_result(result, required_fields):
            self.log_progress("结果验证失败")
            return self._get_empty_result()

        self.log_progress("概览分析完成")
        return result

    def _get_empty_result(self) -> Dict[str, Any]:
        """返回空结果（失败时使用）"""
        return {
            "phase": "overview",
            "domains": [],
            "research_hotspots": [],
            "time_trends": {
                "2018-2020": {"themes": [], "description": ""},
                "2021-2022": {"themes": [], "description": ""},
                "2023-2026": {"themes": [], "description": ""},
            },
            "top_papers": [],
            "summary": "分析失败",
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
        agent = OverviewAgent(keys_file="config/api_keys.txt", model="glm-4.7")

        # 模拟输入数据
        input_data = {
            "agent_results_summaries": [
                {
                    "metadata": {
                        "paper_id": "2026_Test_Paper_1",
                        "title": "A Novel Optimization Method for Wind Turbine Blades",
                        "authors": ["Zhang San", "Li Si", "Wang Wu"],
                        "year": 2026,
                        "journal": "Energy",
                        "score": 0.85,
                    },
                    "innovation_summary": {
                        "new_phenomena_count": 1,
                        "new_methods_count": 2,
                        "new_objects_count": 0,
                    },
                }
            ],
            "min_domains": 5,
            "max_domains": 10,
        }

        # 执行分析
        result = agent.analyze(input_data)

        print(f"\n📊 分析结果:")
        # ⭐ 安全打印 JSON（处理特殊字符）
        try:
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            print(result_json.encode('gbk', errors='replace').decode('gbk'))
        except Exception as e:
            print(f"⚠️ 无法完整显示结果（包含特殊字符）: {e}")
            print(f"结果包含 {len(result.get('domains', []))} 个领域")

        # 保存结果
        agent.save_result(result, "data/processed/phase1_overview.json")
        print(f"\n✅ 结果已保存到: data/processed/phase1_overview.json")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
