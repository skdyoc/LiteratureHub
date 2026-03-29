# ========= Copyright 2025-2026 @ LiteratureHub All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2025-2026 @ LiteratureHub All Rights Reserved. =========

"""
文献评分系统

基于影响因子、时间权重、AI 分析结果进行综合评分。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class ScoringSystem:
    """文献评分系统

    计算文献的综合评分，包括：
    1. 影响因子评分（70%）
    2. 时间权重评分（30%）
    3. AI 分析质量评分（可选）

    使用示例：
    ```python
    scorer = ScoringSystem()

    # 计算单篇文献评分
    score = scorer.calculate_score(
        impact_factor=3.5,
        publication_year=2023,
        citation_count=50
    )

    # 计算综合评分（基于 AI 分析结果）
    overall_score = scorer.calculate_overall_score(
        paper_id="2026_paper_001",
        analysis_results={
            "innovation": {...},
            "motivation": {...}
        }
    )

    # 批量评分并排名
    ranked_papers = scorer.rank_papers(papers)
    ```
    """

    def __init__(self):
        """初始化评分系统"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 评分权重配置
        self.weights = {
            "impact_factor": 0.70,      # 影响因子权重
            "time_decay": 0.30,         # 时间权重
            "ai_quality": 0.10          # AI 分析质量（可选，作为加成）
        }

        # 影响因子范围（用于归一化）
        self.impact_factor_range = (0.0, 10.0)

        # 当前年份（用于时间衰减计算）
        self.current_year = datetime.now().year

    def calculate_score(
        self,
        impact_factor: float = 0.0,
        publication_year: int = None,
        citation_count: int = 0,
        ai_analysis_score: float = None
    ) -> float:
        """计算文献评分

        Args:
            impact_factor: 影响因子
            publication_year: 发表年份
            citation_count: 引用次数
            ai_analysis_score: AI 分析评分（可选）

        Returns:
            综合评分（0-100）
        """
        # 1. 影响因子评分（归一化到 0-100）
        if_score = self._normalize_impact_factor(impact_factor)

        # 2. 时间权重评分（越新越高）
        time_score = self._calculate_time_score(publication_year)

        # 3. 引用次数加成（可选）
        citation_bonus = self._calculate_citation_bonus(citation_count)

        # 4. AI 分析质量加成（可选）
        ai_bonus = 0.0
        if ai_analysis_score is not None:
            ai_bonus = ai_analysis_score * self.weights["ai_quality"]

        # 综合评分
        base_score = (
            if_score * self.weights["impact_factor"] +
            time_score * self.weights["time_decay"]
        )

        final_score = min(100.0, base_score + citation_bonus + ai_bonus)

        return round(final_score, 2)

    def calculate_overall_score(
        self,
        paper_id: str,
        analysis_results: Dict[str, Any]
    ) -> float:
        """基于 AI 分析结果计算综合评分

        Args:
            paper_id: 文献 ID
            analysis_results: AI 分析结果字典

        Returns:
            综合评分
        """
        # 提取各维度的评分
        scores = []

        # 创新点评分
        if "innovation" in analysis_results:
            innovation_data = analysis_results["innovation"]
            if "overall_innovation_level" in innovation_data:
                level = innovation_data["overall_innovation_level"]
                scores.append(self._level_to_score(level))

        # 动机评分
        if "motivation" in analysis_results:
            motivation_data = analysis_results["motivation"]
            if "motivation_strength" in motivation_data:
                strength = motivation_data["motivation_strength"]
                scores.append(self._level_to_score(strength))

        # 技术路线评分
        if "roadmap" in analysis_results:
            roadmap_data = analysis_results["roadmap"]
            if "feasibility" in roadmap_data:
                feasibility = roadmap_data["feasibility"]
                if isinstance(feasibility, dict) and "score" in feasibility:
                    scores.append(feasibility["score"] * 100)

        # 影响评分
        if "impact" in analysis_results:
            impact_data = analysis_results["impact"]
            academic_score = impact_data.get("academic_impact", {}).get("score", 0)
            practical_score = impact_data.get("practical_impact", {}).get("score", 0)
            avg_impact = (academic_score + practical_score) / 2
            scores.append(avg_impact * 100)

        # 计算平均评分
        if scores:
            ai_score = sum(scores) / len(scores)
        else:
            ai_score = 50.0  # 默认中等评分

        return round(ai_score, 2)

    def rank_papers(
        self,
        papers: List[Dict[str, Any]],
        top_n: int = None
    ) -> List[Dict[str, Any]]:
        """对文献进行排名

        Args:
            papers: 文献列表（需包含评分字段）
            top_n: 返回前 N 篇（可选）

        Returns:
            排序后的文献列表
        """
        # 按评分降序排序
        sorted_papers = sorted(
            papers,
            key=lambda p: p.get("overall_score", 0),
            reverse=True
        )

        # 添加排名
        for i, paper in enumerate(sorted_papers):
            paper["rank"] = i + 1

        # 返回 Top N
        if top_n:
            return sorted_papers[:top_n]

        return sorted_papers

    def _normalize_impact_factor(self, impact_factor: float) -> float:
        """归一化影响因子

        Args:
            impact_factor: 原始影响因子

        Returns:
            归一化评分（0-100）
        """
        min_if, max_if = self.impact_factor_range

        # 归一化到 0-1
        normalized = (impact_factor - min_if) / (max_if - min_if)

        # 转换到 0-100
        score = normalized * 100

        # 限制范围
        return max(0, min(100, score))

    def _calculate_time_score(self, publication_year: int) -> float:
        """计算时间权重评分

        Args:
            publication_year: 发表年份

        Returns:
            时间评分（0-100）
        """
        if not publication_year:
            return 50.0  # 默认中等评分

        # 计算年份差
        years_old = self.current_year - publication_year

        # 指数衰减
        # 最新文献：100分
        # 1年前：85分
        # 2年前：70分
        # 3年前：60分
        # 5年前：40分
        # 10年前：15分
        decay_factor = 0.85
        score = 100 * (decay_factor ** years_old)

        return max(0, min(100, score))

    def _calculate_citation_bonus(self, citation_count: int) -> float:
        """计算引用次数加成

        Args:
            citation_count: 引用次数

        Returns:
            加成分数（0-10）
        """
        if citation_count <= 0:
            return 0.0

        # 对数缩放
        import math
        bonus = math.log10(citation_count + 1) * 2

        # 限制最大加成
        return min(10.0, bonus)

    def _level_to_score(self, level: str) -> float:
        """将等级转换为评分

        Args:
            level: 等级（high/medium/low/strong/weak）

        Returns:
            评分（0-100）
        """
        level_scores = {
            "high": 90.0,
            "strong": 85.0,
            "medium": 70.0,
            "low": 50.0,
            "weak": 40.0
        }

        return level_scores.get(level.lower(), 60.0)

    def get_scoring_statistics(
        self,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取评分统计信息

        Args:
            papers: 文献列表

        Returns:
            统计信息
        """
        if not papers:
            return {
                "total": 0,
                "average_score": 0,
                "median_score": 0,
                "max_score": 0,
                "min_score": 0,
                "score_distribution": {}
            }

        scores = [p.get("overall_score", 0) for p in papers]

        # 分数分布
        distribution = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "50-59": 0,
            "0-49": 0
        }

        for score in scores:
            if score >= 90:
                distribution["90-100"] += 1
            elif score >= 80:
                distribution["80-89"] += 1
            elif score >= 70:
                distribution["70-79"] += 1
            elif score >= 60:
                distribution["60-69"] += 1
            elif score >= 50:
                distribution["50-59"] += 1
            else:
                distribution["0-49"] += 1

        return {
            "total": len(papers),
            "average_score": round(sum(scores) / len(scores), 2),
            "median_score": round(sorted(scores)[len(scores) // 2], 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "score_distribution": distribution
        }

    def set_weights(self, impact_factor: float = None, time_decay: float = None):
        """设置评分权重

        Args:
            impact_factor: 影响因子权重
            time_decay: 时间权重
        """
        if impact_factor is not None:
            self.weights["impact_factor"] = impact_factor

        if time_decay is not None:
            self.weights["time_decay"] = time_decay

        self.logger.info(f"评分权重已更新: {self.weights}")
