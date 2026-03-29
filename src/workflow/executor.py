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
工作流执行器

执行具体的工作流任务。
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowExecutor:
    """工作流执行器

    执行具体的工作流任务，支持异步和并发。

    使用示例：
    ```python
    executor = WorkflowExecutor()

    # 执行单个任务
    result = await executor.execute_task(
        task_name="search_papers",
        task_func=search_function,
        params={"keywords": ["AI"]}
    )

    # 批量执行
    results = await executor.execute_batch([
        {"name": "task1", "func": func1, "params": {}},
        {"name": "task2", "func": func2, "params": {}}
    ])
    ```
    """

    def __init__(self, max_concurrent: int = 5):
        """初始化工作流执行器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 任务状态
        self.task_status: Dict[str, TaskStatus] = {}
        self.task_results: Dict[str, Any] = {}

        # 进度回调
        self.progress_callbacks: List[Callable] = []

        # 信号量（限制并发）
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 取消标志
        self._cancelled = False

    async def execute_task(
        self,
        task_name: str,
        task_func: Callable,
        params: Dict[str, Any] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """执行单个任务

        Args:
            task_name: 任务名称
            task_func: 任务函数
            params: 任务参数
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        params = params or {}

        self.logger.info(f"开始执行任务: {task_name}")
        self.task_status[task_name] = TaskStatus.RUNNING

        # 通知进度
        self._notify_progress(task_name, 0, "任务开始")

        try:
            # 执行任务（带并发限制）
            async with self._semaphore:
                if asyncio.iscoroutinefunction(task_func):
                    # 异步函数
                    if timeout:
                        result = await asyncio.wait_for(
                            task_func(**params),
                            timeout=timeout
                        )
                    else:
                        result = await task_func(**params)
                else:
                    # 同步函数（在线程池中执行）
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: task_func(**params)
                    )

            # 记录结果
            self.task_results[task_name] = result
            self.task_status[task_name] = TaskStatus.COMPLETED

            self._notify_progress(task_name, 100, "任务完成")
            self.logger.info(f"任务执行成功: {task_name}")

            return {
                "task_name": task_name,
                "status": "success",
                "result": result,
                "completed_at": datetime.now().isoformat()
            }

        except asyncio.TimeoutError:
            self.task_status[task_name] = TaskStatus.FAILED
            self._notify_progress(task_name, 0, "任务超时")
            self.logger.error(f"任务超时: {task_name}")

            return {
                "task_name": task_name,
                "status": "timeout",
                "error": "任务超时",
                "completed_at": datetime.now().isoformat()
            }

        except asyncio.CancelledError:
            self.task_status[task_name] = TaskStatus.CANCELLED
            self._notify_progress(task_name, 0, "任务取消")
            self.logger.info(f"任务已取消: {task_name}")

            return {
                "task_name": task_name,
                "status": "cancelled",
                "completed_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.task_status[task_name] = TaskStatus.FAILED
            self._notify_progress(task_name, 0, f"任务失败: {e}")
            self.logger.error(f"任务执行失败: {task_name} - {e}")

            return {
                "task_name": task_name,
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }

    async def execute_batch(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """批量执行任务

        Args:
            tasks: 任务列表
            parallel: 是否并行执行

        Returns:
            执行结果列表
        """
        self.logger.info(f"开始批量执行 {len(tasks)} 个任务")

        if parallel:
            # 并行执行
            coroutines = [
                self.execute_task(
                    task_name=task["name"],
                    task_func=task["func"],
                    params=task.get("params", {}),
                    timeout=task.get("timeout")
                )
                for task in tasks
            ]

            results = await asyncio.gather(*coroutines, return_exceptions=True)

        else:
            # 串行执行
            results = []
            for task in tasks:
                if self._cancelled:
                    self.logger.info("批量执行已取消")
                    break

                result = await self.execute_task(
                    task_name=task["name"],
                    task_func=task["func"],
                    params=task.get("params", {}),
                    timeout=task.get("timeout")
                )
                results.append(result)

        self.logger.info(f"批量执行完成: {len(results)} 个任务")
        return results

    async def execute_with_retry(
        self,
        task_name: str,
        task_func: Callable,
        params: Dict[str, Any] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """带重试的任务执行

        Args:
            task_name: 任务名称
            task_func: 任务函数
            params: 任务参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            执行结果
        """
        params = params or {}

        for attempt in range(max_retries + 1):
            try:
                result = await self.execute_task(task_name, task_func, params)

                if result["status"] == "success":
                    return result

                # 如果是最后一次尝试，返回失败
                if attempt == max_retries:
                    return result

                # 等待后重试
                self.logger.info(f"任务 {task_name} 第 {attempt + 1} 次重试...")
                await asyncio.sleep(retry_delay * (attempt + 1))

            except Exception as e:
                self.logger.error(f"任务 {task_name} 第 {attempt + 1} 次失败: {e}")

                if attempt == max_retries:
                    return {
                        "task_name": task_name,
                        "status": "failed",
                        "error": str(e),
                        "attempts": attempt + 1
                    }

        return {
            "task_name": task_name,
            "status": "failed",
            "error": "超过最大重试次数",
            "attempts": max_retries + 1
        }

    def add_progress_callback(self, callback: Callable):
        """添加进度回调

        Args:
            callback: 回调函数(task_name, progress, message)
        """
        self.progress_callbacks.append(callback)

    def _notify_progress(self, task_name: str, progress: int, message: str):
        """通知进度

        Args:
            task_name: 任务名称
            progress: 进度（0-100）
            message: 消息
        """
        for callback in self.progress_callbacks:
            try:
                callback(task_name, progress, message)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")

    def cancel(self):
        """取消所有任务"""
        self._cancelled = True
        self.logger.info("执行器已标记为取消")

    def reset(self):
        """重置执行器"""
        self.task_status.clear()
        self.task_results.clear()
        self._cancelled = False
        self.logger.info("执行器已重置")

    def get_task_status(self, task_name: str) -> Optional[TaskStatus]:
        """获取任务状态

        Args:
            task_name: 任务名称

        Returns:
            任务状态
        """
        return self.task_status.get(task_name)

    def get_task_result(self, task_name: str) -> Optional[Any]:
        """获取任务结果

        Args:
            task_name: 任务名称

        Returns:
            任务结果
        """
        return self.task_results.get(task_name)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for s in self.task_status.values() if s == status
            )

        return {
            "total_tasks": len(self.task_status),
            "status_distribution": status_counts,
            "success_rate": (
                status_counts.get("completed", 0) / len(self.task_status) * 100
                if self.task_status else 0
            )
        }
