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
状态追踪器

持久化保存工作流状态，支持断点续传。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StateTracker:
    """状态追踪器

    负责持久化保存和恢复工作流状态。

    使用示例：
    ```python
    tracker = StateTracker("data/projects/project_001")

    # 保存任务状态
    tracker.save_task_state("search", {
        "status": "completed",
        "result": {...}
    })

    # 恢复工作流
    pending_tasks = tracker.get_pending_tasks()

    # 保存检查点
    tracker.save_checkpoint()
    ```
    """

    def __init__(self, project_path: str = "data/projects"):
        """初始化状态追踪器

        Args:
            project_path: 项目路径
        """
        self.project_path = Path(project_path)
        self.project_path.mkdir(parents=True, exist_ok=True)

        self.state_file = self.project_path / "workflow_state.json"
        self.checkpoint_dir = self.project_path / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 加载状态
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载工作流状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "tasks": {},
            "workflow_history": [],
            "current_phase": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": None
        }

    def _save_state(self):
        """保存工作流状态"""
        self.state["updated_at"] = datetime.now().isoformat()

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def save_task_state(self, task_id: str, task_state: Dict[str, Any]):
        """保存任务状态

        Args:
            task_id: 任务 ID
            task_state: 任务状态数据
        """
        # 添加时间戳
        task_state["timestamp"] = datetime.now().isoformat()

        # 保存任务状态
        self.state["tasks"][task_id] = task_state

        # 添加到历史记录
        self.state["workflow_history"].append({
            "task_id": task_id,
            "status": task_state.get("status"),
            "timestamp": task_state["timestamp"]
        })

        self._save_state()
        self.logger.info(f"任务状态已保存: {task_id} - {task_state.get('status')}")

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态数据
        """
        return self.state["tasks"].get(task_id)

    def get_pending_tasks(self) -> List[str]:
        """获取待执行的任务列表

        Returns:
            待执行任务 ID 列表
        """
        pending = []

        for task_id, task_state in self.state["tasks"].items():
            if task_state.get("status") in [TaskStatus.PENDING.value, TaskStatus.FAILED.value]:
                pending.append(task_id)

        return pending

    def get_completed_tasks(self) -> List[str]:
        """获取已完成的任务列表

        Returns:
            已完成任务 ID 列表
        """
        completed = []

        for task_id, task_state in self.state["tasks"].items():
            if task_state.get("status") == TaskStatus.COMPLETED.value:
                completed.append(task_id)

        return completed

    def save_checkpoint(self, checkpoint_name: str = None):
        """保存检查点

        Args:
            checkpoint_name: 检查点名称（可选）
        """
        if not checkpoint_name:
            checkpoint_name = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        # 复制当前状态
        checkpoint_data = {
            "state": self.state,
            "checkpoint_name": checkpoint_name,
            "created_at": datetime.now().isoformat()
        }

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"检查点已保存: {checkpoint_name}")

    def restore_checkpoint(self, checkpoint_name: str) -> bool:
        """恢复检查点

        Args:
            checkpoint_name: 检查点名称

        Returns:
            是否成功
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        if not checkpoint_file.exists():
            self.logger.error(f"检查点不存在: {checkpoint_name}")
            return False

        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)

        self.state = checkpoint_data["state"]
        self._save_state()

        self.logger.info(f"检查点已恢复: {checkpoint_name}")
        return True

    def list_checkpoints(self) -> List[Dict[str, str]]:
        """列出所有检查点

        Returns:
            检查点列表
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            checkpoints.append({
                "name": data["checkpoint_name"],
                "created_at": data["created_at"],
                "file": str(checkpoint_file)
            })

        # 按时间排序
        checkpoints.sort(key=lambda x: x["created_at"], reverse=True)

        return checkpoints

    def set_current_phase(self, phase: str):
        """设置当前阶段

        Args:
            phase: 阶段名称
        """
        self.state["current_phase"] = phase
        self._save_state()
        self.logger.info(f"当前阶段: {phase}")

    def get_current_phase(self) -> Optional[str]:
        """获取当前阶段

        Returns:
            当前阶段名称
        """
        return self.state.get("current_phase")

    def get_workflow_stats(self) -> Dict[str, int]:
        """获取工作流统计

        Returns:
            统计信息
        """
        stats = {
            "total_tasks": len(self.state["tasks"]),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }

        for task_state in self.state["tasks"].values():
            status = task_state.get("status")
            if status in stats:
                stats[status] += 1

        return stats

    def clear_history(self):
        """清空历史记录"""
        self.state["workflow_history"] = []
        self._save_state()
        self.logger.info("历史记录已清空")

    def reset(self):
        """重置所有状态"""
        self.state = {
            "tasks": {},
            "workflow_history": [],
            "current_phase": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": None
        }
        self._save_state()
        self.logger.info("状态追踪器已重置")
