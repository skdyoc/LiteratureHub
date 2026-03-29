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
文献分析管理器

协调 AI 深度分析、评分和分类。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..data.manager import DatabaseManager
from ..data.file_manager import FileManager
from .ai_analyzer import AIDeepAnalyzer
from .scoring import ScoringSystem
from .classifier import DomainClassifier


class AnalysisManager:
    """文献分析管理器

    统一管理文献的 AI 分析、评分和分类流程。

    使用示例：
    ```python
    manager = AnalysisManager()

    # 分析单篇文献
    result = await manager.analyze_paper(
        paper_id="2026_paper_001",
        analysis_types=["innovation", "motivation", "roadmap"]
    )

    # 批量分析
    results = await manager.batch_analyze(
        paper_ids=["2026_paper_001", "2026_paper_002"],
        max_concurrent=5
    )

    # 获取分析结果
    innovation = manager.get_analysis_result(
        paper_id="2026_paper_001",
        analysis_type="innovation"
    )
    ```
    """

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        file_manager: FileManager = None,
        ai_analyzer: AIDeepAnalyzer = None,
        scoring_system: ScoringSystem = None,
        domain_classifier: DomainClassifier = None
    ):
        """初始化分析管理器

        Args:
            db_manager: 数据库管理器
            file_manager: 文件管理器
            ai_analyzer: AI 分析器
            scoring_system: 评分系统
            domain_classifier: 领域分类器
        """
        self.db_manager = db_manager or DatabaseManager()
        self.file_manager = file_manager or FileManager()

        # 初始化分析组件
        self.ai_analyzer = ai_analyzer or AIDeepAnalyzer()
        self.scoring_system = scoring_system or ScoringSystem()
        self.domain_classifier = domain_classifier or DomainClassifier()

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def analyze_paper(
        self,
        paper_id: str,
        analysis_types: List[str] = None,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """分析单篇文献

        Args:
            paper_id: 文献 ID
            analysis_types: 分析类型列表（默认：全部）
                - "innovation": 创新点分析
                - "motivation": 研究动机分析
                - "roadmap": 技术路线分析
                - "mechanism": 机理解析
                - "impact": 影响评估
                - "history": 历史脉络
            force_reanalyze: 是否强制重新分析

        Returns:
            分析结果字典
        """
        self.logger.info(f"开始分析文献: {paper_id}")

        # 检查是否已分析
        if not force_reanalyze:
            existing = self._get_existing_analysis(paper_id, analysis_types)
            if existing:
                self.logger.info(f"文献已分析，跳过: {paper_id}")
                return existing

        # 读取文献内容
        paper_content = self._load_paper_content(paper_id)
        if not paper_content:
            raise ValueError(f"无法加载文献内容: {paper_id}")

        # 确定分析类型
        all_types = ["innovation", "motivation", "roadmap", "mechanism", "impact", "history"]
        analysis_types = analysis_types or all_types

        results = {
            "paper_id": paper_id,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_results": {}
        }

        # 执行各类分析
        for analysis_type in analysis_types:
            try:
                result = await self.ai_analyzer.analyze(
                    paper_content=paper_content,
                    analysis_type=analysis_type
                )
                results["analysis_results"][analysis_type] = result

                # 保存到数据库
                self._save_analysis_result(paper_id, analysis_type, result)

            except Exception as e:
                self.logger.error(f"分析失败 [{analysis_type}]: {e}")
                results["analysis_results"][analysis_type] = {
                    "error": str(e),
                    "status": "failed"
                }

        # 计算综合评分
        overall_score = self.scoring_system.calculate_overall_score(
            paper_id=paper_id,
            analysis_results=results["analysis_results"]
        )
        results["overall_score"] = overall_score

        # 领域分类
        domain_classification = await self.domain_classifier.classify(
            paper_content=paper_content,
            analysis_results=results["analysis_results"]
        )
        results["domain_classification"] = domain_classification

        # 更新数据库
        self._update_paper_metadata(paper_id, overall_score, domain_classification)

        self.logger.info(f"文献分析完成: {paper_id}, 综合评分: {overall_score}")
        return results

    async def batch_analyze(
        self,
        paper_ids: List[str],
        analysis_types: List[str] = None,
        max_concurrent: int = 5,
        skip_completed: bool = True
    ) -> Dict[str, Any]:
        """批量分析文献

        Args:
            paper_ids: 文献 ID 列表
            analysis_types: 分析类型列表
            max_concurrent: 最大并发数
            skip_completed: 是否跳过已完成的

        Returns:
            批量分析结果
        """
        self.logger.info(f"开始批量分析: {len(paper_ids)} 篇文献")

        results = {
            "total": len(paper_ids),
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "paper_results": {}
        }

        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_limit(paper_id: str):
            async with semaphore:
                try:
                    # 检查是否已完成
                    if skip_completed:
                        existing = self._get_existing_analysis(paper_id, analysis_types)
                        if existing:
                            results["skipped"] += 1
                            results["paper_results"][paper_id] = {
                                "status": "skipped",
                                "message": "已分析"
                            }
                            return

                    # 执行分析
                    result = await self.analyze_paper(paper_id, analysis_types)
                    results["success"] += 1
                    results["paper_results"][paper_id] = {
                        "status": "success",
                        "result": result
                    }

                except Exception as e:
                    results["failed"] += 1
                    results["paper_results"][paper_id] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    self.logger.error(f"批量分析失败 [{paper_id}]: {e}")

        # 并行执行
        tasks = [analyze_with_limit(paper_id) for paper_id in paper_ids]
        await asyncio.gather(*tasks)

        self.logger.info(f"批量分析完成: {results['success']} 成功, "
                        f"{results['skipped']} 跳过, {results['failed']} 失败")
        return results

    def get_analysis_result(
        self,
        paper_id: str,
        analysis_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """获取分析结果

        Args:
            paper_id: 文献 ID
            analysis_type: 分析类型（可选，不指定则返回全部）

        Returns:
            分析结果
        """
        if analysis_type:
            # 查询特定类型
            results = self.db_manager.query(
                "analysis_results",
                {"paper_id": paper_id, "analysis_type": analysis_type}
            )
            return results[0] if results else None
        else:
            # 查询全部
            results = self.db_manager.query(
                "analysis_results",
                {"paper_id": paper_id}
            )

            # 按类型组织
            organized = {}
            for result in results:
                organized[result["analysis_type"]] = result

            return organized

    def _load_paper_content(self, paper_id: str) -> Optional[str]:
        """加载文献内容

        Args:
            paper_id: 文献 ID

        Returns:
            文献内容（Markdown 格式）
        """
        # 查询文献信息
        papers = self.db_manager.query("papers", {"id": paper_id})
        if not papers:
            return None

        paper = papers[0]

        # 读取 Markdown 文件
        if paper.get("markdown_path"):
            md_path = Path(paper["markdown_path"])
            if md_path.exists():
                with open(md_path, 'r', encoding='utf-8') as f:
                    return f.read()

        # 尝试默认路径
        default_path = self.file_manager.base_path / paper.get("project_id", "default") / "markdown" / f"{paper_id}.md"
        if default_path.exists():
            with open(default_path, 'r', encoding='utf-8') as f:
                return f.read()

        return None

    def _get_existing_analysis(
        self,
        paper_id: str,
        analysis_types: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取已存在的分析结果

        Args:
            paper_id: 文献 ID
            analysis_types: 分析类型列表

        Returns:
            已存在的分析结果（如果全部存在）
        """
        all_types = ["innovation", "motivation", "roadmap", "mechanism", "impact", "history"]
        types_to_check = analysis_types or all_types

        existing = {}
        for analysis_type in types_to_check:
            result = self.get_analysis_result(paper_id, analysis_type)
            if not result:
                return None
            existing[analysis_type] = result

        return existing

    def _save_analysis_result(
        self,
        paper_id: str,
        analysis_type: str,
        result: Dict[str, Any]
    ):
        """保存分析结果

        Args:
            paper_id: 文献 ID
            analysis_type: 分析类型
            result: 分析结果
        """
        self.db_manager.insert("analysis_results", {
            "paper_id": paper_id,
            "analysis_type": analysis_type,
            "result_data": result,
            "analyzed_at": datetime.now().isoformat()
        })

    def _update_paper_metadata(
        self,
        paper_id: str,
        overall_score: float,
        domain_classification: Dict[str, Any]
    ):
        """更新文献元数据

        Args:
            paper_id: 文献 ID
            overall_score: 综合评分
            domain_classification: 领域分类
        """
        self.db_manager.update(
            "papers",
            {
                "overall_score": overall_score,
                "primary_domain": domain_classification.get("primary_domain"),
                "secondary_domains": ",".join(domain_classification.get("secondary_domains", [])),
                "classification_confidence": domain_classification.get("confidence", 0.0)
            },
            {"id": paper_id}
        )

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息

        Returns:
            统计信息
        """
        # 查询所有文献
        all_papers = self.db_manager.query("papers")

        # 查询已分析的文献
        analyzed_papers = self.db_manager.query(
            "papers",
            {"overall_score__gt": 0}
        )

        # 按领域统计
        domain_stats = {}
        for paper in analyzed_papers:
            domain = paper.get("primary_domain", "未分类")
            domain_stats[domain] = domain_stats.get(domain, 0) + 1

        # 按分析类型统计
        analysis_stats = {}
        for analysis_type in ["innovation", "motivation", "roadmap", "mechanism", "impact", "history"]:
            count = len(self.db_manager.query("analysis_results", {"analysis_type": analysis_type}))
            analysis_stats[analysis_type] = count

        return {
            "total_papers": len(all_papers),
            "analyzed_papers": len(analyzed_papers),
            "analysis_progress": len(analyzed_papers) / len(all_papers) if all_papers else 0,
            "domain_distribution": domain_stats,
            "analysis_type_distribution": analysis_stats,
            "average_score": sum(p.get("overall_score", 0) for p in analyzed_papers) / len(analyzed_papers) if analyzed_papers else 0
        }
