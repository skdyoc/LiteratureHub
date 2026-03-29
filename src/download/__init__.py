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
文献下载模块

实现三步下载流程：
1. SciHub 自动下载（VPN 代理）
2. NoteExpress 辅助下载
3. Web of Science 手动下载
"""

from .scihub_downloader import SciHubDownloader
from .download_manager import DownloadManager
from .vpn_detector import VPNDetector

__all__ = [
    "SciHubDownloader",
    "DownloadManager",
    "VPNDetector"
]
