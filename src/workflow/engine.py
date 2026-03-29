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
工作流引擎

负责协调和编排所有工作流任务。
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowEngine:
    """工作流引擎

    协调和管理整个工作流。

    使用示例：
    ```python
    engine = WorkflowEngine()

    # 定义工作流
    engine.define_workflow([
        {"name": "search", "type": "literature_search", "params": {...}},
        {"name": "analyze", "type": "literature_analysis", "depends_on": ["search"]},
        {"name": "ppt", "type": "ppt_generation", "depends_on": ["analyze"]}
    ])

    # 执行工作流
    engine.execute()
    ```
    """

    def __init__(self):
        """初始化工作流引擎"""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_status: Dict[str, TaskStatus] = {}
        self.task_results: Dict[str, Any] = {}

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def define_workflow(self, workflow_config: List[Dict[str, Any]]):
        """定义工作流

        Args:
            workflow_config: 工作流配置列表
        """
        self.tasks.clear()
        self.task_status.clear()
        self.task_results.clear()

        for task in workflow_config:
            task_name = task["name"]
            self.tasks[task_name] = task
            self.task_status[task_name] = TaskStatus.PENDING

        self.logger.info(f"工作流定义完成: {len(self.tasks)} 个任务")

    def execute(self) -> bool:
        """执行工作流

        Returns:
            是否全部成功
        """
        self.logger.info("开始执行工作流")

        # 拓扑排序，确保依赖顺序正确
        execution_order = self._topological_sort()

        for task_name in execution_order:
            task = self.tasks[task_name]

            # 检查依赖是否完成
            if not self._check_dependencies(task):
                self.task_status[task_name] = TaskStatus.SKIPPED
                self.logger.warning(f"任务跳过（依赖未完成）: {task_name}")
                continue

            # 执行任务
            self.task_status[task_name] = TaskStatus.RUNNING
            self.logger.info(f"开始执行任务: {task_name}")

            try:
                result = self._execute_task(task)
                self.task_status[task_name] = TaskStatus.COMPLETED
                self.task_results[task_name] = result
                self.logger.info(f"任务完成: {task_name}")
            except Exception as e:
                self.task_status[task_name] = TaskStatus.FAILED
                self.logger.error(f"任务失败: {task_name} - {e}")
                return False

        self.logger.info("工作流执行完成")
        return True

    def _execute_task(self, task: Dict[str, Any]) -> Any:
        """执行单个任务

        Args:
            task: 任务配置

        Returns:
            执行结果
        """
        task_type = task.get("type")
        params = task.get("params", {})

        # 根据任务类型分发
        if task_type == "literature_search":
            return self._search_literature(params)
        elif task_type == "literature_analysis":
            return self._analyze_literature(params)
        elif task_type == "ppt_generation":
            return self._generate_ppt(params)
        else:
            raise ValueError(f"未知任务类型: {task_type}")

    def _search_literature(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """文献搜索任务"""
        # 实际实现会调用 SearchManager
        return {"papers": [], "count": 0}

    def _analyze_literature(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """文献分析任务"""
        # 实际实现会调用 AnalysisManager
        return {"results": [], "count": 0}

    def _generate_ppt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """PPT 生成任务"""
        # 实际实现会调用 PPTGenerator
        return {"ppt_path": "", "slides": 0}

    def _topological_sort(self) -> List[str]:
        """拓扑排序

        Returns:
            任务执行顺序
        """
        visited = set()
        order = []

        def visit(task_name: str):
            if task_name in visited:
                return
            visited.add(task_name)

            task = self.tasks[task_name]
            for dep in task.get("depends_on", []):
                visit(dep)

            order.append(task_name)

        for task_name in self.tasks:
            visit(task_name)

        return order

    def _check_dependencies(self, task: Dict[str, Any]) -> bool:
        """检查依赖是否完成

        Args:
            task: 任务配置

        Returns:
            是否所有依赖都已完成
        """
        for dep in task.get("depends_on", []):
            if self.task_status.get(dep) != TaskStatus.COMPLETED:
                return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取工作流状态

        Returns:
            状态信息
        """
        return {
            "total_tasks": len(self.tasks),
            "status": {name: status.value for name, status in self.task_status.items()},
            "results": self.task_results
        }
