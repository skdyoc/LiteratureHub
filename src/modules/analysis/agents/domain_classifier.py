"""
技术领域分类模块
Domain Classifier Module

功能：
1. 根据关键词将文献分类到技术领域
2. 支持多领域标签
3. 按领域组织文献
"""

import logging
from typing import List, Set, Dict

logger = logging.getLogger(__name__)


class DomainClassifier:
    """技术领域分类器"""

    # 领域关键词映射
    DOMAIN_KEYWORDS = {
        'control_systems': {
            'primary': ['control', 'controller', 'pitch', 'yaw', 'torque',
                        'optimization', 'trpo', 'mpc', 'pid', 'lqr', 'rl', 'dl',
                        'reinforcement', 'feedback', 'dynamics'],
            'secondary': ['actuator', 'sensor', 'turbine', 'rotor', 'blade', 'tower']
        },

        'blade_design': {
            'primary': ['blade', 'airfoil', 'wing', 'aerodynamic', 'design', 'shape',
                        'geometry', 'optimization', 'twist', 'chord', 'span',
                        'thickness', 'camber', 'airfoils'],
            'secondary': ['profile', 'section', 'structural', 'load', 'fatigue']
        },

        'aerodynamic_performance': {
            'primary': ['aerodynamic', 'performance', 'flow', 'cfd', 'simulation',
                        'wind tunnel', 'experimental', 'wake', 'turbulence',
                        'boundary layer', 'separation', 'lift', 'drag',
                        'power', 'efficiency', 'coefficient'],
            'secondary': ['nacelle', 'rotor', 'blade', 'airflow', 'viscous']
        },

        'floating_platforms': {
            'primary': ['floating', 'offshore', 'platform', 'spar', 'mooring',
                        'dynamic', 'response', 'motion', 'stability',
                        'loads', 'wave', 'wind', 'current'],
            'secondary': ['turret', 'substation', 'cable', 'anchor']
        },

        'wind_farm_layout': {
            'primary': ['farm', 'layout', 'wake', 'array', 'park', 'spacing',
                        'efficiency', 'optimization', 'micrositing'],
            'secondary': ['turbine', 'position', 'energy', 'capture']
        },

        'load_analysis': {
            'primary': ['load', 'fatigue', 'stress', 'extreme', 'wind', 'condition',
                        'safety', 'reliability', 'lifetime', 'damage'],
            'secondary': ['blade', 'tower', 'foundation', 'structural']
        }
    }

    def __init__(self):
        """初始化分类器"""
        self.domains = list(self.DOMAIN_KEYWORDS.keys())

    def classify_paper(self, paper) -> List[str]:
        """
        分类文献到技术领域

        Args:
            paper: 论文对象

        Returns:
            领域列表
        """
        domains = []

        # 收集文本
        title_lower = paper.metadata.title.lower()
        keywords_lower = [kw.lower() for kw in (paper.content.keywords or [])]
        abstract_lower = (paper.content.abstract or "").lower()[:500]

        combined_text = f"{title_lower} {' '.join(keywords_lower)} {abstract_lower}"

        # 对每个领域进行匹配
        for domain, keyword_dict in self.DOMAIN_KEYWORDS.items():
            score = 0

            # 主要关键词权重更高
            for keyword in keyword_dict['primary']:
                if keyword in combined_text:
                    score += 2

            # 次要关键词
            for keyword in keyword_dict['secondary']:
                if keyword in combined_text:
                    score += 1

            # 如果有匹配，添加到领域列表
            if score >= 2:
                domains.append(domain)
                logger.debug(f"文献 '{paper.metadata.title[:30]}...' 匹配领域: {domain} (score: {score})")

        if not domains:
            # 默认分类
            domains.append('general')

        return domains

    def group_papers_by_domain(self, scored_papers: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按领域组织文献

        Args:
            scored_papers: 已评分的文献列表

        Returns:
            按领域分组的文献字典
        """
        domain_groups = {domain: [] for domain in self.domains}
        domain_groups['general'] = []

        for item in scored_papers:
            paper = item['paper']

            # 分类
            domains = self.classify_paper(paper)

            # 添加到对应的领域组
            for domain in domains:
                if domain in domain_groups:
                    domain_groups[domain].append(item)
                else:
                    domain_groups['general'].append(item)

        # 统计每个领域的文献数
        for domain, papers in domain_groups.items():
            if papers:
                logger.info(f"领域 '{domain}': {len(papers)} 篇文献")

        return domain_groups
