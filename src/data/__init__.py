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
数据层模块

提供统一的数据管理接口，包括：
- 数据库管理（SQLite）
- 文件管理（PDF、Markdown、JSON）
- 缓存系统（避免重复 API 调用）
- 迁移管理（数据库版本控制）
- 备份管理（数据备份与恢复）
"""

from .manager import DatabaseManager
from .file_manager import FileManager
from .cache import CacheSystem
from .migration import MigrationManager
from .backup import BackupManager

__all__ = [
    'DatabaseManager',
    'FileManager',
    'CacheSystem',
    'MigrationManager',
    'BackupManager',
]
