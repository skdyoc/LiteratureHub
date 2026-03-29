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
增量更新器

智能识别需要更新的部分，避免全量重新计算。
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from datetime import datetime


class IncrementalUpdater:
    """增量更新器

    根据文件变化和依赖关系，智能识别需要更新的部分。

    使用示例：
    ```python
    updater = IncrementalUpdater("data/projects")

    # 检测变化
    changes = updater.detect_changes()

    # 获取需要更新的文献
    papers_to_update = updater.get_papers_to_update()

    # 更新完成后记录
    updater.mark_updated(paper_ids)
    ```
    """

    def __init__(self, project_root: str = "data/projects"):
        """初始化增量更新器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.project_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.project_root / "update_state.json"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 加载状态
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载更新状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "file_hashes": {},
            "paper_status": {},
            "last_update": None
        }

    def _save_state(self):
        """保存更新状态"""
        self.state["last_update"] = datetime.now().isoformat()

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def detect_changes(self, directory: str = None) -> Dict[str, List[str]]:
        """检测文件变化

        Args:
            directory: 要检测的目录（默认为项目根目录）

        Returns:
            变化文件字典：{
                "added": [...],
                "modified": [...],
                "deleted": [...]
            }
        """
        target_dir = Path(directory) if directory else self.project_root

        changes = {
            "added": [],
            "modified": [],
            "deleted": []
        }

        # 当前文件哈希
        current_hashes = {}

        # 扫描所有文件
        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.pdf', '.md', '.json']:
                file_hash = self._calculate_file_hash(file_path)
                relative_path = str(file_path.relative_to(self.project_root))
                current_hashes[relative_path] = file_hash

                # 检查是否新增或修改
                if relative_path not in self.state["file_hashes"]:
                    changes["added"].append(relative_path)
                elif self.state["file_hashes"][relative_path] != file_hash:
                    changes["modified"].append(relative_path)

        # 检查删除的文件
        for relative_path in self.state["file_hashes"]:
            if relative_path not in current_hashes:
                changes["deleted"].append(relative_path)

        # 更新哈希
        self.state["file_hashes"].update(current_hashes)

        # 移除已删除的文件
        for deleted_file in changes["deleted"]:
            self.state["file_hashes"].pop(deleted_file, None)

        self.logger.info(f"检测到变化: {len(changes['added'])} 新增, "
                        f"{len(changes['modified'])} 修改, "
                        f"{len(changes['deleted'])} 删除")

        return changes

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值

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

    def get_papers_to_update(self) -> List[str]:
        """获取需要更新的文献 ID 列表

        Returns:
            需要更新的文献 ID 列表
        """
        to_update = []

        for paper_id, status in self.state["paper_status"].items():
            # 如果文献未分析，或者标记为需要重新分析
            if status.get("status") in ["pending", "needs_update"]:
                to_update.append(paper_id)

        return to_update

    def mark_paper_needs_update(self, paper_id: str, reason: str = ""):
        """标记文献需要更新

        Args:
            paper_id: 文献 ID
            reason: 原因
        """
        self.state["paper_status"][paper_id] = {
            "status": "needs_update",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self._save_state()

        self.logger.info(f"标记文献需要更新: {paper_id} - {reason}")

    def mark_updated(self, paper_ids: List[str]):
        """标记文献已更新

        Args:
            paper_ids: 文献 ID 列表
        """
        for paper_id in paper_ids:
            self.state["paper_status"][paper_id] = {
                "status": "updated",
                "timestamp": datetime.now().isoformat()
            }

        self._save_state()
        self.logger.info(f"标记 {len(paper_ids)} 篇文献已更新")

    def get_analysis_dependencies(self, paper_id: str) -> Set[str]:
        """获取文献分析依赖

        Args:
            paper_id: 文献 ID

        Returns:
            依赖的文献 ID 集合
        """
        # 读取文献元数据
        metadata_path = self.project_root / "json" / paper_id / "metadata.json"

        if not metadata_path.exists():
            return set()

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # 提取引用文献
        dependencies = set()
        for reference in metadata.get("references", []):
            if "doi" in reference:
                dependencies.add(reference["doi"])

        return dependencies

    def propagate_updates(self, changed_paper_id: str) -> List[str]:
        """传播更新（级联更新依赖的文献）

        Args:
            changed_paper_id: 发生变化的文献 ID

        Returns:
            需要级联更新的文献 ID 列表
        """
        to_update = []

        # 查找所有依赖此文献的其他文献
        for paper_id, status in self.state["paper_status"].items():
            if paper_id == changed_paper_id:
                continue

            # 检查依赖关系
            dependencies = self.get_analysis_dependencies(paper_id)

            if changed_paper_id in dependencies:
                # 标记需要重新分析
                self.mark_paper_needs_update(paper_id, f"依赖文献 {changed_paper_id} 已更新")
                to_update.append(paper_id)

        self.logger.info(f"级联更新: {len(to_update)} 篇文献需要重新分析")
        return to_update

    def get_incremental_stats(self) -> Dict[str, int]:
        """获取增量更新统计

        Returns:
            统计信息
        """
        total_papers = len(self.state["paper_status"])
        pending = sum(1 for s in self.state["paper_status"].values()
                     if s.get("status") == "pending")
        needs_update = sum(1 for s in self.state["paper_status"].values()
                          if s.get("status") == "needs_update")
        updated = sum(1 for s in self.state["paper_status"].values()
                     if s.get("status") == "updated")

        return {
            "total_papers": total_papers,
            "pending": pending,
            "needs_update": needs_update,
            "updated": updated,
            "files_tracked": len(self.state["file_hashes"])
        }

    def reset(self):
        """重置所有状态"""
        self.state = {
            "file_hashes": {},
            "paper_status": {},
            "last_update": None
        }
        self._save_state()
        self.logger.info("增量更新器已重置")
