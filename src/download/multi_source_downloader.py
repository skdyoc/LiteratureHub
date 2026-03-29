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
多源论文下载器

优先使用合法的 Unpaywall（开放获取），失败后使用 SciHub 作为备用。
结合两种来源的优势，最大化下载成功率。
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .unpaywall_client import UnpaywallClient, UnpaywallResult
from .scihub_downloader import SciHubDownloader, DownloadResult
from .proxy_manager import ProxyManager


class DownloadSource(Enum):
    """下载来源"""
    UNPAYWALL = "unpaywall"
    SCIHUB = "scihub"
    CACHE = "cache"
    NONE = "none"


@dataclass
class MultiSourceResult:
    """多源下载结果"""
    doi: str
    success: bool
    source: DownloadSource
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    unpaywall_available: bool = False
    scihub_tried: bool = False
    elapsed_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doi": self.doi,
            "success": self.success,
            "source": self.source.value,
            "pdf_path": self.pdf_path,
            "error": self.error,
            "unpaywall_available": self.unpaywall_available,
            "scihub_tried": self.scihub_tried,
            "elapsed_time": self.elapsed_time
        }


class MultiSourceDownloader:
    """多源论文下载器

    策略：
    1. 优先使用 Unpaywall（合法、免费、不需要 VPN）
    2. 如果 Unpaywall 无开放获取版本，使用 SciHub 备用
    3. 记录每个来源的成功率，用于统计

    用法：
    ```python
    downloader = MultiSourceDownloader(
        email="your-email@example.com",
        proxy_manager=proxy_manager
    )

    result = downloader.download("10.1016/j.energy.2023.128788")
    print(f"来源: {result.source}, 成功: {result.success}")
    ```
    """

    def __init__(
        self,
        email: str,
        proxy_manager: ProxyManager = None,
        output_dir: str = "pdfs/all",
        prefer_unpaywall: bool = True
    ):
        """初始化多源下载器

        Args:
            email: 邮箱地址（Unpaywall 要求）
            proxy_manager: 代理管理器（用于 SciHub）
            output_dir: 输出目录
            prefer_unpaywall: 是否优先使用 Unpaywall
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefer_unpaywall = prefer_unpaywall

        # Unpaywall 客户端（不需要代理）
        self.unpaywall = UnpaywallClient(email=email)

        # SciHub 下载器（需要代理）
        if proxy_manager:
            self.scihub = SciHubDownloader(
                proxy_manager=proxy_manager,
                output_dir=output_dir,
                require_proxy=True,
                proxy_switch_interval=10
            )
        else:
            self.scihub = None
            self.logger.warning("未提供代理管理器，SciHub 下载将不可用")

        # 统计信息
        self.stats = {
            "total": 0,
            "unpaywall_success": 0,
            "scihub_success": 0,
            "cache": 0,
            "failed": 0,
            "unpaywall_available_rate": 0.0
        }

    def download(
        self,
        doi: str,
        filename: str = None,
        try_scihub: bool = True,
        max_retries: int = 2
    ) -> MultiSourceResult:
        """下载论文（多源策略）

        Args:
            doi: 论文 DOI
            filename: 文件名（可选）
            try_scihub: Unpaywall 失败时是否尝试 SciHub
            max_retries: SciHub 最大重试次数

        Returns:
            MultiSourceResult 对象
        """
        import time
        start_time = time.time()

        self.stats["total"] += 1
        self.logger.info(f"开始下载: {doi}")

        # 确定输出路径
        if not filename:
            safe_doi = doi.replace("/", "_").replace("\\", "_")
            filename = f"{safe_doi}.pdf"

        output_path = self.output_dir / filename

        # 检查缓存
        if output_path.exists():
            self.logger.info(f"文件已存在，跳过: {output_path}")
            self.stats["cache"] += 1
            return MultiSourceResult(
                doi=doi,
                success=True,
                source=DownloadSource.CACHE,
                pdf_path=str(output_path),
                elapsed_time=time.time() - start_time
            )

        # 策略 1: 优先 Unpaywall
        if self.prefer_unpaywall:
            result = self._try_unpaywall(doi, output_path)
            if result.success:
                self.stats["unpaywall_success"] += 1
                result.elapsed_time = time.time() - start_time
                return result

        # 策略 2: Unpaywall 失败，尝试 SciHub
        if try_scihub and self.scihub:
            self.logger.info(f"Unpaywall 无可用版本，尝试 SciHub...")
            scihub_result = self.scihub.download(
                doi,
                filename=filename,
                max_retries=max_retries
            )

            if scihub_result.success:
                self.stats["scihub_success"] += 1
                return MultiSourceResult(
                    doi=doi,
                    success=True,
                    source=DownloadSource.SCIHUB,
                    pdf_path=scihub_result.pdf_path,
                    unpaywall_available=result.unpaywall_available if result else False,
                    scihub_tried=True,
                    elapsed_time=time.time() - start_time
                )

        # 所有来源都失败
        self.stats["failed"] += 1
        error_msg = "Unpaywall 无开放获取版本，SciHub 下载失败"

        return MultiSourceResult(
            doi=doi,
            success=False,
            source=DownloadSource.NONE,
            error=error_msg,
            unpaywall_available=result.unpaywall_available if result else False,
            scihub_tried=True if self.scihub else False,
            elapsed_time=time.time() - start_time
        )

    def _try_unpaywall(self, doi: str, output_path: Path) -> MultiSourceResult:
        """尝试从 Unpaywall 下载"""
        import time

        start_time = time.time()
        result = self.unpaywall.query(doi)

        if result and result.has_pdf:
            self.logger.info(f"Unpaywall 找到开放获取版本: {doi}")

            pdf_content = self.unpaywall.download_pdf(result.pdf_url)

            if pdf_content:
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)

                self.logger.info(f"Unpaywall 下载成功: {output_path}")
                return MultiSourceResult(
                    doi=doi,
                    success=True,
                    source=DownloadSource.UNPAYWALL,
                    pdf_path=str(output_path),
                    unpaywall_available=True,
                    elapsed_time=time.time() - start_time
                )

        # Unpaywall 无可用版本
        if result:
            self.logger.info(f"Unpaywall: 论文无开放获取版本 (is_oa={result.is_oa})")
            return MultiSourceResult(
                doi=doi,
                success=False,
                source=DownloadSource.NONE,
                unpaywall_available=result.is_oa,
                elapsed_time=time.time() - start_time
            )
        else:
            self.logger.info(f"Unpaywall: 未找到论文信息")
            return MultiSourceResult(
                doi=doi,
                success=False,
                source=DownloadSource.NONE,
                unpaywall_available=False,
                elapsed_time=time.time() - start_time
            )

    def download_batch(
        self,
        doi_list: List[str],
        delay: float = 1.0,
        progress_callback = None
    ) -> List[MultiSourceResult]:
        """批量下载

        Args:
            doi_list: DOI 列表
            delay: 每次下载间隔（秒）
            progress_callback: 进度回调 callback(current, total, result)

        Returns:
            下载结果列表
        """
        results = []
        total = len(doi_list)

        self.logger.info(f"开始批量下载: {total} 篇文献")

        for i, doi in enumerate(doi_list):
            result = self.download(doi)
            results.append(result)

            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total, result)

            # 延迟
            if i < total - 1:
                import time
                time.sleep(delay)

        # 输出统计
        self._print_stats()

        return results

    def _print_stats(self):
        """打印统计信息"""
        total = self.stats["total"]
        if total == 0:
            return

        unpaywall_rate = (self.stats["unpaywall_success"] / total * 100) if total > 0 else 0
        scihub_rate = (self.stats["scihub_success"] / total * 100) if total > 0 else 0
        total_success = self.stats["unpaywall_success"] + self.stats["scihub_success"] + self.stats["cache"]
        success_rate = (total_success / total * 100) if total > 0 else 0

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("下载统计:")
        self.logger.info(f"  总计: {total}")
        self.logger.info(f"  Unpaywall 成功: {self.stats['unpaywall_success']} ({unpaywall_rate:.1f}%)")
        self.logger.info(f"  SciHub 成功: {self.stats['scihub_success']} ({scihub_rate:.1f}%)")
        self.logger.info(f"  缓存: {self.stats['cache']}")
        self.logger.info(f"  失败: {self.stats['failed']}")
        self.logger.info(f"  总成功率: {success_rate:.1f}%")
        self.logger.info("=" * 60)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats["total"]
        return {
            **self.stats,
            "unpaywall_success_rate": (self.stats["unpaywall_success"] / total * 100) if total > 0 else 0,
            "scihub_success_rate": (self.stats["scihub_success"] / total * 100) if total > 0 else 0,
            "total_success_rate": ((self.stats["unpaywall_success"] + self.stats["scihub_success"] + self.stats["cache"]) / total * 100) if total > 0 else 0
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total": 0,
            "unpaywall_success": 0,
            "scihub_success": 0,
            "cache": 0,
            "failed": 0,
            "unpaywall_available_rate": 0.0
        }


def create_multi_source_downloader(
    email: str,
    output_dir: str = "pdfs/all"
) -> MultiSourceDownloader:
    """创建多源下载器（使用默认配置）

    Args:
        email: 邮箱地址
        output_dir: 输出目录

    Returns:
        MultiSourceDownloader 实例
    """
    from .proxy_manager import create_default_proxy_manager

    proxy_manager = create_default_proxy_manager()

    return MultiSourceDownloader(
        email=email,
        proxy_manager=proxy_manager,
        output_dir=output_dir
    )
