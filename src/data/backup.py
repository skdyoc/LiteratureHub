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
备份管理器

提供数据备份和恢复功能。
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List


class BackupManager:
    """备份管理器

    管理项目和数据库的备份。

    使用示例：
    ```python
    backup_mgr = BackupManager("data/backups")

    # 创建备份
    backup_path = backup_mgr.create_backup("data/projects", "daily_backup")

    # 恢复备份
    backup_mgr.restore_backup(backup_path, "data/projects")

    # 列出所有备份
    backups = backup_mgr.list_backups()
    ```
    """

    def __init__(self, backup_dir: str = "data/backups"):
        """初始化备份管理器

        Args:
            backup_dir: 备份目录
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def create_backup(
        self,
        source_path: str,
        backup_name: str = None,
        compress: bool = False
    ) -> Path:
        """创建备份

        Args:
            source_path: 源路径
            backup_name: 备份名称
            compress: 是否压缩（暂未实现）

        Returns:
            备份路径
        """
        import shutil

        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        source = Path(source_path)
        target = self.backup_dir / backup_name

        if not source.exists():
            raise FileNotFoundError(f"源路径不存在: {source_path}")

        if target.exists():
            shutil.rmtree(target)

        shutil.copytree(source, target)

        self.logger.info(f"备份创建成功: {source} -> {target}")
        return target

    def restore_backup(self, backup_path: str, target_path: str):
        """恢复备份

        Args:
            backup_path: 备份路径
            target_path: 目标路径
        """
        import shutil

        backup = Path(backup_path)
        target = Path(target_path)

        if not backup.exists():
            raise FileNotFoundError(f"备份不存在: {backup_path}")

        if target.exists():
            shutil.rmtree(target)

        shutil.copytree(backup, target)

        self.logger.info(f"备份恢复成功: {backup} -> {target}")

    def list_backups(self) -> List[dict]:
        """列出所有备份

        Returns:
            备份列表
        """
        backups = []

        for backup in self.backup_dir.iterdir():
            if backup.is_dir():
                stat = backup.stat()
                backups.append({
                    "name": backup.name,
                    "path": str(backup),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size": self._get_dir_size(backup)
                })

        # 按时间倒序排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return backups

    def delete_backup(self, backup_name: str) -> bool:
        """删除备份

        Args:
            backup_name: 备份名称

        Returns:
            是否成功
        """
        import shutil

        backup_path = self.backup_dir / backup_name

        if backup_path.exists():
            shutil.rmtree(backup_path)
            self.logger.info(f"备份删除成功: {backup_path}")
            return True

        return False

    def _get_dir_size(self, path: Path) -> int:
        """获取目录大小（字节）"""
        total_size = 0
        for file in path.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return total_size

    def clean_old_backups(self, keep_count: int = 10):
        """清理旧备份

        Args:
            keep_count: 保留数量
        """
        backups = self.list_backups()

        if len(backups) > keep_count:
            for backup in backups[keep_count:]:
                self.delete_backup(backup["name"])

            self.logger.info(f"清理了 {len(backups) - keep_count} 个旧备份")
