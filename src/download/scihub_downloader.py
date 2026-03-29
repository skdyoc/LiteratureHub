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
SciHub 下载器

通过智能代理选择从 SciHub 下载 PDF 文献。
"""

import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from lxml import html as lxml_html
from urllib.parse import urljoin

from .vpn_detector import VPNDetector, ProxyInfo as VPNProxyInfo
from .proxy_manager import ProxyManager, create_default_proxy_manager, ProxyInfo as ManagerProxyInfo


@dataclass
class DownloadResult:
    """下载结果"""
    doi: str
    success: bool
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    source: str = "scihub"


class SciHubDownloader:
    """SciHub 下载器

    通过 VPN 代理从 SciHub 下载 PDF 文献。

    用法：
    ```python
    downloader = SciHubDownloader(proxy_url="http://127.0.0.1:7890")

    # 下载单篇
    result = downloader.download("10.1016/j.energy.2023.123456", "pdfs/all/")

    # 批量下载
    results = downloader.download_batch(doi_list, "pdfs/all/")
    ```
    """

    # SciHub 镜像列表（2026年3月更新 - 来自 Sci-Hub中文社区）
    SCIHUB_MIRRORS = [
        "https://sci-hub.se",      # 官方主站（推荐）
        "https://sci-hub.st",      # 官方主站2（推荐）
        "https://sci-hub.ru",      # 官方俄罗斯站（推荐）
        "https://sci-hub.su",      # 官方新镜像（推荐）
        "https://sci-hub.tw",      # 官方台湾站（推荐）
        "https://sci-hub.wf",      # 备用站
        "https://sci-hub.do",      # 备用站
        "https://sci-hub.mksa.top", # 备用站
        "https://sci-hub.ms",      # 备用站
    ]

    # 浏览器请求头
    BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    def __init__(
        self,
        proxy_url: str = None,
        proxy_manager: ProxyManager = None,
        output_dir: str = "pdfs/all",
        timeout: int = 60,
        require_proxy: bool = False,
        proxy_switch_interval: int = 10
    ):
        """初始化下载器

        Args:
            proxy_url: 代理 URL（如 http://127.0.0.1:7890）已弃用，建议使用 proxy_manager
            proxy_manager: 智能代理管理器（推荐使用）
            output_dir: 输出目录
            timeout: 请求超时时间（秒）
            require_proxy: 是否强制要求代理（True则没有代理时失败）
            proxy_switch_interval: 代理切换间隔（每N篇切换一次）
        """
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.require_proxy = require_proxy
        self.proxy_switch_interval = proxy_switch_interval
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化代理管理器
        if proxy_manager:
            self.proxy_manager = proxy_manager
            self.current_proxy = None
        elif proxy_url:
            # 兼容旧的 proxy_url 参数
            self.proxy_manager = create_default_proxy_manager()
            self.current_proxy = self.proxy_manager.proxies[0]
        else:
            # 自动检测代理
            self.proxy_manager = create_default_proxy_manager()
            self.current_proxy = None

            # 尝试启动 VPN
            detector = VPNDetector()
            vpn_proxy = detector.ensure_proxy_running()

            if vpn_proxy:
                self.current_proxy = self.proxy_manager.proxies[0]
                self.logger.info(f"使用代理: {vpn_proxy.proxy_url}")
            else:
                if self.require_proxy:
                    self.logger.error("无法获取代理，下载无法进行")
                    raise RuntimeError("需要代理才能下载PDF")
                else:
                    self.logger.warning("无代理可用，下载可能失败")

        # 创建会话
        self.session = requests.Session()
        self._update_session_proxy()
        self.session.headers.update(self.BROWSER_HEADERS)

        # 统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }

        # 下载计数器（用于代理切换）
        self._download_count = 0

    def _update_session_proxy(self):
        """更新会话代理配置"""
        if self.current_proxy:
            proxies = {
                "http": self.current_proxy.proxy_url,
                "https": self.current_proxy.proxy_url
            }
            self.session.proxies.update(proxies)
            self.logger.debug(f"代理已更新: {self.current_proxy.name}")
        else:
            self.session.proxies.clear()

    def download(
        self,
        doi: str,
        output_dir: str = None,
        filename: str = None,
        retry_on_mirror_fail: bool = True,
        max_retries: int = 3
    ) -> DownloadResult:
        """
        下载单篇文献（智能代理选择）

        Args:
            doi: DOI
            output_dir: 输出目录（可选，覆盖默认值）
            filename: 文件名（可选，默认为 DOI.pdf）
            retry_on_mirror_fail: 镜像站失败时是否重试其他镜像
            max_retries: 最大重试次数（失败后切换代理重试）

        Returns:
            下载结果
        """
        self.stats["total"] += 1
        self.logger.info(f"开始下载: {doi}")

        # 确定输出目录
        save_dir = Path(output_dir) if output_dir else self.output_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        # 确定文件名
        if not filename:
            safe_doi = doi.replace("/", "_").replace("\\", "_")
            filename = f"{safe_doi}.pdf"

        output_path = save_dir / filename

        # 检查是否已存在
        if output_path.exists():
            self.logger.info(f"文件已存在，跳过: {output_path}")
            self.stats["success"] += 1
            return DownloadResult(
                doi=doi,
                success=True,
                pdf_path=str(output_path),
                source="cache"
            )

        # 智能代理选择：每 N 篇切换一次代理
        if self._download_count % self.proxy_switch_interval == 0:
            self.logger.info(f"下载计数: {self._download_count}，重新选择最佳代理...")
            best_proxy = self.proxy_manager.select_best_proxy()
            if best_proxy:
                self.current_proxy = best_proxy
                self._update_session_proxy()

        self._download_count += 1

        # 尝试下载（带代理切换重试）
        for retry in range(max_retries):
            # 尝试所有镜像站
            for mirror in self.SCIHUB_MIRRORS:
                try:
                    result = self._download_from_mirror(doi, mirror, output_path)

                    if result.success:
                        self.stats["success"] += 1
                        self.proxy_manager.record_success(self.current_proxy)
                        return result

                except Exception as e:
                    self.logger.warning(f"镜像 {mirror} 下载失败: {e}")
                    continue

            # 所有镜像都失败，切换代理重试
            if retry < max_retries - 1:
                self.logger.warning(f"第 {retry + 1} 次尝试失败，切换代理...")
                best_proxy = self.proxy_manager.select_best_proxy()
                if best_proxy:
                    self.current_proxy = best_proxy
                    self._update_session_proxy()

        # 所有重试都失败
        error_msg = f"所有 SciHub 镜像都无法下载（已重试 {max_retries} 次）"
        self.stats["failed"] += 1
        self.stats["errors"].append({"doi": doi, "error": error_msg})
        self.proxy_manager.record_failure(self.current_proxy)

        return DownloadResult(
            doi=doi,
            success=False,
            error=error_msg
        )

    def _download_from_mirror(
        self,
        doi: str,
        mirror_url: str,
        output_path: Path
    ) -> DownloadResult:
        """从指定镜像下载"""
        self.logger.debug(f"尝试镜像: {mirror_url}")

        # 构建 SciHub URL
        scihub_url = f"{mirror_url}/{doi}"

        # 获取页面
        response = self.session.get(
            scihub_url,
            timeout=self.timeout,
            allow_redirects=True
        )

        if response.status_code != 200:
            raise Exception(f"HTTP 错误: {response.status_code}")

        content = response.content
        content_type = response.headers.get('Content-Type', '')

        # 检查是否直接返回 PDF
        if 'application/pdf' in content_type or content.startswith(b'%PDF'):
            with open(output_path, 'wb') as f:
                f.write(content)
            self.logger.info(f"下载成功: {output_path}")
            return DownloadResult(
                doi=doi,
                success=True,
                pdf_path=str(output_path),
                source="scihub"
            )

        # 解析页面获取 PDF 链接
        pdf_url = self._extract_pdf_url(response.text, mirror_url)

        if not pdf_url:
            raise Exception("无法从页面提取 PDF 链接")

        # 下载 PDF
        pdf_response = self.session.get(
            pdf_url,
            timeout=self.timeout,
            stream=True
        )

        if pdf_response.status_code != 200:
            raise Exception(f"PDF 下载失败: HTTP {pdf_response.status_code}")

        # 检查内容类型
        pdf_content = pdf_response.content
        if not pdf_content.startswith(b'%PDF'):
            raise Exception("响应不是有效的 PDF 文件")

        # 保存文件
        with open(output_path, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)

        self.logger.info(f"下载成功: {output_path}")

        return DownloadResult(
            doi=doi,
            success=True,
            pdf_path=str(output_path),
            source="scihub"
        )

    def _extract_pdf_url(self, html: str, base_url: str) -> Optional[str]:
        """从 HTML 页面提取 PDF 链接

        使用多种方法按优先级提取：
        1. Meta 标签（2024+ 新格式优先）
        2. /storage/ 路径（2024+ 新格式）
        3. JavaScript fetch 模式（2024+ 新格式）
        4. lxml + XPath 解析（传统格式）
        5. BeautifulSoup 解析（embed/iframe 标签）
        6. 正则表达式匹配（最后备选）
        """
        soup = BeautifulSoup(html, 'html.parser')

        # ========== 方法1: Meta 标签（2024+ 新格式，优先级最高）==========
        # 新 SciHub 使用: <meta name="citation_pdf_url" content="/storage/..."/>
        meta_tag = soup.find('meta', attrs={'name': 'citation_pdf_url'})
        if meta_tag and meta_tag.get('content'):
            pdf_url = meta_tag['content']
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(base_url, pdf_url)
            self.logger.debug(f"使用 meta 标签找到 PDF 链接（新格式）")
            return pdf_url

        # ========== 方法2: /storage/ 路径（2024+ 新格式）==========
        # 查找任何包含 /storage/ 的链接或路径
        storage_pattern = r'["\'](/storage/[^"\']+\.pdf)["\']'
        storage_match = re.search(storage_pattern, html)
        if storage_match:
            pdf_url = storage_match.group(1)
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(base_url, pdf_url)
            self.logger.debug(f"使用 /storage/ 路径找到 PDF 链接（新格式）")
            return pdf_url

        # ========== 方法3: JavaScript fetch 模式（2024+ 新格式）==========
        # 新格式: fetch('/storage/moscow/...pdf')
        fetch_pattern = r'fetch\(["\']([^"\']+\.pdf)["\']'
        fetch_match = re.search(fetch_pattern, html)
        if fetch_match:
            pdf_url = fetch_match.group(1)
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(base_url, pdf_url)
            self.logger.debug(f"使用 fetch 模式找到 PDF 链接（新格式）")
            return pdf_url

        # ========== 方法4: lxml + XPath 解析（传统格式）==========
        try:
            tree = lxml_html.fromstring(html)
            pdf_links = tree.xpath("//a[contains(@href, '.pdf') or contains(@href, '/download')]")

            if pdf_links:
                pdf_url = pdf_links[0].get('href', '')
                if pdf_url:
                    if not pdf_url.startswith('http'):
                        pdf_url = urljoin(base_url, pdf_url)
                    self.logger.debug(f"使用 lxml 解析找到 PDF 链接（传统格式）")
                    return pdf_url
        except Exception as e:
            self.logger.debug(f"lxml 解析失败: {e}")

        # ========== 方法5: BeautifulSoup 查找 embed 标签（旧格式）==========
        embed = soup.find('embed')
        if embed and embed.get('src'):
            pdf_url = embed['src']
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(base_url, pdf_url)
            self.logger.debug(f"使用 embed 标签找到 PDF 链接（旧格式）")
            return pdf_url

        # ========== 方法6: BeautifulSoup 查找 iframe 标签（旧格式）==========
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            pdf_url = iframe['src']
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(base_url, pdf_url)
            self.logger.debug(f"使用 iframe 标签找到 PDF 链接（旧格式）")
            return pdf_url

        # ========== 方法7: 正则表达式匹配（最后备选）==========
        patterns = [
            r'(https?://[^\s<>"]+?\.pdf)',
            r'src=["\']([^"\']+\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']+\.pdf[^"\']*)["\']'
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                pdf_url = match.group(1)
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin(base_url, pdf_url)
                self.logger.debug(f"使用正则表达式找到 PDF 链接")
                return pdf_url

        return None

    def download_batch(
        self,
        doi_list: List[str],
        output_dir: str = None,
        delay: float = 2.0,
        progress_callback: callable = None
    ) -> List[DownloadResult]:
        """
        批量下载文献

        Args:
            doi_list: DOI 列表
            output_dir: 输出目录
            delay: 每次下载间隔（秒）
            progress_callback: 进度回调函数 callback(current, total, result)

        Returns:
            下载结果列表
        """
        results = []
        total = len(doi_list)

        self.logger.info(f"开始批量下载: {total} 篇文献")

        for i, doi in enumerate(doi_list):
            result = self.download(doi, output_dir)
            results.append(result)

            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total, result)

            # 延迟
            if i < total - 1:
                time.sleep(delay)

        # 输出统计
        self.logger.info(
            f"批量下载完成: {self.stats['success']}/{total} 成功"
        )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }
