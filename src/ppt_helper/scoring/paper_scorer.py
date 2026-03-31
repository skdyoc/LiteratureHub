"""
文献评分模块（LiteratureHub PPT Helper 版本）

功能：
1. 根据影响因子计算评分（使用 JCR 期刊数据库）
2. 根据年份计算时间权重
3. 综合评分（影响因子70% + 时间30%）
4. 生成文献排名

与 Wind-Aero-Literature-Analysis-System 的评分逻辑保持一致

使用 impact_factor 包获取真实的 JCR 分区和影响因子数据
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 导入 JCR 期刊数据库
try:
    from impact_factor.core import Factor
    JCR_DB_AVAILABLE = True
    logger.info("JCR 期刊数据库加载成功")
except ImportError:
    JCR_DB_AVAILABLE = False
    logger.warning("impact_factor 包未安装，将使用基础评分方法。请运行: pip install impact-factor")


@dataclass
class JournalImpactData:
    """期刊影响因子数据（基于 JCR 分区）"""

    # Q1 期刊（各细分等级）
    Q1_TOP = 100.0   # 顶级期刊（Nature, Science, Cell 等）
    Q1_HIGH = 97.0   # Q1 高分区（IF >= 10）
    Q1_MID = 93.0    # Q1 中分区（IF 5-10）
    Q1_LOW = 88.0    # Q1 低分区（IF 3-5）

    # Q2 期刊
    Q2_HIGH = 83.0   # Q2 高分区（IF 3-4）
    Q2_MID = 78.0    # Q2 中分区（IF 2-3）
    Q2_LOW = 73.0    # Q2 低分区（IF 1.5-2）

    # Q3 期刊
    Q3_HIGH = 68.0   # Q3 高分区（IF 1.5-2）
    Q3_MID = 63.0    # Q3 中分区（IF 1-1.5）
    Q3_LOW = 58.0    # Q3 低分区（IF 0.8-1）

    # Q4 期刊
    Q4_HIGH = 53.0   # Q4 高分区（IF 0.8-1）
    Q4_MID = 48.0    # Q4 中分区（IF 0.5-0.8）
    Q4_LOW = 43.0    # Q4 低分区（IF < 0.5）

    # 未分类期刊
    OTHER = 35.0


class PaperScorer:
    """文献评分器（基于 JCR 期刊数据库）"""

    def __init__(self):
        """初始化评分器"""
        self.default_score = 50.0

        # 初始化 JCR 数据库
        self.jcr_db = None
        if JCR_DB_AVAILABLE:
            try:
                self.jcr_db = Factor()
                logger.info("JCR 期刊数据库初始化成功")
            except Exception as e:
                logger.warning(f"JCR 数据库初始化失败: {e}")

        # 顶级期刊列表（特殊处理）
        self.top_journals = {
            'nature', 'science', 'cell',
            'nature materials', 'nature nanotechnology',
            'nature energy', 'nature communications',
            'science advances', 'science translational medicine'
        }

    def calculate_impact_score(self, journal: str, impact_factor: float = None) -> float:
        """
        计算影响因子评分（0-100）

        使用 JCR 期刊数据库获取真实的分区和影响因子数据

        Args:
            journal: 期刊名称
            impact_factor: 影响因子（如果有）

        Returns:
            影响因子评分
        """
        # 1. 如果提供了IF，使用提供的IF
        if impact_factor is not None:
            return self._score_by_impact_factor(impact_factor)

        # 2. 使用 JCR 数据库查询
        if self.jcr_db is not None:
            return self._score_by_jcr_database(journal)

        # 3. 降级方案：顶级期刊识别
        return self._score_by_top_journal_detection(journal)

    def _score_by_jcr_database(self, journal: str) -> float:
        """
        使用 JCR 数据库计算评分

        Args:
            journal: 期刊名称

        Returns:
            影响因子评分
        """
        try:
            # 查询 JCR 数据库
            result = self.jcr_db.search(journal)

            if result and len(result) > 0:
                # 取第一个匹配结果
                jcr_data = result[0]

                # 提取分区和影响因子
                quartile = jcr_data.get('quartile', '')  # Q1, Q2, Q3, Q4
                impact_factor = float(jcr_data.get('factor', 0))

                logger.debug(f"JCR 查询成功: {journal} -> {quartile}, IF={impact_factor}")

                # 根据分区和影响因子计算评分
                return self._score_by_quartile_and_if(quartile, impact_factor)

        except Exception as e:
            logger.debug(f"JCR 查询失败: {journal}, 错误: {e}")

        # JCR 查询失败，降级到基础方法
        return self._score_by_top_journal_detection(journal)

    def _score_by_quartile_and_if(self, quartile: str, impact_factor: float) -> float:
        """
        根据分区和影响因子计算评分

        Args:
            quartile: JCR 分区（Q1, Q2, Q3, Q4）
            impact_factor: 影响因子

        Returns:
            评分（0-100）
        """
        quartile = quartile.upper().strip()

        # Q1 期刊
        if quartile == 'Q1':
            if impact_factor >= 10:
                return JournalImpactData.Q1_HIGH
            elif impact_factor >= 5:
                return JournalImpactData.Q1_MID
            else:
                return JournalImpactData.Q1_LOW

        # Q2 期刊
        elif quartile == 'Q2':
            if impact_factor >= 3:
                return JournalImpactData.Q2_HIGH
            elif impact_factor >= 2:
                return JournalImpactData.Q2_MID
            else:
                return JournalImpactData.Q2_LOW

        # Q3 期刊
        elif quartile == 'Q3':
            if impact_factor >= 1.5:
                return JournalImpactData.Q3_HIGH
            elif impact_factor >= 1:
                return JournalImpactData.Q3_MID
            else:
                return JournalImpactData.Q3_LOW

        # Q4 期刊
        elif quartile == 'Q4':
            if impact_factor >= 0.8:
                return JournalImpactData.Q4_HIGH
            elif impact_factor >= 0.5:
                return JournalImpactData.Q4_MID
            else:
                return JournalImpactData.Q4_LOW

        # 未分区
        else:
            return self._score_by_impact_factor(impact_factor)

    def _score_by_top_journal_detection(self, journal: str) -> float:
        """
        顶级期刊识别（降级方案）

        Args:
            journal: 期刊名称

        Returns:
            影响因子评分
        """
        journal_lower = journal.lower()

        # 检查是否为顶级期刊
        for top_journal in self.top_journals:
            if top_journal in journal_lower:
                logger.debug(f"识别为顶级期刊: {journal}")
                return JournalImpactData.Q1_TOP

        # 默认评分
        logger.debug(f"期刊 '{journal}' 未找到 JCR 数据，使用默认评分: {self.default_score:.0f}分")
        return self.default_score

    def _score_by_impact_factor(self, impact_factor: float) -> float:
        """
        根据影响因子值计算评分

        Args:
            impact_factor: 影响因子值

        Returns:
            评分（0-100）
        """
        if impact_factor >= 5.0:
            return JournalImpactData.Q1_HIGH
        elif impact_factor >= 3.0:
            return JournalImpactData.Q1_MID
        elif impact_factor >= 1.0:
            return JournalImpactData.Q1_LOW
        elif impact_factor >= 0.5:
            return JournalImpactData.Q4_HIGH
        else:
            return JournalImpactData.OTHER

    def calculate_time_score(self, year: int, current_year: int = 2026) -> float:
        """
        计算时间权重评分（0-100）

        Args:
            year: 论文发表年份
            current_year: 当前年份

        Returns:
            时间权重评分
        """
        age = current_year - year

        # 时间衰减公式
        # 当年/去年: 95分
        # 2-3年前: 85分
        # 4-5年前: 70分
        # 5-10年前: 40分
        # >10年前: 10分

        if age <= 1:
            return 95.0
        elif age <= 3:
            return 85.0
        elif age <= 5:
            return 70.0
        elif age <= 10:
            return 40.0
        else:
            return 10.0

    def calculate_final_score(
        self,
        journal: str,
        year: int,
        impact_factor: float = None
    ) -> float:
        """
        计算综合评分

        Args:
            journal: 期刊名称
            year: 发表年份
            impact_factor: 影响因子（可选）

        Returns:
            综合评分（0-100）
        """
        impact_score = self.calculate_impact_score(journal, impact_factor)
        time_score = self.calculate_time_score(year)

        # 影响因子70% + 时间权重30%
        final_score = impact_score * 0.7 + time_score * 0.3

        logger.debug(f"评分: {journal} ({year}) - 影响:{impact_score:.1f} 时间:{time_score:.1f} = {final_score:.1f}")

        return round(final_score, 2)

    def rank_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对文献进行评分并排名

        Args:
            papers: 论文列表，格式:
                [
                    {
                        "paper_id": "xxx",
                        "title": "xxx",
                        "authors": [...],
                        "year": 2026,
                        "journal": "Energy",
                        "impact_factor": 5.0  # 可选
                    },
                    ...
                ]

        Returns:
            排名后的文献列表，格式:
            [
                {
                    "paper_id": "xxx",
                    "title": "xxx",
                    "authors": [...],
                    "year": 2026,
                    "journal": "Energy",
                    "score": 98.5,
                    "rank": 1
                },
                ...
            ]
        """
        scored_papers = []

        for paper in papers:
            # 计算评分
            score = self.calculate_final_score(
                journal=paper.get('journal', ''),
                year=paper.get('year', 2020),
                impact_factor=paper.get('impact_factor')
            )

            scored_papers.append({
                'paper_id': paper.get('paper_id', ''),
                'title': paper.get('title', ''),
                'authors': paper.get('authors', []),
                'year': paper.get('year', 2020),
                'journal': paper.get('journal', ''),
                'score': score,
                'rank': 0  # 稍后计算排名
            })

        # 按评分降序排序
        scored_papers.sort(key=lambda x: x['score'], reverse=True)

        # 分配排名
        for i, item in enumerate(scored_papers, 1):
            item['rank'] = i

        logger.info(f"文献评分完成，共 {len(scored_papers)} 篇")
        logger.info(f"最高分: {scored_papers[0]['score']:.1f}")
        logger.info(f"最低分: {scored_papers[-1]['score']:.1f}")

        return scored_papers


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import sys
    import io

    # Windows UTF-8 支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    # 示例数据
    papers = [
        {
            "paper_id": "2026_Test_Paper_1",
            "title": "A Novel Method for Wind Turbine Optimization",
            "authors": ["Zhang San", "Li Si"],
            "year": 2026,
            "journal": "Energy",
            "impact_factor": 5.5
        },
        {
            "paper_id": "2020_Test_Paper_2",
            "title": "Old Research on Aerodynamics",
            "authors": ["Wang Wu"],
            "year": 2020,
            "journal": "Journal of Physics",
            "impact_factor": 2.5
        }
    ]

    # 创建评分器
    scorer = PaperScorer()

    # 评分和排名
    ranked_papers = scorer.rank_papers(papers)

    # 打印结果
    print("\n排名结果:")
    print("-" * 80)
    for item in ranked_papers:
        print(f"#{item['rank']:3d} [{item['score']:6.2f}分] "
              f"{item['year']} | {item['journal'][:40]:<40} | "
              f"{item['title'][:50]}...")
