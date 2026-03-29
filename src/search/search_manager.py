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
搜索管理器

统一管理多个数据库搜索器。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .elsevier_searcher import ElsevierSearcher
from .arxiv_searcher import ArxivSearcher
from .ieee_searcher import IEEESearcher
from .springer_searcher import SpringerSearcher


class SearchManager:
    """搜索管理器

    统一管理多个数据库搜索器，支持并行搜索和结果合并。

    用法：
    ```python
    manager = SearchManager()

    # 配置搜索器
    manager.configure_searcher("elsevier", api_key="your_key")
    manager.configure_searcher("arxiv")  # arXiv 不需要 API key

    # 搜索文献
    results = await manager.search(
        keywords=["deep learning", "neural networks"],
        databases=["elsevier", "arxiv"],
        max_results=100
    )

    # 导出结果
    manager.export_results(results, "output.json")
    ```
    """

    # 支持的数据库
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
        """初始化搜索管理器

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 搜索器注册表
        self.searchers: Dict[str, Any] = {}

        # 搜索历史
        self.search_history: List[Dict[str, Any]] = []

    def configure_searcher(
        self,
        database: str,
        api_key: str = None,
        **kwargs
    ):
        """配置搜索器

        Args:
            database: 数据库名称
            api_key: API 密钥
            **kwargs: 其他配置参数
        """
        if database not in self.SUPPORTED_DATABASES:
            raise ValueError(f"不支持的数据库: {database}")

        db_config = self.SUPPORTED_DATABASES[database]

        # 检查 API 密钥
        if db_config["requires_api_key"] and not api_key:
            self.logger.warning(f"{db_config['name']} 需要 API 密钥")

        # 创建搜索器实例
        searcher_class = db_config["searcher_class"]
        searcher = searcher_class(api_key=api_key, **kwargs)

        self.searchers[database] = searcher
        self.logger.info(f"搜索器已配置: {database}")

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
            databases: 数据库列表（默认：全部已配置的）
            max_results: 每个数据库的最大结果数
            year_range: 年份范围
            parallel: 是否并行搜索

        Returns:
            合并后的文献列表
        """
        self.logger.info(f"开始搜索: {keywords}")

        # 确定要搜索的数据库
        if databases is None:
            databases = list(self.searchers.keys())

        # 验证数据库是否已配置
        for db in databases:
            if db not in self.searchers:
                self.logger.warning(f"数据库未配置，跳过: {db}")
                databases.remove(db)

        if not databases:
            self.logger.error("没有可用的搜索器")
            return []

        # 执行搜索
        if parallel:
            # 并行搜索
            tasks = []
            for db in databases:
                searcher = self.searchers[db]
                tasks.append(
                    searcher.search(keywords, max_results, year_range)
                )

            results_list = await asyncio.gather(*tasks, return_exceptions=True)

        else:
            # 串行搜索
            results_list = []
            for db in databases:
                searcher = self.searchers[db]
                try:
                    results = await searcher.search(keywords, max_results, year_range)
                    results_list.append(results)
                except Exception as e:
                    self.logger.error(f"搜索失败 [{db}]: {e}")
                    results_list.append([])

        # 合并结果
        all_papers = []
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                self.logger.error(f"搜索失败 [{databases[i]}]: {results}")
            else:
                all_papers.extend(results)

        # 去重
        unique_papers = self._deduplicate(all_papers)

        # 记录搜索历史
        self.search_history.append({
            "keywords": keywords,
            "databases": databases,
            "total_results": len(all_papers),
            "unique_results": len(unique_papers),
            "searched_at": datetime.now().isoformat()
        })

        self.logger.info(
            f"搜索完成: {len(unique_papers)} 篇唯一文献 "
            f"(去重前 {len(all_papers)} 篇)"
        )

        return unique_papers

    def _deduplicate(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重

        Args:
            papers: 文献列表

        Returns:
            去重后的列表
        """
        seen = set()
        unique = []

        for paper in papers:
            # 使用 DOI 或标题作为标识符
            identifier = paper.get("doi") or paper.get("title", "").lower()

            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(paper)

        return unique

    def export_results(
        self,
        papers: List[Dict[str, Any]],
        output_path: str,
        format: str = "json"
    ):
        """导出搜索结果

        Args:
            papers: 文献列表
            output_path: 输出路径
            format: 输出格式（json, csv, bibtex）
        """
        import json
        import csv

        output_file = Path(output_path)

        if format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)

        elif format == "csv":
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if papers:
                    fieldnames = papers[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(papers)

        elif format == "bibtex":
            with open(output_file, 'w', encoding='utf-8') as f:
                for paper in papers:
                    bibtex = self._to_bibtex(paper)
                    f.write(bibtex + "\n\n")

        else:
            raise ValueError(f"不支持的格式: {format}")

        self.logger.info(f"结果已导出: {output_file}")

    def _to_bibtex(self, paper: Dict[str, Any]) -> str:
        """转换为 BibTeX 格式

        Args:
            paper: 文献信息

        Returns:
            BibTeX 字符串
        """
        # 生成引用键
        cite_key = paper.get("doi", "").replace("/", "_") or \
                   f"paper_{hash(paper.get('title', ''))}"

        authors = " and ".join(paper.get("authors", []))

        bibtex = f"@article{{{cite_key},\n"
        bibtex += f"  title = {{{paper.get('title', '')}}},\n"
        bibtex += f"  author = {{{authors}}},\n"

        if paper.get("year"):
            bibtex += f"  year = {{{paper.get('year')}}},\n"

        if paper.get("journal"):
            bibtex += f"  journal = {{{paper.get('journal')}}},\n"

        if paper.get("doi"):
            bibtex += f"  doi = {{{paper.get('doi')}}},\n"

        if paper.get("url"):
            bibtex += f"  url = {{{paper.get('url')}}},\n"

        bibtex += "}"

        return bibtex

    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取搜索历史

        Args:
            limit: 限制数量

        Returns:
            搜索历史列表
        """
        return self.search_history[-limit:]

    def get_available_databases(self) -> List[Dict[str, Any]]:
        """获取可用的数据库列表

        Returns:
            数据库信息列表
        """
        databases = []

        for db_id, db_config in self.SUPPORTED_DATABASES.items():
            databases.append({
                "id": db_id,
                "name": db_config["name"],
                "requires_api_key": db_config["requires_api_key"],
                "configured": db_id in self.searchers
            })

        return databases

    def validate_api_keys(self) -> Dict[str, bool]:
        """验证所有 API 密钥

        Returns:
            验证结果字典
        """
        results = {}

        for db_id, searcher in self.searchers.items():
            try:
                if hasattr(searcher, "validate_api_key"):
                    results[db_id] = searcher.validate_api_key()
                else:
                    results[db_id] = True  # 不需要 API key 的数据库
            except Exception as e:
                self.logger.error(f"验证 API 密钥失败 [{db_id}]: {e}")
                results[db_id] = False

        return results

    def clear_cache(self):
        """清空缓存"""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("缓存已清空")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "configured_databases": len(self.searchers),
            "supported_databases": len(self.SUPPORTED_DATABASES),
            "total_searches": len(self.search_history),
            "cache_size": sum(
                f.stat().st_size
                for f in self.cache_dir.rglob("*")
                if f.is_file()
            ) if self.cache_dir.exists() else 0
        }
