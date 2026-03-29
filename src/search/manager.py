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
文献搜索管理器

统一管理多源文献搜索。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..data.manager import DatabaseManager
from ..data.file_manager import FileManager
from ..data.cache import CacheSystem


class SearchManager:
    """文献搜索管理器

    协调多个文献数据库的搜索。

    用法：
    ```python
    manager = SearchManager()

    # 搜索文献
    results = await manager.search(
        keywords=["machine learning", "deep learning"],
        databases=["Elsevier", "arXiv"],
        max_results=100
    )

    # 下载文献
    await manager.download_papers(results)
    ```
    """

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        file_manager: FileManager = None,
        cache: CacheSystem = None
    ):
        """初始化搜索管理器

        Args:
            db_manager: 数据库管理器
            file_manager: 文件管理器
            cache: 缓存系统
        """
        self.db_manager = db_manager or DatabaseManager()
        self.file_manager = file_manager or FileManager()
        self.cache = cache or CacheSystem()

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 搜索器注册表
        self.searchers = {}

    def register_searcher(self, database_name: str, searcher: Any):
        """注册搜索器

        Args:
            database_name: 数据库名称
            searcher: 搜索器实例
        """
        self.searchers[database_name] = searcher
        self.logger.info(f"搜索器已注册: {database_name}")

    async def search(
        self,
        keywords: List[str],
        databases: List[str] = None,
        max_results: int = 100,
        year_range: tuple = None,
        require_all_keywords: bool = True,
        exclude_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索文献

        Args:
            keywords: 关键词列表
            databases: 数据库列表（默认：全部）
            max_results: 最大结果数
            year_range: 年份范围（例如：(2020, 2024)）
            require_all_keywords: 是否要求所有关键词都出现（默认 True）
            exclude_keywords: 排除关键词列表（例如：["vertical axis", "VAWT"]）

        Returns:
            文献列表
        """
        # 检查缓存
        cache_key = f"search:{','.join(keywords)}:{','.join(databases or [])}:{max_results}:{require_all_keywords}:{','.join(exclude_keywords or [])}"
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.info(f"从缓存返回搜索结果: {len(cached)} 篇")
            return cached

        # 确定要搜索的数据库
        databases = databases or list(self.searchers.keys())

        # 并行搜索
        tasks = []
        for db_name in databases:
            if db_name in self.searchers:
                searcher = self.searchers[db_name]
                # 传递新参数
                search_kwargs = {
                    "keywords": keywords,
                    "max_results": max_results // len(databases),
                    "year_range": year_range,
                }
                # 如果搜索器支持新参数，则传递
                if hasattr(searcher.search, '__code__'):
                    params = searcher.search.__code__.co_varnames
                    if 'require_all_keywords' in params:
                        search_kwargs['require_all_keywords'] = require_all_keywords
                    if 'exclude_keywords' in params:
                        search_kwargs['exclude_keywords'] = exclude_keywords

                tasks.append(searcher.search(**search_kwargs))

        # 执行搜索
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"搜索失败: {databases[i]} - {result}")
            else:
                all_papers.extend(result)

        # 去重（基于 DOI）
        unique_papers = self._deduplicate(all_papers)

        # 全局二次过滤（确保所有搜索器结果一致）
        if require_all_keywords or exclude_keywords:
            unique_papers = self._filter_papers(unique_papers, keywords, exclude_keywords)

        # 保存到缓存
        self.cache.set(cache_key, unique_papers, ttl=3600)  # 1 小时

        self.logger.info(f"搜索完成: {len(unique_papers)} 篇文献（去重前 {len(all_papers)} 篇）")
        return unique_papers

    def _filter_papers(
        self,
        papers: List[Dict[str, Any]],
        keywords: List[str],
        exclude_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """全局文献过滤

        Args:
            papers: 文献列表
            keywords: 关键词列表
            exclude_keywords: 排除关键词列表

        Returns:
            过滤后的列表
        """
        import re

        filtered = []
        for paper in papers:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()

            # 合并文本
            full_text = f"{title} {abstract}"

            # 检查关键词
            all_found = True
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower not in full_text:
                    # 尝试分词匹配
                    words = [w for w in re.split(r'[\s\-_]+', kw_lower) if len(w) > 2]
                    if words and not all(w in full_text for w in words):
                        all_found = False
                        break

            if not all_found:
                continue

            # 检查排除关键词
            if exclude_keywords:
                excluded = False
                for ex_kw in exclude_keywords:
                    if ex_kw.lower() in full_text:
                        excluded = True
                        break
                if excluded:
                    continue

            filtered.append(paper)

        return filtered

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
            # 优先使用 DOI，其次使用标题
            identifier = paper.get("doi") or paper.get("title")

            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(paper)

        return unique

    async def download_papers(
        self,
        papers: List[Dict[str, Any]],
        project_id: str,
        parallel: int = 5
    ) -> Dict[str, Any]:
        """批量下载文献

        Args:
            papers: 文献列表
            project_id: 项目 ID
            parallel: 并行下载数

        Returns:
            下载结果统计
        """
        self.logger.info(f"开始下载 {len(papers)} 篇文献")

        results = {
            "total": len(papers),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(parallel)

        async def download_with_limit(paper):
            async with semaphore:
                return await self._download_single_paper(paper, project_id)

        # 并行下载
        download_results = await asyncio.gather(
            *[download_with_limit(paper) for paper in papers],
            return_exceptions=True
        )

        # 统计结果
        for i, result in enumerate(download_results):
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({
                    "paper": papers[i].get("title", "Unknown"),
                    "error": str(result)
                })
            elif result == "success":
                results["success"] += 1
            elif result == "skipped":
                results["skipped"] += 1

        self.logger.info(f"下载完成: {results['success']} 成功, "
                        f"{results['failed']} 失败, "
                        f"{results['skipped']} 跳过")

        return results

    async def _download_single_paper(
        self,
        paper: Dict[str, Any],
        project_id: str
    ) -> str:
        """下载单篇文献

        Args:
            paper: 文献信息
            project_id: 项目 ID

        Returns:
            下载结果（success, skipped, failed）
        """
        paper_id = paper.get("doi") or paper.get("title")

        # 检查是否已下载
        existing = self.db_manager.query(
            "papers",
            {"doi": paper.get("doi")} if paper.get("doi") else {"title": paper.get("title")}
        )

        if existing:
            self.logger.debug(f"文献已存在: {paper_id}")
            return "skipped"

        # 下载 PDF（这里需要实现具体的下载逻辑）
        # 简化实现：假设已经下载成功
        pdf_path = None

        # 保存到数据库
        self.db_manager.insert("papers", {
            "title": paper.get("title"),
            "doi": paper.get("doi"),
            "authors": ", ".join(paper.get("authors", [])),
            "year": paper.get("year"),
            "journal": paper.get("journal"),
            "abstract": paper.get("abstract"),
            "pdf_path": str(pdf_path) if pdf_path else None
        })

        return "success"

    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取搜索历史

        Args:
            limit: 限制数量

        Returns:
            搜索历史列表
        """
        # 从数据库读取搜索历史
        return self.db_manager.query(
            "search_history",
            order_by="created_at DESC",
            limit=limit
        )

    def save_search_history(self, keywords: List[str], result_count: int):
        """保存搜索历史

        Args:
            keywords: 关键词
            result_count: 结果数量
        """
        self.db_manager.insert("search_history", {
            "keywords": ", ".join(keywords),
            "result_count": result_count,
            "created_at": datetime.now().isoformat()
        })
