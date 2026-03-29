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
Elsevier 搜索器

使用 Elsevier API 搜索学术文献。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
import requests

try:
    from pybliometrics.scopus import ScopusSearch
    PYBLIOMETRICS_AVAILABLE = True
except ImportError:
    PYBLIOMETRICS_AVAILABLE = False


class ElsevierSearcher:
    """Elsevier 文献搜索器

    使用 Elsevier Scopus API 搜索学术文献。

    使用示例：
    ```python
    searcher = ElsevierSearcher(api_key="your_api_key")

    # 搜索文献
    results = await searcher.search(
        keywords=["machine learning", "wind energy"],
        max_results=100,
        year_range=(2020, 2024)
    )

    # 获取文献详情
    details = await searcher.get_paper_details("10.1016/j.energy.2023.123456")
    ```
    """

    def __init__(self, api_key: str = None, inst_token: str = None):
        """初始化搜索器

        Args:
            api_key: Elsevier API 密钥
            inst_token: 机构令牌（可选）
        """
        self.api_key = api_key
        self.inst_token = inst_token
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 检查依赖
        if not PYBLIOMETRICS_AVAILABLE:
            self.logger.warning("pybliometrics 库未安装，部分功能将不可用")

        # API 基础 URL
        self.base_url = "https://api.elsevier.com/content"

    # API 限制：单次查询最多返回20篇结果（取决于API密钥类型）
    MAX_RESULTS_PER_QUERY = 20

    async def search(
        self,
        keywords: List[str],
        max_results: int = 100,
        year_range: tuple = None,
        require_all_keywords: bool = True,
        exclude_keywords: List[str] = None,
        match_mode: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """搜索文献

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围（例如：(2020, 2024)）
            require_all_keywords: 是否要求所有关键词都出现（默认 True）
            exclude_keywords: 排除关键词列表（例如：["vertical axis", "VAWT"]）
            match_mode: 匹配模式 {"fields": ["title", "keywords", "abstract"], "combination": "all" | "any"}

        Returns:
            文献列表
        """
        self.logger.info(f"开始 Elsevier 搜索: {keywords}")
        self.logger.info(f"要求所有关键词: {require_all_keywords}, 排除: {exclude_keywords}")
        if match_mode:
            self.logger.info(f"匹配模式: fields={match_mode.get('fields')}, combination={match_mode.get('combination')}")

        # 对关键词进行转义（与查询时保持一致）
        escaped_keywords = [self._escape_query_term(kw) for kw in keywords]
        escaped_exclude = [self._escape_query_term(kw) for kw in exclude_keywords] if exclude_keywords else []

        # 构建查询字符串
        query = self._build_query(keywords, year_range, require_all_keywords, exclude_keywords, match_mode)
        self.logger.info(f"构建的查询字符串: {query}")

        try:
            # 优先使用 REST API（更稳定）
            if self.api_key:
                self.logger.info(f"Elsevier API 查询字符串: {query} (max_results={max_results})")
                results = await self._search_with_rest_api(query, max_results)
                self.logger.info(f"API 返回原始结果: {len(results)} 篇")
            else:
                self.logger.error("Elsevier API 密钥未配置")
                return []

            # 二次过滤：使用转义后的关键词确保结果真正包含关键词
            # 如果没有指定 match_mode，使用默认的宽松模式
            filter_match_mode = match_mode or {"fields": ["title", "keywords", "abstract"], "combination": "any"}
            results = self._filter_results(results, escaped_keywords, escaped_exclude, filter_match_mode)

            self.logger.info(f"Elsevier 搜索完成: {len(results)} 篇文献（过滤后）")
            return results

        except Exception as e:
            self.logger.error(f"Elsevier 搜索失败: {e}")
            return []

    def _escape_query_term(self, term: str) -> str:
        """转义查询字符串中的特殊字符

        Scopus API 特殊字符: -, +, &, |, !, (, ), {, }, [, ], ^, ", ~, *, ?, :, \

        Args:
            term: 原始查询词

        Returns:
            转义后的查询词
        """
        # 对于连字符，用空格替换（更安全）
        # 其他特殊字符用反斜杠转义
        term = term.replace("-", " ")
        return term

    def _build_query(
        self,
        keywords: List[str],
        year_range: tuple = None,
        require_all_keywords: bool = True,
        exclude_keywords: List[str] = None,
        match_mode: Dict[str, Any] = None
    ) -> str:
        """构建查询字符串

        Args:
            keywords: 关键词列表
            year_range: 年份范围
            require_all_keywords: 是否要求所有关键词都出现
            exclude_keywords: 排除关键词列表
            match_mode: 匹配模式 {"fields": ["title", "keywords", "abstract"], "combination": "all" | "any"}

        Returns:
            查询字符串

        注意：Scopus API 只支持以下字段语法：
        - TITLE() - 只标题
        - ABS() - 只摘要
        - KEY() - 只关键词
        - TITLE-ABS-KEY() - 全部字段
        不支持部分组合（如 TITLE-ABS, TITLE-KEY）
        """
        # 确定搜索字段
        if match_mode and match_mode.get("fields"):
            fields = match_mode["fields"]
        else:
            fields = ["title", "keywords", "abstract"]

        # Scopus API 字段语法限制：
        # 只支持：TITLE(), ABS(), KEY(), TITLE-ABS-KEY()
        # 不支持部分组合，需要通过二次过滤实现精确匹配

        # 根据选择的字段确定 API 查询语法
        if set(fields) == {"title"}:
            api_field = "TITLE"
        elif set(fields) == {"keywords"}:
            api_field = "KEY"
        elif set(fields) == {"abstract"}:
            api_field = "ABS"
        else:
            # 多个字段组合，使用全部字段查询，然后通过二次过滤实现精确匹配
            api_field = "TITLE-ABS-KEY"

        # 关键词查询构建
        # 对每个关键词进行转义处理
        escaped_keywords = [self._escape_query_term(kw) for kw in keywords]

        if require_all_keywords and len(escaped_keywords) > 1:
            # AND 连接所有关键词
            keyword_query = " AND ".join(f'{api_field}("{kw}")' for kw in escaped_keywords)
        else:
            # OR 连接关键词
            keyword_query = " OR ".join(f'{api_field}("{kw}")' for kw in escaped_keywords)

        # 排除关键词
        if exclude_keywords:
            escaped_exclude = [self._escape_query_term(kw) for kw in exclude_keywords]
            exclude_query = " AND ".join(f'NOT {api_field}("{kw}")' for kw in escaped_exclude)
            keyword_query = f"({keyword_query}) AND {exclude_query}"

        # 年份范围
        if year_range:
            start_year, end_year = year_range
            year_query = f"PUBYEAR > {start_year-1} AND PUBYEAR < {end_year+1}"
            query = f"({keyword_query}) AND ({year_query})"
        else:
            query = keyword_query

        return query

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        keywords: List[str],
        exclude_keywords: List[str] = None,
        match_mode: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """二次过滤搜索结果

        根据匹配模式过滤结果，确保返回的文献符合匹配要求。

        Args:
            results: 原始搜索结果
            keywords: 要求的关键词列表
            exclude_keywords: 排除的关键词列表
            match_mode: 匹配模式 {"fields": ["title", "keywords", "abstract"], "combination": "all" | "any"}

        Returns:
            过滤后的结果
        """
        import re

        # 确定搜索字段
        if match_mode and match_mode.get("fields"):
            fields = match_mode["fields"]
        else:
            fields = ["title", "keywords", "abstract"]

        # 确定组合模式
        combination = match_mode.get("combination", "all") if match_mode else "all"

        filtered = []
        for paper in results:
            title = (paper.get("title") or "").lower()
            abstract = (paper.get("abstract") or "").lower()
            paper_keywords = " ".join(paper.get("keywords") or []).lower()

            # 构建字段文本映射
            field_texts = {
                "title": title,
                "abstract": abstract,
                "keywords": paper_keywords
            }

            # 检查关键词匹配
            keywords_match = self._check_keywords_match(
                keywords, field_texts, fields, combination
            )

            if not keywords_match:
                continue

            if not keywords_match:
                continue

            # 检查是否包含排除关键词
            if exclude_keywords:
                excluded = False
                for ex_kw in exclude_keywords:
                    ex_kw_lower = ex_kw.lower()
                    # 在选择的字段中检查排除关键词
                    for field in fields:
                        if ex_kw_lower in field_texts.get(field, ""):
                            excluded = True
                            self.logger.debug(f"排除文献（{field}包含'{ex_kw}'）: {title[:50]}...")
                            break
                    if excluded:
                        break
                if excluded:
                    continue

            filtered.append(paper)

        return filtered

    def _check_keywords_match(
        self,
        keywords: List[str],
        field_texts: Dict[str, str],
        fields: List[str],
        combination: str
    ) -> bool:
        """检查关键词是否匹配

        Args:
            keywords: 关键词列表
            field_texts: 字段文本映射 {"title": "...", "abstract": "...", "keywords": "..."}
            fields: 要检查的字段列表
            combination: "all" (所有字段都要匹配) 或 "any" (至少一个字段匹配)

        Returns:
            是否匹配
        """
        import re

        # combination="all": 每个字段都要包含所有关键词
        # combination="any": 至少一个字段包含至少一个关键词

        if combination == "all":
            # 严格模式：每个字段都要包含所有关键词
            for field in fields:
                text = field_texts.get(field, "")
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower not in text:
                        # 尝试分词匹配
                        words = re.split(r'[\s\-_]+', kw_lower)
                        content_words = [w for w in words if len(w) > 2 and w not in {
                            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
                            'had', 'her', 'was', 'one', 'our', 'out', 'with', 'from'
                        }]
                        matched_count = sum(1 for w in content_words if w in text)
                        if len(content_words) > 0 and matched_count < len(content_words) / 2:
                            return False  # 该字段不包含某个关键词
            return True  # 所有字段都匹配

        else:  # "any"
            # 宽松模式：至少一个字段包含至少一个关键词
            for field in fields:
                text = field_texts.get(field, "")
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower in text:
                        return True  # 找到一个匹配就返回

                    # 尝试分词匹配
                    words = re.split(r'[\s\-_]+', kw_lower)
                    content_words = [w for w in words if len(w) > 2 and w not in {
                        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
                        'had', 'her', 'was', 'one', 'our', 'out', 'with', 'from'
                    }]
                    matched_count = sum(1 for w in content_words if w in text)
                    if len(content_words) > 0 and matched_count >= len(content_words) / 2:
                        return True  # 分词匹配成功

            return False  # 没有任何字段匹配任何关键词

    async def _search_with_pybliometrics(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """使用 pybliometrics 搜索

        Args:
            query: 查询字符串
            max_results: 最大结果数

        Returns:
            文献列表
        """
        # 在后台线程中执行同步操作
        loop = asyncio.get_event_loop()

        def sync_search():
            try:
                search = ScopusSearch(
                    query,
                    api_key=self.api_key,
                    view="STANDARD",
                    verbose=True
                )

                results = []
                for i, result in enumerate(search.results[:max_results]):
                    paper = {
                        "title": result.title,
                        "authors": result.authors.split("; ") if result.authors else [],
                        "year": result.coverDate[:4] if result.coverDate else None,
                        "journal": result.publicationName,
                        "doi": result.doi,
                        "abstract": result.description,
                        "keywords": result.authkeywords.split("; ") if result.authkeywords else [],
                        "citations": int(result.citedby_count) if result.citedby_count else 0,
                        "source": "Elsevier",
                        "url": result.url,
                        "retrieved_at": datetime.now().isoformat()
                    }
                    results.append(paper)

                return results

            except Exception as e:
                self.logger.error(f"pybliometrics 搜索失败: {e}")
                return []

        results = await loop.run_in_executor(None, sync_search)
        return results

    async def _search_with_rest_api(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """使用 REST API 搜索（支持分页）

        Args:
            query: 查询字符串
            max_results: 最大结果数

        Returns:
            文献列表
        """
        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        }

        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token

        url = f"{self.base_url}/search/scopus"

        all_results = []
        start = 0
        per_page = min(self.MAX_RESULTS_PER_QUERY, 20)  # 每页最多20篇（API限制）

        while len(all_results) < max_results:
            params = {
                "query": query,
                "count": per_page,
                "start": start,
                "view": "STANDARD"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"API 请求失败 (start={start}): {response.status}")
                        if start == 0:  # 第一次请求就失败
                            self.logger.error(f"错误详情: {error_text}")
                        break

                    data = await response.json()

            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                self.logger.info(f"没有更多结果 (start={start})")
                break

            self.logger.info(f"获取到 {len(entries)} 篇文献 (start={start})")

            for entry in entries:
                paper = {
                    "title": entry.get("dc:title"),
                    "authors": self._parse_authors(entry.get("author", [])),
                    "year": entry.get("prism:coverDate", "")[:4] if entry.get("prism:coverDate") else None,
                    "journal": entry.get("prism:publicationName"),
                    "doi": entry.get("prism:doi"),
                    "abstract": entry.get("dc:description"),
                    "keywords": [],
                    "citations": int(entry.get("citedby-count", 0)),
                    "source": "Elsevier",
                    "url": entry.get("prism:url"),
                    "retrieved_at": datetime.now().isoformat()
                }
                all_results.append(paper)

            # 如果返回的结果少于每页数量，说明已经到最后一页
            if len(entries) < per_page:
                self.logger.info(f"已到达最后一页")
                break

            # 移动到下一页
            start += per_page

        self.logger.info(f"分页搜索完成: 共获取 {len(all_results)} 篇文献")
        return all_results[:max_results]  # 返回最多max_results篇

    def _parse_authors(self, authors_data: List[Dict]) -> List[str]:
        """解析作者信息

        Args:
            authors_data: 作者数据

        Returns:
            作者姓名列表
        """
        if not authors_data:
            return []

        return [author.get("authname", "") for author in authors_data if author.get("authname")]

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
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        }

        url = f"{self.base_url}/article/doi/{doi}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"获取文献详情失败: {response.status}")
                    return None

                data = await response.json()

        article = data.get("full-text-retrieval-response", {})

        return {
            "doi": doi,
            "title": article.get("coredata", {}).get("dc:title"),
            "abstract": article.get("coredata", {}).get("dc:description"),
            "authors": self._parse_authors(article.get("authors", {}).get("author", [])),
            "year": article.get("coredata", {}).get("prism:coverDate", "")[:4],
            "journal": article.get("coredata", {}).get("prism:publicationName"),
            "keywords": article.get("coredata", {}).get("dctype:subject", []),
            "source": "Elsevier",
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
            test_url = "https://api.elsevier.com/content/search/scopus"
            headers = {
                "X-ELS-APIKey": self.api_key,
                "Accept": "application/json"
            }
            params = {"query": "test", "count": 1}

            response = requests.get(test_url, headers=headers, params=params, timeout=10)

            # 200 表示密钥有效，401 表示无效
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"验证 API 密钥失败: {e}")
            return False
