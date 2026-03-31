"""
领域分类器 Agent

职责：根据文献内容判断其属于哪个研究领域
"""

import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..prompts import DOMAIN_CLASSIFIER_PROMPT


class DomainClassifierAgent(BaseAgent):
    """领域分类器 Agent"""

    def __init__(self, keys_file: str, model: str = "glm-4.7"):
        super().__init__(keys_file, model)
        self.agent_name = "DomainClassifierAgent"

    def classify_single(
        self,
        title: str,
        abstract: str,
        innovation_points: str,
        candidate_domains: List[str],
    ) -> Dict[str, Any]:
        """
        分类单篇文献

        Args:
            title: 文献标题
            abstract: 文献摘要
            innovation_points: 创新点
            candidate_domains: 候选领域列表

        Returns:
            分类结果，包含：
                - domain: 领域名称
                - confidence: 置信度
                - reason: 理由
        """
        # 构造 Prompt
        prompt = DOMAIN_CLASSIFIER_PROMPT.format(
            title=title,
            abstract=abstract,
            innovation_points=innovation_points,
            candidate_domains="\n".join([f"- {d}" for d in candidate_domains]),
        )

        # 调用 API
        response = self._call_glm_api(prompt, temperature=0.3)  # 低温度以提高准确性

        if not response:
            return {"domain": "OTHER", "confidence": 0.0, "reason": "API 调用失败"}

        # 解析响应
        result = self._parse_json_response(response)

        if not result:
            return {"domain": "OTHER", "confidence": 0.0, "reason": "JSON 解析失败"}

        # 验证结果
        required_fields = ["domain", "confidence", "reason"]
        if not self.validate_result(result, required_fields):
            return {"domain": "OTHER", "confidence": 0.0, "reason": "结果验证失败"}

        return result

    def classify_batch(
        self, papers: List[Dict[str, Any]], candidate_domains: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量分类文献

        Args:
            papers: 文献列表，每个文献包含 title, abstract, innovation_points
            candidate_domains: 候选领域列表

        Returns:
            分类结果字典 {paper_id: classification_result}
        """
        self.log_progress(f"开始批量分类 {len(papers)} 篇文献...")

        results = {}

        for i, paper in enumerate(papers, 1):
            paper_id = paper.get("paper_id", f"paper_{i}")

            self.log_progress(f"[{i}/{len(papers)}] 分类: {paper_id}")

            result = self.classify_single(
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                innovation_points=paper.get("innovation_points", ""),
                candidate_domains=candidate_domains,
            )

            results[paper_id] = result

            # 简单的速率限制
            import time

            time.sleep(1)

        self.log_progress(f"批量分类完成")
        return results

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析（兼容 BaseAgent 接口）

        Args:
            input_data: 输入数据

        Returns:
            分析结果
        """
        papers = input_data.get("papers", [])
        candidate_domains = input_data.get("candidate_domains", [])

        return self.classify_batch(papers, candidate_domains)


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
        agent = DomainClassifierAgent(keys_file="config/api_keys.txt", model="glm-4.7")

        # 候选领域
        candidate_domains = [
            "叶片气动优化",
            "尾流效应与风电场布局",
            "气动噪声机理与控制",
            "风载与结构动力学",
            "风能资源评估",
        ]

        # 单篇分类示例
        result = agent.classify_single(
            title="Aerodynamic optimization of wind turbine blades using genetic algorithm",
            abstract="This paper proposes a genetic algorithm-based optimization method...",
            innovation_points="New optimization method, 15% efficiency improvement",
            candidate_domains=candidate_domains,
        )

        print(f"📊 分类结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
