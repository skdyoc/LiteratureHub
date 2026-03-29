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
PPT 版本控制

管理 PPT 文件的版本历史、对比和回滚。
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import shutil
import hashlib


class VersionControl:
    """PPT 版本控制系统

    提供完整的版本管理功能，包括版本保存、对比、回滚等。

    用法：
    ```python
    vc = VersionControl(project_id="project_001")

    # 保存新版本
    version_id = vc.save_version(
        ppt_path="output/presentation.pptx",
        message="添加了创新点分析",
        author="User"
    )

    # 列出所有版本
    versions = vc.list_versions()

    # 对比两个版本
    diff = vc.compare_versions(version_id_1, version_id_2)

    # 回滚到指定版本
    vc.rollback(version_id="v1.2", output_path="output/restored.pptx")

    # 获取版本统计
    stats = vc.get_version_statistics()
    ```
    """

    def __init__(self, project_id: str, version_dir: str = "data/versions"):
        """初始化版本控制系统

        Args:
            project_id: 项目 ID
            version_dir: 版本存储目录
        """
        self.project_id = project_id
        self.version_dir = Path(version_dir) / project_id
        self.version_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 版本注册表
        self.versions_file = self.version_dir / "versions.json"
        self.versions: Dict[str, Dict[str, Any]] = self._load_versions()

    def _load_versions(self) -> Dict[str, Dict[str, Any]]:
        """加载版本注册表

        Returns:
            版本字典
        """
        if self.versions_file.exists():
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_versions(self):
        """保存版本注册表"""
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            json.dump(self.versions, f, ensure_ascii=False, indent=2)

    def save_version(
        self,
        ppt_path: str,
        message: str = "",
        author: str = "Unknown",
        tags: List[str] = None
    ) -> str:
        """保存新版本

        Args:
            ppt_path: PPT 文件路径
            message: 版本说明
            author: 作者
            tags: 标签列表

        Returns:
            版本 ID
        """
        ppt_file = Path(ppt_path)
        if not ppt_file.exists():
            raise FileNotFoundError(f"PPT 文件不存在: {ppt_path}")

        # 生成版本 ID
        timestamp = datetime.now()
        version_id = f"v{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 计算文件哈希
        file_hash = self._calculate_file_hash(ppt_file)

        # 复制文件到版本目录
        version_file = self.version_dir / f"{version_id}.pptx"
        shutil.copy2(ppt_file, version_file)

        # 记录版本信息
        self.versions[version_id] = {
            "version_id": version_id,
            "timestamp": timestamp.isoformat(),
            "message": message,
            "author": author,
            "tags": tags or [],
            "file_hash": file_hash,
            "file_size": ppt_file.stat().st_size,
            "ppt_path": str(version_file)
        }

        # 保存版本注册表
        self._save_versions()

        self.logger.info(f"版本已保存: {version_id} - {message}")
        return version_id

    def list_versions(
        self,
        limit: int = None,
        author: str = None,
        tag: str = None
    ) -> List[Dict[str, Any]]:
        """列出所有版本

        Args:
            limit: 限制数量
            author: 按作者筛选
            tag: 按标签筛选

        Returns:
            版本列表
        """
        versions = list(self.versions.values())

        # 筛选
        if author:
            versions = [v for v in versions if v.get("author") == author]

        if tag:
            versions = [v for v in versions if tag in v.get("tags", [])]

        # 按时间降序排序
        versions.sort(key=lambda x: x["timestamp"], reverse=True)

        # 限制数量
        if limit:
            versions = versions[:limit]

        return versions

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """获取版本信息

        Args:
            version_id: 版本 ID

        Returns:
            版本信息
        """
        return self.versions.get(version_id)

    def rollback(
        self,
        version_id: str,
        output_path: str,
        create_backup: bool = True
    ) -> bool:
        """回滚到指定版本

        Args:
            version_id: 版本 ID
            output_path: 输出路径
            create_backup: 是否创建当前版本的备份

        Returns:
            是否成功
        """
        version_info = self.get_version(version_id)
        if not version_info:
            self.logger.error(f"版本不存在: {version_id}")
            return False

        version_file = Path(version_info["ppt_path"])
        if not version_file.exists():
            self.logger.error(f"版本文件不存在: {version_file}")
            return False

        output_file = Path(output_path)

        # 创建备份
        if create_backup and output_file.exists():
            backup_id = self.save_version(
                str(output_file),
                message=f"回滚前自动备份",
                author="System"
            )
            self.logger.info(f"已创建备份: {backup_id}")

        # 复制版本文件
        shutil.copy2(version_file, output_file)

        self.logger.info(f"已回滚到版本: {version_id}")
        return True

    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """对比两个版本

        Args:
            version_id_1: 版本 1 ID
            version_id_2: 版本 2 ID

        Returns:
            对比结果
        """
        version_1 = self.get_version(version_id_1)
        version_2 = self.get_version(version_id_2)

        if not version_1 or not version_2:
            raise ValueError("一个或多个版本不存在")

        result = {
            "version_1": version_id_1,
            "version_2": version_id_2,
            "timestamp_diff": None,
            "size_diff": 0,
            "hash_match": False,
            "author_diff": None,
            "changes": []
        }

        # 时间差异
        time_1 = datetime.fromisoformat(version_1["timestamp"])
        time_2 = datetime.fromisoformat(version_2["timestamp"])
        result["timestamp_diff"] = str(time_2 - time_1)

        # 大小差异
        result["size_diff"] = version_2["file_size"] - version_1["file_size"]

        # 哈希匹配
        result["hash_match"] = version_1["file_hash"] == version_2["file_hash"]

        # 作者差异
        if version_1["author"] != version_2["author"]:
            result["author_diff"] = {
                "from": version_1["author"],
                "to": version_2["author"]
            }

        # 标签变化
        tags_1 = set(version_1.get("tags", []))
        tags_2 = set(version_2.get("tags", []))

        if tags_1 != tags_2:
            result["changes"].append({
                "type": "tags",
                "added": list(tags_2 - tags_1),
                "removed": list(tags_1 - tags_2)
            })

        return result

    def delete_version(self, version_id: str) -> bool:
        """删除版本

        Args:
            version_id: 版本 ID

        Returns:
            是否成功
        """
        version_info = self.get_version(version_id)
        if not version_info:
            self.logger.error(f"版本不存在: {version_id}")
            return False

        # 删除版本文件
        version_file = Path(version_info["ppt_path"])
        if version_file.exists():
            version_file.unlink()

        # 从注册表移除
        del self.versions[version_id]
        self._save_versions()

        self.logger.info(f"版本已删除: {version_id}")
        return True

    def add_tag(self, version_id: str, tag: str) -> bool:
        """添加标签

        Args:
            version_id: 版本 ID
            tag: 标签

        Returns:
            是否成功
        """
        version_info = self.get_version(version_id)
        if not version_info:
            return False

        if tag not in version_info["tags"]:
            version_info["tags"].append(tag)
            self._save_versions()

        return True

    def remove_tag(self, version_id: str, tag: str) -> bool:
        """移除标签

        Args:
            version_id: 版本 ID
            tag: 标签

        Returns:
            是否成功
        """
        version_info = self.get_version(version_id)
        if not version_info:
            return False

        if tag in version_info["tags"]:
            version_info["tags"].remove(tag)
            self._save_versions()

        return True

    def get_latest_version(self) -> Optional[Dict[str, Any]]:
        """获取最新版本

        Returns:
            最新版本信息
        """
        if not self.versions:
            return None

        latest = max(
            self.versions.values(),
            key=lambda x: x["timestamp"]
        )

        return latest

    def get_version_statistics(self) -> Dict[str, Any]:
        """获取版本统计信息

        Returns:
            统计信息
        """
        if not self.versions:
            return {
                "total_versions": 0,
                "total_size": 0,
                "first_version": None,
                "latest_version": None,
                "authors": [],
                "tags": []
            }

        total_size = sum(v["file_size"] for v in self.versions.values())

        authors = list(set(v["author"] for v in self.versions.values()))

        all_tags = []
        for v in self.versions.values():
            all_tags.extend(v.get("tags", []))
        tags = list(set(all_tags))

        timestamps = [v["timestamp"] for v in self.versions.values()]
        first_version = min(timestamps)
        latest_version = max(timestamps)

        return {
            "total_versions": len(self.versions),
            "total_size": total_size,
            "first_version": first_version,
            "latest_version": latest_version,
            "authors": authors,
            "tags": tags,
            "average_size": total_size / len(self.versions) if self.versions else 0
        }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希值
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def cleanup_old_versions(
        self,
        keep_count: int = 10,
        keep_tags: List[str] = None
    ) -> int:
        """清理旧版本

        Args:
            keep_count: 保留的版本数量
            keep_tags: 要保留的标签

        Returns:
            删除的版本数量
        """
        if len(self.versions) <= keep_count:
            return 0

        # 按时间排序
        sorted_versions = sorted(
            self.versions.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        )

        # 确定要删除的版本
        to_delete = []
        for i, (version_id, version_info) in enumerate(sorted_versions):
            if i < keep_count:
                # 保留前 keep_count 个
                continue

            # 检查标签
            if keep_tags and any(tag in version_info.get("tags", []) for tag in keep_tags):
                continue

            to_delete.append(version_id)

        # 删除版本
        for version_id in to_delete:
            self.delete_version(version_id)

        self.logger.info(f"已清理 {len(to_delete)} 个旧版本")
        return len(to_delete)

    def export_version_history(self, output_path: str) -> bool:
        """导出版本历史

        Args:
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            export_data = {
                "project_id": self.project_id,
                "exported_at": datetime.now().isoformat(),
                "versions": list(self.versions.values())
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"版本历史已导出: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            return False
