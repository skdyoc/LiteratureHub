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
任务编排器

管理和协调多个工作流任务的执行。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict


class TaskOrchestrator:
    """任务编排器

    负责管理和协调多个工作流任务的执行，确保任务按依赖关系正确执行。

    功能：
    - 任务注册和管理
    - 依赖关系解析
    - 执行顺序编排
    - 进度跟踪和通知
    - 错误处理和重试
    - 任务状态持久化
    """

    def __init__(self, max_concurrent: int = 5):
        """初始化任务编排器

        Args:
            max_concurrent: 最大并发任务数
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.task_status: Dict[str, str] = {}  # pending, running, completed, failed
        self.logger = logging.getLogger(self.__class__.__name__)

        # 进度回调
        self.progress_callbacks: List[Callable[[str, int, int, str], None]] = []

        # 执行结果
        self.results: Dict[str, Any] = {}

    def register_task(
        self,
        task_name: str,
        task_func: Callable,
        params: Dict[str, Any] = None,
        dependencies: List[str] = None
    ):
        """注册任务

        Args:
            task_name: 任务名称
            task_func: 任务函数
            params: 任务参数
            dependencies: 依赖任务列表
        """
        self.tasks[task_name] = {
            "func": task_func,
            "params": params or {},
            "dependencies": dependencies or [],
            "created_at": datetime.now()
        }

        # 设置依赖关系
        for dep in dependencies or []:
            self.dependencies[task_name].add(dep)

        # 初始化状态
        self.task_status[task_name] = "pending"

        self.logger.info(f"已注册任务: {task_name}, 依赖: {dependencies or []}")

    def add_progress_callback(self, callback: Callable[[str, int, int, str], None]):
        """添加进度回调函数

        Args:
            callback: 回调函数 (task_name, current, total, message)
        """
        self.progress_callbacks.append(callback)

    def _notify_progress(self, task_name: str, current: int, total: int, message: str):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(task_name, current, total, message)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")

    def _get_execution_order(self) -> List[str]:
        """获取任务执行顺序（拓扑排序）

        Returns:
            排序后的任务名称列表
        """
        visited = set()
        order = []

        def visit(task_name: str):
            if task_name in visited:
                return

            # 先访问依赖
            for dep in self.dependencies[task_name]:
                if dep not in self.tasks:
                    self.logger.warning(f"任务 {task_name} 的依赖 {dep} 不存在")
                    continue

                visit(dep)

            visited.add(task_name)
            order.append(task_name)

        # 访问所有任务
        for task_name in self.tasks.keys():
            visit(task_name)

        return order

    async def execute_task(self, task_name: str) -> Dict[str, Any]:
        """执行单个任务

        Args:
            task_name: 任务名称

        Returns:
            执行结果
        """
        task_info = self.tasks.get(task_name)

        if not task_info:
            return {
                "status": "error",
                "error": f"任务不存在: {task_name}"
            }

        # 检查依赖是否完成
        for dep in self.dependencies[task_name]:
            if self.task_status.get(dep) != "completed":
                return {
                    "status": "error",
                    "error": f"依赖任务未完成: {dep}"
                }

        # 更新状态
        self.task_status[task_name] = "running"
        self._notify_progress(task_name, 0, 100, "开始执行")

        try:
            # 执行任务
            func = task_info["func"]
            params = task_info["params"]

            if asyncio.iscoroutinefunction(func):
                result = await func(**params)
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(**params))

            # 保存结果
            self.results[task_name] = result
            self.task_status[task_name] = "completed"

            self._notify_progress(task_name, 100, 100, "执行完成")

            return {
                "status": "success",
                "result": result
            }

        except Exception as e:
            self.task_status[task_name] = "failed"
            self.logger.error(f"任务执行失败 {task_name}: {e}", exc_info=True)

            self._notify_progress(task_name, 0, 100, f"执行失败: {e}")

            return {
                "status": "error",
                "error": str(e)
            }

    async def execute_all(self, parallel: bool = False) -> Dict[str, Any]:
        """执行所有任务

        Args:
            parallel: 是否并行执行

        Returns:
            所有任务的执行结果
        """
        start_time = datetime.now()
        execution_order = self._get_execution_order()

        self.logger.info(f"开始执行 {len(execution_order)} 个任务")
        self.logger.info(f"执行顺序: {execution_order}")

        results = {}

        if parallel:
            # 分阶段并行执行（考虑依赖关系）
            completed = set()

            while len(completed) < len(execution_order):
                # 找出可以执行的任务
                ready_tasks = [
                    task_name
                    for task_name in execution_order
                    if task_name not in completed
                    and all(dep in completed for dep in self.dependencies[task_name])
                ]

                if not ready_tasks:
                    break

                # 并行执行
                tasks = [self.execute_task(task_name) for task_name in ready_tasks]
                task_results = await asyncio.gather(*tasks, return_exceptions=True)

                for task_name, result in zip(ready_tasks, task_results):
                    if isinstance(result, Exception):
                        results[task_name] = {
                            "status": "error",
                            "error": str(result)
                        }
                    else:
                        results[task_name] = result

                    completed.add(task_name)

        else:
            # 串行执行
            for i, task_name in enumerate(execution_order, 1):
                self._notify_progress(task_name, i, len(execution_order), f"执行任务 {i}/{len(execution_order)}")

                result = await self.execute_task(task_name)
                results[task_name] = result

                # 如果任务失败且依赖此任务的其他任务，停止执行
                if result["status"] == "error":
                    self.logger.error(f"任务 {task_name} 失败，停止后续执行")
                    break

        # 统计结果
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        success_count = sum(1 for r in results.values() if r.get("status") == "success")
        failed_count = sum(1 for r in results.values() if r.get("status") == "error")

        self.logger.info(f"执行完成: {success_count} 成功, {failed_count} 失败, 耗时 {duration:.2f} 秒")

        return {
            "total": len(execution_order),
            "success": success_count,
            "failed": failed_count,
            "duration": duration,
            "results": results
        }

    def get_task_status(self, task_name: str) -> Optional[str]:
        """获取任务状态

        Args:
            task_name: 任务名称

        Returns:
            任务状态 (pending, running, completed, failed)
        """
        return self.task_status.get(task_name)

    def get_all_status(self) -> Dict[str, str]:
        """获取所有任务状态

        Returns:
            任务状态字典
        """
        return self.task_status.copy()

    def clear(self):
        """清空所有任务"""
        self.tasks.clear()
        self.dependencies.clear()
        self.task_status.clear()
        self.results.clear()

        self.logger.info("已清空所有任务")
