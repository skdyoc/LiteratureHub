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
多源搜索器

统一搜索多个学术数据库。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .elsevier_searcher import ElsevierSearcher
from .arxiv_searcher import ArxivSearcher
from .ieee_searcher import IEEESearcher
from .springer_searcher import SpringerSearcher


class MultiSourceSearcher:
    """多源搜索器

    统一搜索多个学术数据库，支持并行搜索和结果合并。

    功能：
    - 多数据库并行搜索
    - 自动去重
    - 结果排序和过滤
    - 搜索历史记录
    - 错误重试机制
    """

    SUPPORTED_DATABASES = {
        "elsevier": {
            "name": "Elsevier Scopus",
            "requires_api_key": True,
            "searcher_class": ElsevierSearcher
        },
        "arxiv": {
            "name": "arXiv",
            "requires_api_key": False,
            "searcher_class": ArxivSearcher
        },
        "ieee": {
            "name": "IEEE Xplore",
            "requires_api_key": True,
            "searcher_class": IEEESearcher
        },
        "springer": {
            "name": "Springer Nature",
            "requires_api_key": True,
            "searcher_class": SpringerSearcher
        }
    }

    def __init__(self, cache_dir: str = "data/cache"):
        """初始化多源搜索器

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.searchers: Dict[str, Any] = {}
        self.search_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def configure_searcher(self, database: str, **kwargs):
        """配置搜索器

        Args:
            database: 数据库名称
            **kwargs: 配置参数
        """
        if database not in self.SUPPORTED_DATABASES:
            raise ValueError(f"不支持的数据库: {database}")

        db_info = self.SUPPORTED_DATABASES[database]
        searcher_class = db_info["searcher_class"]

        # 创建搜索器实例
        self.searchers[database] = searcher_class(**kwargs)

        self.logger.info(f"已配置搜索器: {database}")

    async def search(
        self,
        keywords: List[str],
        databases: List[str] = None,
        max_results: int = 100,
        year_range: tuple = None,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索文献

        Args:
            keywords: 关键词列表
            databases: 数据库列表（None表示所有可用数据库）
            max_results: 每个数据库最大结果数
            year_range: 年份范围 (start_year, end_year)
            parallel: 是否并行搜索

        Returns:
            合并后的文献列表
        """
        # 使用所有可用数据库
        if databases is None:
            databases = list(self.searchers.keys())

        # 验证数据库
        for db in databases:
            if db not in self.searchers:
                self.logger.warning(f"数据库 {db} 未配置，跳过")
                databases.remove(db)

        if not databases:
            self.logger.warning("没有可用的搜索器")
            return []

        self.logger.info(f"开始搜索: {keywords}")
        self.logger.info(f"数据库: {databases}")
        self.logger.info(f"并行模式: {parallel}")

        start_time = datetime.now()

        # 执行搜索
        if parallel:
            # 并行搜索
            tasks = [
                self._search_single(db, keywords, max_results, year_range)
                for db in databases
            ]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 串行搜索
            results_list = []
            for db in databases:
                result = await self._search_single(db, keywords, max_results, year_range)
                results_list.append(result)

        # 合并结果
        all_papers = []
        for db, result in zip(databases, results_list):
            if isinstance(result, Exception):
                self.logger.error(f"搜索 {db} 失败: {result}")
            else:
                all_papers.extend(result)

        # 去重
        unique_papers = self._deduplicate(all_papers)

        # 排序（按年份降序）
        unique_papers.sort(key=lambda p: p.get("year", 0), reverse=True)

        # 记录搜索历史
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.search_history.append({
            "keywords": keywords,
            "databases": databases,
            "max_results": max_results,
            "year_range": year_range,
            "result_count": len(unique_papers),
            "duration": duration,
            "timestamp": start_time
        })

        self.logger.info(f"搜索完成: {len(unique_papers)} 篇文献, 耗时 {duration:.2f} 秒")

        return unique_papers

    async def _search_single(
        self,
        database: str,
        keywords: List[str],
        max_results: int,
        year_range: tuple
    ) -> List[Dict[str, Any]]:
        """搜索单个数据库

        Args:
            database: 数据库名称
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围

        Returns:
            文献列表
        """
        searcher = self.searchers[database]

        try:
            papers = await searcher.search(
                keywords=keywords,
                max_results=max_results,
                year_range=year_range
            )

            self.logger.info(f"{database}: 找到 {len(papers)} 篇文献")
            return papers

        except Exception as e:
            self.logger.error(f"{database} 搜索失败: {e}")
            return []

    def _deduplicate(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重

        Args:
            papers: 文献列表

        Returns:
            去重后的文献列表
        """
        seen = set()
        unique = []

        for paper in papers:
            # 使用 DOI 或标题作为唯一标识
            identifier = paper.get("doi") or paper.get("title", "").lower()

            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(paper)

        return unique

    def get_available_databases(self) -> List[Dict[str, Any]]:
        """获取可用数据库列表

        Returns:
            数据库信息列表
        """
        return [
            {
                "id": db_id,
                "name": info["name"],
                "requires_api_key": info["requires_api_key"],
                "configured": db_id in self.searchers
            }
            for db_id, info in self.SUPPORTED_DATABASES.items()
        ]

    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取搜索历史

        Args:
            limit: 最大返回数量

        Returns:
            搜索历史列表
        """
        return self.search_history[-limit:]

    def clear_history(self):
        """清空搜索历史"""
        self.search_history.clear()
        self.logger.info("已清空搜索历史")
