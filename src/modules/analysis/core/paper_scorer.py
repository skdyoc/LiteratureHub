"""
文献评分模块
Paper Scoring Module

功能：
1. 根据影响因子计算评分
2. 根据年份计算时间权重
3. 综合评分（影响因子70% + 时间30%）
4. 生成文献排名
5. 从 journals.yaml 读取期刊影响因子数据
6. 支持智能搜索和关键词匹配
"""

import logging
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class JournalImpactData:
    """期刊影响因子数据"""

    # Q1期刊
    Q1_HIGH = 100.0  # IF > 5.0
    Q1_MID = 95.0   # IF 3.0-5.0
    Q1_LOW = 90.0    # IF 1.0-3.0

    # Q2期刊
    Q2_HIGH = 85.0   # IF 2.0-3.0
    Q2_MID = 80.0    # IF 1.5-2.0
    Q2_LOW = 75.0    # IF 1.0-1.5

    # Q3期刊
    Q3_HIGH = 70.0   # IF 1.0-2.0
    Q3_MID = 65.0    # IF 0.8-1.0
    Q3_LOW = 60.0    # IF 0.5-0.8

    # Q4期刊
    Q4_HIGH = 55.0   # IF 0.5-1.0
    Q4_MID = 50.0    # IF 0.3-0.5
    Q4_LOW = 45.0    # IF 0.1-0.3

    # 未分类期刊
    OTHER = 30.0


class PaperScorer:
    """文献评分器"""

    def __init__(self, config_path: str = None):
        """
        初始化评分器

        Args:
            config_path: journals.yaml 配置文件路径
        """
        # 加载期刊影响因子数据库
        self.journal_impact_db = {}
        self.conference_impact_db = {}
        self.keyword_rules = []
        self.default_score = 50.0

        # 加载配置文件
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "journals.yaml"

        self._load_journal_db(config_path)

    def _load_journal_db(self, config_path: str):
        """
        从 YAML 文件加载期刊数据库

        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 加载各个等级的期刊数据
            all_sections = [
                'q1_high_impact', 'q1_mid_impact',
                'q2_high_impact', 'q2_mid_impact',
                'q3_impact', 'q4_impact'
            ]

            for section in all_sections:
                if section in config:
                    self.journal_impact_db.update(config[section])

            # 加载会议数据
            if 'conferences' in config:
                for conf_name, conf_data in config['conferences'].items():
                    self.conference_impact_db[conf_name] = conf_data

            # 加载关键词规则
            if 'default_rules' in config and 'keywords' in config['default_rules']:
                self.keyword_rules = config['default_rules']['keywords']

            # 加载默认评分
            if 'default_rules' in config and 'unknown_journal_score' in config['default_rules']:
                self.default_score = config['default_rules']['unknown_journal_score']

            logger.info(f"✓ 成功加载期刊数据库：{len(self.journal_impact_db)} 种期刊")
            logger.info(f"✓ 成功加载会议数据库：{len(self.conference_impact_db)} 个会议")
            logger.info(f"✓ 成功加载关键词规则：{len(self.keyword_rules)} 条")

        except FileNotFoundError:
            logger.warning(f"⚠️  期刊数据库文件未找到: {config_path}")
            logger.warning("⚠️  使用内置的小型数据库")
        except Exception as e:
            logger.error(f"❌ 加载期刊数据库失败: {e}")
            logger.warning("⚠️  使用内置的小型数据库")

    def _find_journal_by_keyword(self, journal: str) -> Optional[float]:
        """
        根据关键词查找期刊评分

        Args:
            journal: 期刊名称

        Returns:
            找到的评分，否则返回 None
        """
        journal_lower = journal.lower()

        for rule in self.keyword_rules:
            keyword = rule['keyword'].lower()
            if keyword in journal_lower:
                logger.debug(f"  关键词匹配: '{keyword}' → {rule['score']:.0f}分 ({rule['reason']})")
                return rule['score']

        return None

    def calculate_impact_score(self, journal: str, impact_factor: float = None) -> float:
        """
        计算影响因子评分（0-100）

        Args:
            journal: 期刊名称
            impact_factor: 影响因子（如果有）

        Returns:
            影响因子评分
        """
        # 1. 如果提供了IF，使用提供的IF
        if impact_factor is not None:
            return self._score_by_impact_factor(impact_factor)

        # 2. 从期刊数据库精确查找
        journal_data = self.journal_impact_db.get(journal)
        if journal_data:
            if isinstance(journal_data, dict):
                # 新格式的 YAML 数据
                if 'impact_factor' in journal_data:
                    return self._score_by_impact_factor(journal_data['impact_factor'])
                elif 'equivalent_impact' in journal_data:
                    # 会议论文使用等效评分
                    return journal_data['equivalent_impact']
            else:
                # 旧格式的直接IF值
                return self._score_by_impact_factor(journal_data)

        # 3. 从会议数据库查找
        conf_data = self.conference_impact_db.get(journal)
        if conf_data and 'equivalent_impact' in conf_data:
            logger.debug(f"  会议匹配: {journal} → {conf_data['equivalent_impact']:.0f}分")
            return conf_data['equivalent_impact']

        # 4. 关键词匹配
        keyword_score = self._find_journal_by_keyword(journal)
        if keyword_score is not None:
            return keyword_score

        # 5. 默认评分
        logger.warning(f"⚠️  期刊 '{journal}' 未找到影响因子数据，使用默认评分: {self.default_score:.0f}分")
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
        # 当年/去年: 90-100分
        # 2-3年前: 80-90分
        # 4-5年前: 60-80分
        # 5-10年前: 10-60分
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

    def rank_papers(self, papers: List[Any]) -> List[Dict[str, Any]]:
        """
        对文献进行评分并排名

        Args:
            papers: 论文列表

        Returns:
            排名后的文献列表
        """
        scored_papers = []

        for paper in papers:
            # 计算评分
            score = self.calculate_final_score(
                journal=paper.metadata.journal,
                year=paper.metadata.year,
                impact_factor=paper.metadata.impact_factor if hasattr(paper.metadata, 'impact_factor') else None
            )

            scored_papers.append({
                'paper': paper,
                'paper_id': paper.folder_name,
                'title': paper.metadata.title,
                'authors': paper.metadata.authors,
                'year': paper.metadata.year,
                'journal': paper.metadata.journal,
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
