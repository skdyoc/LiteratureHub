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
Unpaywall API 客户端

Unpaywall 是一个完全合法的开放获取论文数据库，从 50,000+ 家合法来源收集论文。
官网: https://unpaywall.org
API 文档: https://unpaywall.org/api
"""

import logging
import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UnpaywallLocation:
    """Unpaywall 论文位置信息"""
    url: str
    source: str
    license: Optional[str] = None
    version: Optional[str] = None
    is_oa: bool = False


@dataclass
class UnpaywallResult:
    """Unpaywall 查询结果"""
    doi: str
    is_oa: bool  # 是否开放获取
    oa_locations: list[UnpaywallLocation]
    best_oa_location: Optional[UnpaywallLocation]
    title: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None

    @property
    def has_pdf(self) -> bool:
        """是否有可用的 PDF"""
        return self.is_oa and self.best_oa_location is not None

    @property
    def pdf_url(self) -> Optional[str]:
        """获取最佳 PDF URL"""
        if self.best_oa_location:
            return self.best_oa_location.url
        return None


class UnpaywallClient:
    """Unpaywall API 客户端

    用法：
    ```python
    client = UnpaywallClient(email="your-email@example.com")
    result = client.query("10.1016/j.energy.2023.128788")

    if result.has_pdf:
        pdf_content = client.download_pdf(result.pdf_url)
    ```
    """

    API_BASE = "https://api.unpaywall.org/v2"
    USER_AGENT = "LiteratureHub/1.0 (mailto:{email})"

    def __init__(self, email: str, timeout: int = 30):
        """初始化 Unpaywall 客户端

        Args:
            email: 电子邮箱（Unpaywall 要求，用于统计和联系）
            timeout: 请求超时时间（秒）
        """
        if not email or "@" not in email:
            raise ValueError("请提供有效的邮箱地址")

        self.email = email
        self.timeout = timeout
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT.format(email=email),
            "Accept": "application/json"
        })

    def query(self, doi: str) -> Optional[UnpaywallResult]:
        """查询论文的开放获取状态

        Args:
            doi: 论文 DOI

        Returns:
            UnpaywallResult 对象，如果查询失败返回 None
        """
        url = f"{self.API_BASE}/{doi}"
        params = {"email": self.email}

        try:
            self.logger.debug(f"查询 Unpaywall: {doi}")
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                return self._parse_result(data)
            elif response.status_code == 404:
                self.logger.debug(f"Unpaywall 未找到论文: {doi}")
                return None
            else:
                self.logger.warning(f"Unpaywall API 错误: HTTP {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"Unpaywall 查询超时: {doi}")
            return None
        except Exception as e:
            self.logger.error(f"Unpaywall 查询失败: {e}")
            return None

    def _parse_result(self, data: Dict[str, Any]) -> Optional[UnpaywallResult]:
        """解析 Unpaywall API 响应"""
        try:
            # 解析开放获取位置
            oa_locations = []
            for loc in data.get("oa_locations", []):
                oa_locations.append(UnpaywallLocation(
                    url=loc.get("url", ""),
                    source=loc.get("source", "unknown"),
                    license=loc.get("license"),
                    version=loc.get("version"),
                    is_oa=loc.get("is_oa", False)
                ))

            # 解析最佳位置
            best_oa = None
            if data.get("best_oa_location"):
                best = data["best_oa_location"]
                best_oa = UnpaywallLocation(
                    url=best.get("url", ""),
                    source=best.get("source", "unknown"),
                    license=best.get("license"),
                    version=best.get("version"),
                    is_oa=best.get("is_oa", False)
                )

            return UnpaywallResult(
                doi=data.get("doi", ""),
                is_oa=data.get("is_oa", False),
                oa_locations=oa_locations,
                best_oa_location=best_oa,
                title=data.get("title"),
                year=str(data.get("year", "")) if data.get("year") else None,
                journal=data.get("journal_name")
            )

        except Exception as e:
            self.logger.error(f"解析 Unpaywall 响应失败: {e}")
            return None

    def download_pdf(self, pdf_url: str, timeout: int = 60) -> Optional[bytes]:
        """下载 PDF 文件

        Args:
            pdf_url: PDF URL
            timeout: 下载超时时间（秒）

        Returns:
            PDF 内容（bytes），失败返回 None
        """
        try:
            self.logger.debug(f"从 Unpaywall 下载 PDF: {pdf_url}")
            response = self.session.get(pdf_url, timeout=timeout, stream=True)

            if response.status_code == 200:
                content = response.content

                # 验证是否为有效 PDF
                if content.startswith(b'%PDF'):
                    return content
                else:
                    self.logger.warning(f"下载的不是 PDF 文件")
                    return None
            else:
                self.logger.warning(f"PDF 下载失败: HTTP {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"PDF 下载超时")
            return None
        except Exception as e:
            self.logger.error(f"PDF 下载失败: {e}")
            return None

    def download_by_doi(self, doi: str, output_path: str) -> bool:
        """通过 DOI 下载论文（一步完成）

        Args:
            doi: 论文 DOI
            output_path: 输出文件路径

        Returns:
            是否下载成功
        """
        # 查询论文
        result = self.query(doi)

        if not result or not result.has_pdf:
            self.logger.info(f"论文无开放获取版本: {doi}")
            return False

        # 下载 PDF
        pdf_content = self.download_pdf(result.pdf_url)

        if pdf_content:
            # 保存文件
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'wb') as f:
                f.write(pdf_content)

            self.logger.info(f"Unpaywall 下载成功: {output_path}")
            return True

        return False

    def get_oa_rate(self, doi_list: list[str]) -> Dict[str, Any]:
        """统计 DOI 列表的开放获取率

        Args:
            doi_list: DOI 列表

        Returns:
            统计信息 {"total": int, "oa_count": int, "oa_rate": float}
        """
        total = len(doi_list)
        oa_count = 0

        for doi in doi_list:
            result = self.query(doi)
            if result and result.is_oa:
                oa_count += 1

        oa_rate = (oa_count / total * 100) if total > 0 else 0

        return {
            "total": total,
            "oa_count": oa_count,
            "oa_rate": oa_rate
        }


def create_unpaywall_client(email: str = None) -> UnpaywallClient:
    """创建 Unpaywall 客户端

    Args:
        email: 邮箱地址，如果为 None 则使用默认值

    Returns:
        UnpaywallClient 实例
    """
    if email is None:
        # 可以从配置文件读取默认邮箱
        email = "literaturehub@example.com"

    return UnpaywallClient(email=email)
