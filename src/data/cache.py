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
缓存系统

提供内存和磁盘缓存，避免重复 API 调用。
"""

import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


class CacheSystem:
    """缓存系统

    支持内存缓存和磁盘缓存。

    用法：
    ```python
    cache = CacheSystem()

    # 设置缓存
    cache.set("api_result_key", {"data": "value"}, ttl=3600)

    # 获取缓存
    result = cache.get("api_result_key")

    # 检查是否存在
    if cache.exists("api_result_key"):
        print("缓存存在")
    ```
    """

    def __init__(self, cache_dir: str = "data/cache", default_ttl: int = 3600):
        """初始化缓存系统

        Args:
            cache_dir: 缓存目录
            default_ttl: 默认过期时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.default_ttl = default_ttl
        self.memory_cache: Dict[str, Any] = {}

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def _generate_key(self, key: str) -> str:
        """生成缓存键（MD5）"""
        return hashlib.md5(key.encode()).hexdigest()

    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        ttl = ttl or self.default_ttl
        cache_key = self._generate_key(key)

        # 内存缓存
        self.memory_cache[cache_key] = {
            "value": value,
            "expire_at": time.time() + ttl
        }

        # 磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.json"
        cache_data = {
            "value": value,
            "expire_at": time.time() + ttl
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)

        self.logger.debug(f"缓存设置: {key}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值（如果存在且未过期）
        """
        cache_key = self._generate_key(key)

        # 先检查内存缓存
        if cache_key in self.memory_cache:
            cache_data = self.memory_cache[cache_key]
            if time.time() < cache_data["expire_at"]:
                return cache_data["value"]
            else:
                del self.memory_cache[cache_key]

        # 检查磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            if time.time() < cache_data["expire_at"]:
                # 加载到内存缓存
                self.memory_cache[cache_key] = cache_data
                return cache_data["value"]
            else:
                # 过期，删除
                cache_file.unlink()

        return None

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在且未过期
        """
        return self.get(key) is not None

    def delete(self, key: str):
        """删除缓存

        Args:
            key: 缓存键
        """
        cache_key = self._generate_key(key)

        # 删除内存缓存
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

        # 删除磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            cache_file.unlink()

        self.logger.debug(f"缓存删除: {key}")

    def clear(self):
        """清空所有缓存"""
        self.memory_cache.clear()

        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

        self.logger.info("所有缓存已清空")

    def cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()

        # 清理内存缓存
        expired_keys = [
            key for key, data in self.memory_cache.items()
            if current_time >= data["expire_at"]
        ]
        for key in expired_keys:
            del self.memory_cache[key]

        # 清理磁盘缓存
        for cache_file in self.cache_dir.glob("*.json"):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            if current_time >= cache_data["expire_at"]:
                cache_file.unlink()

        self.logger.info(f"过期缓存清理完成: {len(expired_keys)} 个")

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计

        Returns:
            统计信息
        """
        memory_count = len(self.memory_cache)
        disk_count = len(list(self.cache_dir.glob("*.json")))

        return {
            "memory_cache_count": memory_count,
            "disk_cache_count": disk_count,
            "total_count": memory_count + disk_count
        }
