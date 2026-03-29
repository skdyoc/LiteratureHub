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
VPN 检测器

自动检测用户系统中的 VPN 代理配置。
支持 Mihomo/Clash、V2Ray、Shadowsocks 等。
"""

import logging
import requests
import time
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml


@dataclass
class ProxyInfo:
    """代理信息"""
    proxy_type: str
    host: str
    port: int
    proxy_url: str
    config_path: Optional[str] = None
    executable: Optional[str] = None
    latency: float = 0.0


class VPNDetector:
    """VPN 自动检测器

    自动检测用户使用的 VPN 软件并获取代理配置。

    用法：
    ```python
    detector = VPNDetector()
    proxy = detector.detect()
    if proxy:
        print(f"检测到代理: {proxy.proxy_url}")
    ```
    """

    # 常见 VPN 软件配置
    VPN_CONFIGS = {
        "mihomo": {
            "executable": "D:/mihomo/mihomo.exe",
            "config": "D:/mihomo/config.yaml",
            "default_port": 7890
        },
        "clash": {
            "executable": "C:/Program Files/Clash/clash.exe",
            "config": None,
            "default_port": 7890
        },
        "v2ray": {
            "executable": "C:/Program Files/v2ray/v2ray.exe",
            "config": None,
            "default_port": 10808
        },
        "shadowsocks": {
            "executable": None,
            "config": None,
            "default_port": 1080
        }
    }

    # 测试 URL
    TEST_URLS = [
        "https://www.google.com",
        "https://www.github.com",
        "https://sci-hub.se"
    ]

    def __init__(self):
        """初始化检测器"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.detected_proxy: Optional[ProxyInfo] = None

    def detect(self) -> Optional[ProxyInfo]:
        """
        自动检测 VPN 代理

        Returns:
            代理信息，如果检测失败则返回 None
        """
        self.logger.info("开始检测 VPN 代理...")

        # 1. 检测 Mihomo
        proxy = self._detect_mihomo()
        if proxy:
            self.detected_proxy = proxy
            return proxy

        # 2. 检测系统代理
        proxy = self._detect_system_proxy()
        if proxy:
            self.detected_proxy = proxy
            return proxy

        # 3. 尝试常见端口
        proxy = self._detect_common_ports()
        if proxy:
            self.detected_proxy = proxy
            return proxy

        self.logger.warning("未检测到可用的 VPN 代理")
        return None

    def _detect_mihomo(self) -> Optional[ProxyInfo]:
        """检测 Mihomo 代理"""
        mihomo_config = self.VPN_CONFIGS["mihomo"]

        # 检查可执行文件是否存在
        exe_path = Path(mihomo_config["executable"])
        if not exe_path.exists():
            self.logger.debug(f"Mihomo 可执行文件不存在: {exe_path}")
            return None

        # 读取配置文件获取端口
        config_path = Path(mihomo_config["config"])
        port = mihomo_config["default_port"]

        if config_path.exists():
            try:
                port = self._read_mihomo_port(config_path)
                self.logger.info(f"从配置文件读取端口: {port}")
            except Exception as e:
                self.logger.warning(f"读取配置文件失败: {e}")

        proxy_url = f"http://127.0.0.1:{port}"

        # 测试代理
        if self._test_proxy(proxy_url):
            return ProxyInfo(
                proxy_type="mihomo",
                host="127.0.0.1",
                port=port,
                proxy_url=proxy_url,
                config_path=str(config_path),
                executable=str(exe_path)
            )

        return None

    def _read_mihomo_port(self, config_path: Path) -> int:
        """读取 Mihomo 配置文件中的端口"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 尝试获取 mixed-port 或 port
        port = config.get("mixed-port") or config.get("port") or 7890
        return int(port)

    def _detect_system_proxy(self) -> Optional[ProxyInfo]:
        """检测系统代理设置"""
        import os

        # 检查环境变量
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        if http_proxy or https_proxy:
            proxy_url = https_proxy or http_proxy

            # 解析代理 URL
            if proxy_url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(proxy_url)
                    host = parsed.hostname or "127.0.0.1"
                    port = parsed.port or 7890

                    if self._test_proxy(proxy_url):
                        return ProxyInfo(
                            proxy_type="system",
                            host=host,
                            port=port,
                            proxy_url=proxy_url
                        )
                except Exception as e:
                    self.logger.warning(f"解析代理 URL 失败: {e}")

        return None

    def _detect_common_ports(self) -> Optional[ProxyInfo]:
        """检测常见代理端口"""
        common_ports = [7890, 10808, 1080, 8080, 10809]

        for port in common_ports:
            proxy_url = f"http://127.0.0.1:{port}"

            if self._test_proxy(proxy_url):
                self.logger.info(f"检测到代理端口: {port}")
                return ProxyInfo(
                    proxy_type="unknown",
                    host="127.0.0.1",
                    port=port,
                    proxy_url=proxy_url
                )

        return None

    def _test_proxy(self, proxy_url: str, timeout: float = 5.0) -> bool:
        """测试代理是否可用"""
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        for test_url in self.TEST_URLS:
            try:
                start_time = time.time()
                response = requests.get(
                    test_url,
                    proxies=proxies,
                    timeout=timeout,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                latency = time.time() - start_time

                if response.status_code == 200:
                    self.logger.info(f"代理测试成功: {proxy_url} (延迟: {latency:.2f}s)")
                    return True

            except requests.exceptions.RequestException:
                continue

        return False

    def start_mihomo(self) -> bool:
        """启动 Mihomo 代理

        Returns:
            是否启动成功
        """
        mihomo_exe = Path("D:/mihomo/mihomo.exe")

        if not mihomo_exe.exists():
            self.logger.error(f"Mihomo 可执行文件不存在: {mihomo_exe}")
            return False

        # 检查是否已经在运行
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if 'mihomo' in proc.info['name'].lower():
                    self.logger.info("Mihomo 已经在运行")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 查找配置文件
        config_dir = Path("C:/Users/19874/.config/clash/profiles")
        config_files = list(config_dir.glob("*.yml")) + list(config_dir.glob("*.yaml")) if config_dir.exists() else []

        if not config_files:
            self.logger.error("未找到 Mihomo 配置文件")
            return False

        config_file = config_files[0]  # 使用最新的配置文件
        self.logger.info(f"使用配置文件: {config_file}")

        # 启动 Mihomo
        try:
            subprocess.Popen(
                [str(mihomo_exe), "-f", str(config_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.logger.info("Mihomo 启动命令已执行")

            # 等待代理启动
            for i in range(10):
                time.sleep(1)
                if self._test_proxy("http://127.0.0.1:7890", timeout=2):
                    self.logger.info("Mihomo 代理已就绪")
                    return True
                self.logger.debug(f"等待 Mihomo 启动... ({i+1}/10)")

            self.logger.warning("Mihomo 启动超时，可能需要手动检查")
            return False

        except Exception as e:
            self.logger.error(f"启动 Mihomo 失败: {e}")
            return False

    def ensure_proxy_running(self) -> Optional[ProxyInfo]:
        """确保代理正在运行

        检测代理，如果没有运行则尝试启动 Mihomo

        Returns:
            代理信息，失败返回 None
        """
        # 先尝试检测现有代理
        proxy = self.detect()
        if proxy:
            return proxy

        # 没有检测到代理，尝试启动 Mihomo
        self.logger.info("未检测到代理，尝试启动 Mihomo...")
        if self.start_mihomo():
            # 重新检测代理
            proxy = self.detect()
            if proxy:
                return proxy

        self.logger.error("无法启动代理服务")
        return None

    def get_available_proxies(self) -> List[ProxyInfo]:
        """
        获取所有可用的代理

        Returns:
            代理列表
        """
        proxies = []

        # 检测 Mihomo
        mihomo_proxy = self._detect_mihomo()
        if mihomo_proxy:
            proxies.append(mihomo_proxy)

        # 检测常见端口
        common_ports = [7890, 10808, 1080, 8080, 10809]
        for port in common_ports:
            proxy_url = f"http://127.0.0.1:{port}"

            # 跳过已检测的
            if any(p.port == port for p in proxies):
                continue

            if self._test_proxy(proxy_url):
                proxies.append(ProxyInfo(
                    proxy_type="unknown",
                    host="127.0.0.1",
                    port=port,
                    proxy_url=proxy_url
                ))

        return proxies

    def test_proxy_latency(self, proxy_url: str, test_url: str = None) -> float:
        """
        测试代理延迟

        Args:
            proxy_url: 代理 URL
            test_url: 测试 URL

        Returns:
            延迟（秒），失败返回 -1
        """
        test_url = test_url or self.TEST_URLS[0]
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            latency = time.time() - start_time

            if response.status_code == 200:
                return latency

        except requests.exceptions.RequestException:
            pass

        return -1.0
