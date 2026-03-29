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
智能代理管理器

支持从多种来源加载代理配置，并发测试代理延迟，智能选择最佳代理。
"""

import logging
import socket
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


@dataclass
class ProxyInfo:
    """代理信息"""
    name: str
    host: str
    port: int
    proxy_type: str = "http"
    latency: float = 9999.0
    success_count: int = 0
    fail_count: int = 0
    last_check: float = 0.0

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.fail_count
        return (self.success_count / total * 100) if total > 0 else 0.0

    @property
    def proxy_url(self) -> str:
        """代理 URL"""
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "type": self.proxy_type,
            "latency": self.latency,
            "success_rate": self.success_rate,
            "success_count": self.success_count,
            "fail_count": self.fail_count
        }


class ProxyManager:
    """智能代理管理器

    用法：
    ```python
    # 方式1: 从 YAML 配置加载
    manager = ProxyManager.from_yaml("config/proxies.yaml")
    best_proxy = manager.select_best_proxy()

    # 方式2: 使用默认代理列表
    manager = ProxyManager(default_proxies=[
        {"name": "Mihomo", "host": "127.0.0.1", "port": 7890}
    ])
    best_proxy = manager.select_best_proxy()
    ```
    """

    # 测试 URL（用于延迟测试）
    TEST_URLS = [
        "https://www.google.com",
        "https://www.github.com",
        "https://sci-hub.se"
    ]

    def __init__(
        self,
        default_proxies: List[Dict] = None,
        max_concurrent: int = 10,
        test_timeout: float = 5.0
    ):
        """初始化代理管理器

        Args:
            default_proxies: 默认代理列表 [{"name": "...", "host": "...", "port": ...}]
            max_concurrent: 并发测试的最大代理数
            test_timeout: 测试超时时间（秒）
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.proxies: List[ProxyInfo] = []
        self.max_concurrent = max_concurrent
        self.test_timeout = test_timeout

        if default_proxies:
            self._load_from_list(default_proxies)

    @classmethod
    def from_yaml(
        cls,
        config_file: str,
        max_concurrent: int = 10,
        test_timeout: float = 5.0
    ) -> "ProxyManager":
        """从 YAML 配置文件加载代理

        Args:
            config_file: YAML 配置文件路径
            max_concurrent: 并发测试的最大代理数
            test_timeout: 测试超时时间（秒）

        Returns:
            ProxyManager 实例
        """
        manager = cls(max_concurrent=max_concurrent, test_timeout=test_timeout)
        manager._load_from_yaml(config_file)
        return manager

    def _load_from_list(self, proxies_list: List[Dict]):
        """从列表加载代理"""
        for proxy_dict in proxies_list:
            self.proxies.append(ProxyInfo(
                name=proxy_dict.get("name", "Unknown"),
                host=proxy_dict.get("host", "127.0.0.1"),
                port=proxy_dict.get("port", 7890),
                proxy_type=proxy_dict.get("type", "http")
            ))

        self.logger.info(f"加载了 {len(self.proxies)} 个代理")

    def _load_from_yaml(self, config_file: str):
        """从 YAML 配置文件加载代理"""
        config_path = Path(config_file)

        if not config_path.exists():
            self.logger.warning(f"配置文件不存在: {config_file}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            proxies_list = config.get('proxies', [])
            self.logger.info(f"从配置文件加载了 {len(proxies_list)} 个代理")

            # 提取有效代理
            for proxy in proxies_list:
                if isinstance(proxy, dict):
                    name = proxy.get('name', 'Unknown')
                    server = proxy.get('server')
                    port = proxy.get('port')

                    if server and port:
                        self.proxies.append(ProxyInfo(
                            name=name,
                            host=server,
                            port=port,
                            proxy_type=proxy.get('type', 'http')
                        ))

            self.logger.info(f"解析出 {len(self.proxies)} 个可用代理")

        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")

    def test_proxy_latency(self, proxy_info: ProxyInfo) -> Tuple[float, bool]:
        """测试单个代理的延迟

        使用 TCP 连接测试 + HTTP 请求测试，返回更准确的延迟。

        Args:
            proxy_info: 代理信息

        Returns:
            (延迟毫秒, 是否成功)
        """
        name = proxy_info.name
        host = proxy_info.host
        port = proxy_info.port

        # 步骤1: 测试 TCP 连接延迟
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.test_timeout)
            sock.connect((host, port))
            sock.close()

            tcp_latency = (time.time() - start_time) * 1000  # 转换为毫秒

        except Exception as e:
            proxy_info.fail_count += 1
            proxy_info.last_check = time.time()
            return 9999.0, False

        # 步骤2: 测试 HTTP 请求延迟
        try:
            proxies_dict = {
                'http': proxy_info.proxy_url,
                'https': proxy_info.proxy_url
            }

            http_start = time.time()
            response = requests.get(
                self.TEST_URLS[0],
                proxies=proxies_dict,
                timeout=self.test_timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            http_latency = (time.time() - http_start) * 1000

            if response.status_code == 200:
                proxy_info.latency = http_latency
                proxy_info.last_check = time.time()
                return http_latency, True
            else:
                return tcp_latency, True

        except Exception:
            # TCP 连接成功但 HTTP 请求失败，返回 TCP 延迟
            proxy_info.latency = tcp_latency
            proxy_info.last_check = time.time()
            return tcp_latency, True

    def select_best_proxy(self, max_concurrent: int = None) -> Optional[ProxyInfo]:
        """并发测试所有代理，选择延迟最低的

        Args:
            max_concurrent: 并发测试的最大代理数（默认使用初始化时的值）

        Returns:
            最佳代理信息，如果全部失败则返回 None
        """
        if not self.proxies:
            self.logger.warning("没有可用的代理")
            return None

        max_workers = max_concurrent or self.max_concurrent
        test_proxies = self.proxies[:max_workers]

        self.logger.info(f"开始测试 {len(test_proxies)} 个代理的延迟...")

        best_proxy = None
        best_latency = 9999.0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {
                executor.submit(self.test_proxy_latency, proxy): proxy
                for proxy in test_proxies
            }

            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    latency, success = future.result()
                    if success and latency < best_latency:
                        best_latency = latency
                        best_proxy = proxy
                        self.logger.info(f"  OK {proxy.name}: {latency:.0f}ms")
                except Exception as e:
                    self.logger.warning(f"  FAIL {proxy.name}: {e}")

        if best_proxy:
            self.logger.info(f"选择最佳代理: {best_proxy.name} ({best_proxy.latency:.0f}ms)")
            return best_proxy
        else:
            self.logger.warning("所有代理测试失败")
            return None

    def record_success(self, proxy_info: ProxyInfo):
        """记录下载成功"""
        proxy_info.success_count += 1
        self.logger.debug(f"{proxy_info.name} 成功: {proxy_info.success_rate:.1f}%")

    def record_failure(self, proxy_info: ProxyInfo):
        """记录下载失败"""
        proxy_info.fail_count += 1
        self.logger.debug(f"{proxy_info.name} 失败: {proxy_info.success_rate:.1f}%")

    def get_stats(self) -> List[Dict]:
        """获取所有代理的统计信息"""
        return [proxy.to_dict() for proxy in self.proxies]

    def get_best_by_stats(self) -> Optional[ProxyInfo]:
        """根据历史统计选择最佳代理

        优先选择成功率高的代理，延迟作为次要指标。
        """
        if not self.proxies:
            return None

        # 过滤有使用记录的代理
        used_proxies = [p for p in self.proxies if p.success_count + p.fail_count > 0]

        if not used_proxies:
            # 如果没有使用记录，返回第一个
            return self.proxies[0]

        # 按成功率和延迟排序
        sorted_proxies = sorted(
            used_proxies,
            key=lambda p: (-p.success_rate, p.latency)
        )

        return sorted_proxies[0]


def create_default_proxy_manager() -> ProxyManager:
    """创建默认代理管理器（使用本地 Mihomo）"""
    default_proxies = [
        {
            "name": "Mihomo",
            "host": "127.0.0.1",
            "port": 7890
        }
    ]
    return ProxyManager(default_proxies=default_proxies)
