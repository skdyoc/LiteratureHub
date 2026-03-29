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
领域分类器

基于关键词和 AI 分析进行技术领域分类。
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import json


class DomainClassifier:
    """领域分类器

    根据文献内容和 AI 分析结果，将文献分类到相应的技术领域。

    使用示例：
    ```python
    classifier = DomainClassifier()

    # 加载领域定义
    classifier.load_domains("config/domains.yaml")

    # 分类文献
    classification = await classifier.classify(
        paper_content="# Paper Title\\n...",
        analysis_results={
            "innovation": {...},
            "roadmap": {...}
        }
    )

    # 批量分类
    classifications = await classifier.batch_classify(papers)
    ```
    """

    # 默认领域定义
    DEFAULT_DOMAINS = {
        "Aerodynamic Optimization": {
            "keywords": [
                "aerodynamic", "drag reduction", "lift", "airfoil",
                "blade design", "flow control", "wake", "turbulence"
            ],
            "subdomains": [
                "Blade Design",
                "Flow Control",
                "Wake Analysis",
                "Turbulence Modeling"
            ]
        },
        "Wind Turbine Control": {
            "keywords": [
                "control system", "pitch control", "yaw control",
                "power optimization", "load reduction", "fault detection"
            ],
            "subdomains": [
                "Pitch Control",
                "Yaw Control",
                "Power Optimization",
                "Fault Detection"
            ]
        },
        "Wind Farm Layout": {
            "keywords": [
                "wind farm", "layout optimization", "wake effect",
                "turbine placement", "array efficiency", "farm design"
            ],
            "subdomains": [
                "Layout Optimization",
                "Wake Modeling",
                "Array Design",
                "Site Assessment"
            ]
        },
        "Materials and Structures": {
            "keywords": [
                "composite materials", "blade structure", "fatigue",
                "structural health", "lightweight design", "durability"
            ],
            "subdomains": [
                "Composite Materials",
                "Structural Analysis",
                "Fatigue Assessment",
                "Health Monitoring"
            ]
        },
        "Offshore Wind": {
            "keywords": [
                "offshore", "floating platform", "marine environment",
                "wave loading", "foundation design", "installation"
            ],
            "subdomains": [
                "Floating Platforms",
                "Foundation Design",
                "Marine Operations",
                "Environmental Impact"
            ]
        },
        "Wind Resource Assessment": {
            "keywords": [
                "wind resource", "site assessment", "wind speed",
                "turbulence intensity", "wind profile", "meteorological"
            ],
            "subdomains": [
                "Site Assessment",
                "Wind Modeling",
                "Resource Mapping",
                "Climate Analysis"
            ]
        }
    }

    def __init__(self, domains_config: Dict[str, Any] = None):
        """初始化领域分类器

        Args:
            domains_config: 领域配置（可选）
        """
        self.domains = domains_config or self.DEFAULT_DOMAINS
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 构建关键词索引
        self.keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, str]:
        """构建关键词到领域的索引

        Returns:
            关键词索引字典
        """
        index = {}
        for domain_name, domain_info in self.domains.items():
            for keyword in domain_info.get("keywords", []):
                index[keyword.lower()] = domain_name

        return index

    async def classify(
        self,
        paper_content: str,
        analysis_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """分类文献

        Args:
            paper_content: 文献内容
            analysis_results: AI 分析结果（可选）

        Returns:
            分类结果
        """
        self.logger.debug("开始领域分类")

        # 1. 基于关键词的初步分类
        keyword_scores = self._keyword_based_classification(paper_content)

        # 2. 基于 AI 分析结果的细化（如果有）
        if analysis_results:
            ai_scores = self._ai_based_classification(analysis_results)

            # 合并分数
            final_scores = self._merge_scores(keyword_scores, ai_scores)
        else:
            final_scores = keyword_scores

        # 3. 确定主领域和次领域
        primary_domain, secondary_domains = self._determine_domains(final_scores)

        # 4. 识别子领域
        subdomains = self._identify_subdomains(primary_domain, paper_content)

        result = {
            "primary_domain": primary_domain,
            "secondary_domains": secondary_domains,
            "subdomains": subdomains,
            "confidence": final_scores.get(primary_domain, 0.0),
            "all_scores": final_scores
        }

        self.logger.info(f"分类完成: {primary_domain} (置信度: {result['confidence']:.2f})")
        return result

    def _keyword_based_classification(self, content: str) -> Dict[str, float]:
        """基于关键词的分类

        Args:
            content: 文献内容

        Returns:
            领域分数字典
        """
        content_lower = content.lower()

        scores = {}
        for domain_name in self.domains.keys():
            scores[domain_name] = 0.0

        # 统计关键词出现次数
        for keyword, domain in self.keyword_index.items():
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content_lower))
            if count > 0:
                scores[domain] += count

        # 归一化
        total = sum(scores.values())
        if total > 0:
            for domain in scores:
                scores[domain] = scores[domain] / total

        return scores

    def _ai_based_classification(
        self,
        analysis_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """基于 AI 分析的分类

        Args:
            analysis_results: AI 分析结果

        Returns:
            领域分数字典
        """
        scores = {}
        for domain_name in self.domains.keys():
            scores[domain_name] = 0.0

        # 从创新点分析中提取领域信息
        if "innovation" in analysis_results:
            innovation = analysis_results["innovation"]
            if "key_contributions" in innovation:
                contributions = innovation["key_contributions"]
                scores.update(self._extract_domain_from_text(contributions))

        # 从技术路线分析中提取
        if "roadmap" in analysis_results:
            roadmap = analysis_results["roadmap"]
            if "main_approach" in roadmap:
                approach = roadmap["main_approach"]
                approach_text = f"{approach.get('name', '')} {approach.get('description', '')}"
                approach_scores = self._extract_domain_from_text([approach_text])
                for domain, score in approach_scores.items():
                    scores[domain] = max(scores.get(domain, 0), score)

        return scores

    def _extract_domain_from_text(self, texts: List[str]) -> Dict[str, float]:
        """从文本中提取领域信息

        Args:
            texts: 文本列表

        Returns:
            领域分数
        """
        combined_text = " ".join(texts).lower()

        scores = {}
        for keyword, domain in self.keyword_index.items():
            if keyword in combined_text:
                scores[domain] = scores.get(domain, 0) + 0.1

        return scores

    def _merge_scores(
        self,
        keyword_scores: Dict[str, float],
        ai_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """合并关键词和 AI 分数

        Args:
            keyword_scores: 关键词分数
            ai_scores: AI 分数

        Returns:
            合并后的分数
        """
        merged = {}

        for domain in self.domains.keys():
            keyword_score = keyword_scores.get(domain, 0)
            ai_score = ai_scores.get(domain, 0)

            # 加权平均（关键词 60%，AI 40%）
            merged[domain] = keyword_score * 0.6 + ai_score * 0.4

        return merged

    def _determine_domains(
        self,
        scores: Dict[str, float]
    ) -> tuple:
        """确定主领域和次领域

        Args:
            scores: 领域分数

        Returns:
            (主领域, 次领域列表)
        """
        # 排序
        sorted_domains = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 主领域
        primary_domain = sorted_domains[0][0] if sorted_domains else "Unclassified"

        # 次领域（分数 > 0.1 且不是主领域）
        secondary_domains = [
            domain for domain, score in sorted_domains[1:]
            if score > 0.1
        ][:3]  # 最多 3 个次领域

        return primary_domain, secondary_domains

    def _identify_subdomains(
        self,
        primary_domain: str,
        content: str
    ) -> List[str]:
        """识别子领域

        Args:
            primary_domain: 主领域
            content: 文献内容

        Returns:
            子领域列表
        """
        if primary_domain not in self.domains:
            return []

        subdomains = self.domains[primary_domain].get("subdomains", [])
        content_lower = content.lower()

        # 检查每个子领域是否在内容中提及
        matched = []
        for subdomain in subdomains:
            if subdomain.lower() in content_lower:
                matched.append(subdomain)

        return matched

    async def batch_classify(
        self,
        papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量分类

        Args:
            papers: 文献列表（需包含 content 字段）

        Returns:
            分类结果列表
        """
        results = []
        for i, paper in enumerate(papers):
            try:
                classification = await self.classify(
                    paper_content=paper.get("content", ""),
                    analysis_results=paper.get("analysis_results")
                )
                results.append(classification)
                self.logger.info(f"批量分类进度: {i+1}/{len(papers)}")
            except Exception as e:
                self.logger.error(f"分类失败: {e}")
                results.append({
                    "primary_domain": "Unclassified",
                    "error": str(e)
                })

        return results

    def load_domains(self, config_path: str):
        """加载领域配置

        Args:
            config_path: 配置文件路径（YAML 或 JSON）
        """
        path = Path(config_path)

        if not path.exists():
            self.logger.warning(f"配置文件不存在: {config_path}")
            return

        try:
            if path.suffix in ['.yaml', '.yml']:
                import yaml
                with open(path, 'r', encoding='utf-8') as f:
                    self.domains = yaml.safe_load(f)
            elif path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    self.domains = json.load(f)
            else:
                raise ValueError(f"不支持的配置格式: {path.suffix}")

            # 重建索引
            self.keyword_index = self._build_keyword_index()
            self.logger.info(f"已加载 {len(self.domains)} 个领域定义")

        except Exception as e:
            self.logger.error(f"加载领域配置失败: {e}")
            raise

    def add_domain(self, domain_name: str, keywords: List[str], subdomains: List[str] = None):
        """添加新领域

        Args:
            domain_name: 领域名称
            keywords: 关键词列表
            subdomains: 子领域列表（可选）
        """
        self.domains[domain_name] = {
            "keywords": keywords,
            "subdomains": subdomains or []
        }

        # 更新索引
        for keyword in keywords:
            self.keyword_index[keyword.lower()] = domain_name

        self.logger.info(f"已添加领域: {domain_name}")

    def get_domain_statistics(
        self,
        classifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取领域统计信息

        Args:
            classifications: 分类结果列表

        Returns:
            统计信息
        """
        domain_counts = {}
        for classification in classifications:
            primary = classification.get("primary_domain", "Unclassified")
            domain_counts[primary] = domain_counts.get(primary, 0) + 1

        total = len(classifications)

        return {
            "total_papers": total,
            "domain_distribution": domain_counts,
            "domain_percentages": {
                domain: (count / total * 100) if total > 0 else 0
                for domain, count in domain_counts.items()
            }
        }
