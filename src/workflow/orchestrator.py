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
工作流编排器

协调多个工作流任务，支持依赖管理和并发执行。
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

from .engine import WorkflowEngine
from .state_tracker import StateTracker, TaskStatus
from .incremental_updater import IncrementalUpdater


class WorkflowOrchestrator:
    """工作流编排器

    协调多个工作流任务，支持依赖管理和并发执行。

    用法：
    ```python
    orchestrator = WorkflowOrchestrator()

    # 注册工作流
    orchestrator.register_workflow("search", search_workflow)
    orchestrator.register_workflow("analyze", analyze_workflow)
    orchestrator.register_workflow("generate", ppt_workflow)

    # 设置依赖
    orchestrator.set_dependency("analyze", ["search"])
    orchestrator.set_dependency("generate", ["analyze"])

    # 执行所有工作流
    results = await orchestrator.execute_all()

    # 获取进度
    progress = orchestrator.get_progress()
    ```
    """

    def __init__(self, project_path: str = "data/projects"):
        """初始化工作流编排器

        Args:
            project_path: 项目路径
        """
        self.project_path = project_path
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 工作流注册表
        self.workflows: Dict[str, WorkflowEngine] = {}

        # 依赖关系
        self.dependencies: Dict[str, List[str]] = {}

        # 状态追踪器
        self.state_tracker = StateTracker(project_path)

        # 增量更新器
        self.incremental_updater = IncrementalUpdater(project_path)

        # 进度回调
        self.progress_callbacks: List[Callable] = []

        # 执行结果
        self.execution_results: Dict[str, Any] = {}

    def register_workflow(self, name: str, workflow: WorkflowEngine):
        """注册工作流

        Args:
            name: 工作流名称
            workflow: 工作流引擎实例
        """
        self.workflows[name] = workflow
        self.logger.info(f"工作流已注册: {name}")

        # 初始化状态
        self.state_tracker.save_task_state(name, {
            "status": TaskStatus.PENDING.value,
            "registered_at": datetime.now().isoformat()
        })

    def set_dependency(self, workflow_name: str, depends_on: List[str]):
        """设置工作流依赖

        Args:
            workflow_name: 工作流名称
            depends_on: 依赖的工作流列表
        """
        self.dependencies[workflow_name] = depends_on
        self.logger.info(f"工作流依赖已设置: {workflow_name} -> {depends_on}")

    async def execute_all(self) -> Dict[str, Any]:
        """执行所有工作流

        Returns:
            执行结果字典
        """
        self.logger.info("开始执行所有工作流")

        # 获取执行顺序（拓扑排序）
        execution_order = self._get_execution_order()

        # 按顺序执行
        for workflow_name in execution_order:
            try:
                result = await self._execute_workflow(workflow_name)
                self.execution_results[workflow_name] = result

            except Exception as e:
                self.logger.error(f"工作流执行失败 [{workflow_name}]: {e}")
                self.execution_results[workflow_name] = {
                    "status": "failed",
                    "error": str(e)
                }

        self.logger.info("所有工作流执行完成")
        return self.execution_results

    def _get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）

        Returns:
            执行顺序列表
        """
        # 简单的拓扑排序
        visited = set()
        order = []

        def visit(name: str):
            if name in visited:
                return

            # 先访问依赖
            for dep in self.dependencies.get(name, []):
                visit(dep)

            visited.add(name)
            order.append(name)
        for name in self.workflows.keys():
            visit(name)
        return order
    async def _execute_workflow(self, name: str) -> Dict[str, Any]:
        """执行单个工作流

        Args:
            name: 工作流名称

        Returns:
            执行结果
        """
        self.logger.info(f"开始执行工作流: {name}")
        # 更新状态
        self.state_tracker.save_task_state(name, {
            "status": TaskStatus.RUNNING.value,
            "started_at": datetime.now().isoformat()
        })
        # 通知进度
        self._notify_progress(name, 0, f"开始执行工作流: {name}")
        # 执行工作流
        workflow = self.workflows[name]
        result = await workflow.execute()
        # 更新状态
        self.state_tracker.save_task_state(name, {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": datetime.now().isoformat(),
            "result": result
        })
        # 通知进度
        self._notify_progress(name, 100, f"工作流完成: {name}")
        self.logger.info(f"工作流执行完成: {name}")
        return {
            "status": "completed",
            "result": result
        }
    def _notify_progress(self, workflow_name: str, progress: int, message: str):
        """通知进度

        Args:
            workflow_name: 工作流名称
            progress: 进度（0-100）
            message: 消息
        """
        for callback in self.progress_callbacks:
            try:
                callback(workflow_name, progress, message)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    def add_progress_callback(self, callback: Callable):
        """添加进度回调

        Args:
            callback: 回调函数(workflow_name, progress, message)
        """
        self.progress_callbacks.append(callback)
    def get_progress(self) -> Dict[str, Any]:
        """获取整体进度

        Returns:
            进度信息
        """
        stats = self.state_tracker.get_workflow_stats()
        progress_info = {
            "total_workflows": len(self.workflows),
            "completed": stats.get("completed", 0),
            "running": stats.get("running", 0),
            "failed": stats.get("failed", 0),
            "pending": stats.get("pending", 0),
            "progress_percentage": int((stats.get("completed", 0) / len(self.workflows)) * 100) if self.workflows else 0
        }
        return progress_info
    def get_workflow_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态

        Args:
            name: 工作流名称

        Returns:
            状态信息
        """
        return self.state_tracker.get_task_state(name)
    def reset(self):
        """重置所有状态"""
        self.state_tracker.reset()
        self.execution_results.clear()
        self.logger.info("工作流编排器已重置")
    def save_checkpoint(self, checkpoint_name: str = None):
        """保存检查点

        Args:
            checkpoint_name: 检查点名称
        """
        self.state_tracker.save_checkpoint(checkpoint_name)
        self.logger.info(f"检查点已保存: {checkpoint_name}")
    def restore_checkpoint(self, checkpoint_name: str) -> bool:
        """恢复检查点

        Args:
            checkpoint_name: 检查点名称

        Returns:
            是否成功
        """
        success = self.state_tracker.restore_checkpoint(checkpoint_name)
        if success:
            self.logger.info(f"检查点已恢复: {checkpoint_name}")
        else:
            self.logger.error(f"检查点恢复失败: {checkpoint_name}")
        return success
