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
IEEE 搜索器

使用 IEEE Xplore API 搜索学术文献。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp


class IEEESearcher:
    """IEEE 文献搜索器

    使用 IEEE Xplore API 搜索学术文献。

    使用示例：
    ```python
    searcher = IEEESearcher(api_key="your_api_key")

    # 搜索文献
    results = await searcher.search(
        keywords=["deep learning", "neural networks"],
        max_results=100,
        year_range=(2020, 2024)
    )

    # 获取文献详情
    details = await searcher.get_paper_details("10.1109/5.123456")
    ```
    """

    def __init__(self, api_key: str = None):
        """初始化 IEEE 搜索器

        Args:
            api_key: IEEE API 密钥
        """
        self.api_key = api_key
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # API 基础 URL
        self.base_url = "https://ieeexploreapi.ieee.org/api/v1"

    async def search(
        self,
        keywords: List[str],
        max_results: int = 100,
        year_range: tuple = None
    ) -> List[Dict[str, Any]]:
        """搜索文献

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围

        Returns:
            文献列表
        """
        self.logger.info(f"开始 IEEE 搜索: {keywords}")

        # 构建查询
        query = self._build_query(keywords, year_range)

        try:
            results = await self._search_with_api(query, max_results)

            self.logger.info(f"IEEE 搜索完成: {len(results)} 篇文献")
            return results

        except Exception as e:
            self.logger.error(f"IEEE 搜索失败: {e}")
            return []

    def _build_query(self, keywords: List[str], year_range: tuple = None) -> str:
        """构建查询字符串

        Args:
            keywords: 关键词列表
            year_range: 年份范围

        Returns:
            查询字符串
        """
        # 关键词查询
        keyword_query = " ".join(keywords)

        if year_range:
            start_year, end_year = year_range
            query = f'("{keyword_query}") AND py:{start_year}-{end_year}'
        else:
            query = f'"{keyword_query}"'

        return query

    async def _search_with_api(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """使用 API 搜索

        Args:
            query: 查询字符串
            max_results: 最大结果数

        Returns:
            文献列表
        """
        if not self.api_key:
            self.logger.warning("API 密钥未配置，返回空结果")
            return []

        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }

        params = {
            "querytext": query,
            "max_records": max_results
        }

        url = f"{self.base_url}/search"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"IEEE API 请求失败: {response.status}")
                    return []

                data = await response.json()

        # 解析结果
        results = []
        articles = data.get("articles", [])

        for article in articles:
            paper = {
                "title": article.get("title"),
                "authors": article.get("authors", []).split("; ") if article.get("authors") else [],
                "year": article.get("publication_year"),
                "journal": article.get("publication_title"),
                "doi": article.get("doi"),
                "abstract": article.get("abstract"),
                "keywords": article.get("keywords", []),
                "citations": article.get("citing_paper_count", 0),
                "source": "IEEE",
                "url": article.get("html_url"),
                "pdf_url": article.get("pdf_url"),
                "retrieved_at": datetime.now().isoformat()
            }
            results.append(paper)

        return results

    async def get_paper_details(self, doi: str) -> Optional[Dict[str, Any]]:
        """获取文献详情

        Args:
            doi: DOI

        Returns:
            文献详情
        """
        if not self.api_key:
            self.logger.error("API 密钥未配置")
            return None

        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }

        url = f"{self.base_url}/article/{doi}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"获取文献详情失败: {response.status}")
                    return None

                data = await response.json()

        article = data.get("article", {})

        return {
            "doi": doi,
            "title": article.get("title"),
            "abstract": article.get("abstract"),
            "authors": article.get("authors", []).split("; ") if article.get("authors") else [],
            "year": article.get("publication_year"),
            "journal": article.get("publication_title"),
            "keywords": article.get("keywords", []),
            "source": "IEEE",
            "retrieved_at": datetime.now().isoformat()
        }

    def validate_api_key(self) -> bool:
        """验证 API 密钥

        Returns:
            是否有效
        """
        if not self.api_key:
            return False

        # 实现实际的验证逻辑
        try:
            # 发送测试请求验证 API 密钥
            test_url = f"{self.base_url}/search"
            params = {
                "apikey": self.api_key,
                "query": "test",
                "max_records": 1
            }

            response = requests.get(test_url, params=params, timeout=10)

            # 200 表示密钥有效，401/403 表示无效
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"验证 API 密钥失败: {e}")
            return False
