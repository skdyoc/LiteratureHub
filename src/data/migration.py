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
数据库迁移管理器

管理数据库版本和迁移脚本。
"""

import logging
from pathlib import Path
from typing import List
from .manager import DatabaseManager


class MigrationManager:
    """迁移管理器

    管理数据库版本控制。

    使用示例：
    ```python
    db = DatabaseManager("data/literature.db")
    migration = MigrationManager(db)

    # 应用所有迁移
    migration.migrate()

    # 回滚到指定版本
    migration.rollback(1)
    ```
    """

    def __init__(self, db_manager: DatabaseManager):
        """初始化迁移管理器

        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 创建迁移表
        self._create_migration_table()

    def _create_migration_table(self):
        """创建迁移记录表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def get_current_version(self) -> int:
        """获取当前数据库版本

        Returns:
            当前版本号
        """
        result = self.db.query('migrations', order_by='version DESC', limit=1)
        return result[0]['version'] if result else 0

    def migrate(self):
        """应用所有待执行的迁移"""
        current_version = self.get_current_version()
        migrations = self._get_pending_migrations(current_version)

        for migration in migrations:
            self._apply_migration(migration)

        self.logger.info(f"迁移完成: {current_version} -> {self.get_current_version()}")

    def _get_pending_migrations(self, current_version: int) -> List[dict]:
        """获取待执行的迁移列表"""
        # 定义迁移脚本
        migrations = [
            {
                "version": 1,
                "name": "initial_schema",
                "sql": """
                    -- 初始表结构已在 DatabaseManager 中创建
                    -- 此迁移仅作为版本标记
                """
            },
            # 可以添加更多迁移
        ]

        return [m for m in migrations if m["version"] > current_version]

    def _apply_migration(self, migration: dict):
        """应用单个迁移"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 执行迁移 SQL
            cursor.executescript(migration["sql"])

            # 记录迁移
            cursor.execute(
                "INSERT INTO migrations (version, name) VALUES (?, ?)",
                (migration["version"], migration["name"])
            )

            conn.commit()
            self.logger.info(f"迁移应用成功: v{migration['version']} - {migration['name']}")

    def rollback(self, target_version: int):
        """回滚到指定版本

        Args:
            target_version: 目标版本号
        """
        current_version = self.get_current_version()

        if target_version >= current_version:
            self.logger.warning("目标版本 >= 当前版本，无需回滚")
            return

        self.logger.warning(f"回滚功能尚未实现: {current_version} -> {target_version}")
