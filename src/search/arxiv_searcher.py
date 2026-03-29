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
arXiv 搜索器

使用 arXiv API 搜索学术文献。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
import xml.etree.ElementTree as ET

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False


class ArxivSearcher:
    """arXiv 文献搜索器

    使用 arXiv API 搜索学术预印本。

    使用示例：
    ```python
    searcher = ArxivSearcher()

    # 搜索文献
    results = await searcher.search(
        keywords=["machine learning", "deep learning"],
        max_results=100,
        year_range=(2023, 2024)
    )

    # 获取文献详情
    details = await searcher.get_paper_details("2301.12345")
    ```
    """

    # arXiv 分类
    CATEGORIES = {
        "cs": "Computer Science",
        "physics": "Physics",
        "math": "Mathematics",
        "stat": "Statistics",
        "eess": "Electrical Engineering and Systems Science",
        "econ": "Economics",
        "q-bio": "Quantitative Biology",
        "q-fin": "Quantitative Finance"
    }

    def __init__(self):
        """初始化 arXiv 搜索器"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 检查依赖
        if not ARXIV_AVAILABLE:
            self.logger.warning("arxiv 库未安装，将使用 REST API")

        # API 基础 URL
        self.base_url = "http://export.arxiv.org/api/query"

    async def search(
        self,
        keywords: List[str],
        max_results: int = 100,
        year_range: tuple = None,
        categories: List[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索文献

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围
            categories: 分类列表（例如：["cs.AI", "cs.LG"]）

        Returns:
            文献列表
        """
        self.logger.info(f"开始 arXiv 搜索: {keywords}")

        try:
            if ARXIV_AVAILABLE:
                results = await self._search_with_arxiv_lib(
                    keywords, max_results, year_range, categories
                )
            else:
                results = await self._search_with_rest_api(
                    keywords, max_results, year_range, categories
                )

            self.logger.info(f"arXiv 搜索完成: {len(results)} 篇文献")
            return results

        except Exception as e:
            self.logger.error(f"arXiv 搜索失败: {e}")
            return []

    async def _search_with_arxiv_lib(
        self,
        keywords: List[str],
        max_results: int,
        year_range: tuple,
        categories: List[str]
    ) -> List[Dict[str, Any]]:
        """使用 arxiv 库搜索

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围
            categories: 分类列表

        Returns:
            文献列表
        """
        loop = asyncio.get_event_loop()

        def sync_search():
            try:
                # 构建查询
                query = " AND ".join(f'all:"{kw}"' for kw in keywords)

                if categories:
                    cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
                    query = f"({query}) AND ({cat_query})"

                # 执行搜索
                search = arxiv.Search(
                    query=query,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                results = []
                for result in search.results():
                    # 过滤年份
                    if year_range:
                        year = result.published.year
                        if not (year_range[0] <= year <= year_range[1]):
                            continue

                    paper = {
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "year": result.published.year,
                        "journal": "arXiv",
                        "doi": result.doi,
                        "arxiv_id": result.entry_id.split("/")[-1],
                        "abstract": result.summary,
                        "keywords": result.categories,
                        "citations": 0,  # arXiv 没有引用数据
                        "source": "arXiv",
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "retrieved_at": datetime.now().isoformat()
                    }
                    results.append(paper)

                return results

            except Exception as e:
                self.logger.error(f"arxiv 库搜索失败: {e}")
                return []

        results = await loop.run_in_executor(None, sync_search)
        return results

    async def _search_with_rest_api(
        self,
        keywords: List[str],
        max_results: int,
        year_range: tuple,
        categories: List[str]
    ) -> List[Dict[str, Any]]:
        """使用 REST API 搜索

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围
            categories: 分类列表

        Returns:
            文献列表
        """
        # 构建查询
        query = "+AND+".join(f'all:"{kw}"' for kw in keywords)

        if categories:
            cat_query = "+OR+".join(f"cat:{cat}" for cat in categories)
            query = f"({query})+AND+({cat_query})"

        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"arXiv API 请求失败: {response.status}")
                    return []

                xml_data = await response.text()

        # 解析 XML
        results = self._parse_arxiv_response(xml_data, year_range)

        return results

    def _parse_arxiv_response(
        self,
        xml_data: str,
        year_range: tuple
    ) -> List[Dict[str, Any]]:
        """解析 arXiv API 响应

        Args:
            xml_data: XML 数据
            year_range: 年份范围

        Returns:
            文献列表
        """
        results = []

        try:
            root = ET.fromstring(xml_data)

            # 命名空间
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom"
            }

            for entry in root.findall("atom:entry", ns):
                # 提取年份
                published = entry.find("atom:published", ns)
                if published is not None:
                    year = int(published.text[:4])

                    # 过滤年份
                    if year_range:
                        if not (year_range[0] <= year <= year_range[1]):
                            continue
                else:
                    year = None

                # 提取标题
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text if title_elem is not None else ""

                # 提取作者
                authors = []
                for author in entry.findall("atom:author", ns):
                    name_elem = author.find("atom:name", ns)
                    if name_elem is not None:
                        authors.append(name_elem.text)

                # 提取摘要
                summary_elem = entry.find("atom:summary", ns)
                abstract = summary_elem.text.strip() if summary_elem is not None else ""

                # 提取 DOI
                doi_elem = entry.find("arxiv:doi", ns)
                doi = doi_elem.text if doi_elem is not None else None

                # 提取 arXiv ID
                id_elem = entry.find("atom:id", ns)
                arxiv_id = id_elem.text.split("/")[-1] if id_elem is not None else ""

                # 提取分类
                categories = []
                for cat in entry.findall("atom:category", ns):
                    term = cat.get("term")
                    if term:
                        categories.append(term)

                # 提取 PDF URL
                pdf_url = None
                for link in entry.findall("atom:link", ns):
                    if link.get("type") == "application/pdf":
                        pdf_url = link.get("href")
                        break

                paper = {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "journal": "arXiv",
                    "doi": doi,
                    "arxiv_id": arxiv_id,
                    "abstract": abstract,
                    "keywords": categories,
                    "citations": 0,
                    "source": "arXiv",
                    "url": id_elem.text if id_elem is not None else "",
                    "pdf_url": pdf_url,
                    "retrieved_at": datetime.now().isoformat()
                }

                results.append(paper)

        except Exception as e:
            self.logger.error(f"解析 arXiv 响应失败: {e}")

        return results

    async def get_paper_details(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """获取文献详情

        Args:
            arxiv_id: arXiv ID

        Returns:
            文献详情
        """
        if ARXIV_AVAILABLE:
            loop = asyncio.get_event_loop()

            def sync_get():
                try:
                    search = arxiv.Search(id_list=[arxiv_id])
                    result = next(search.results())

                    return {
                        "arxiv_id": arxiv_id,
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "year": result.published.year,
                        "journal": "arXiv",
                        "doi": result.doi,
                        "abstract": result.summary,
                        "keywords": result.categories,
                        "source": "arXiv",
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "retrieved_at": datetime.now().isoformat()
                    }

                except Exception as e:
                    self.logger.error(f"获取 arXiv 文献详情失败: {e}")
                    return None

            return await loop.run_in_executor(None, sync_get)

        else:
            # 使用 REST API
            params = {"id_list": arxiv_id}

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        return None

                    xml_data = await response.text()

            results = self._parse_arxiv_response(xml_data, None)
            return results[0] if results else None

    def get_category_name(self, category_code: str) -> str:
        """获取分类名称

        Args:
            category_code: 分类代码（例如："cs.AI"）

        Returns:
            分类名称
        """
        # 提取主分类
        main_cat = category_code.split(".")[0]
        return self.CATEGORIES.get(main_cat, category_code)
