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
GLM-5 串行队列管理器

⚠️ 重要：由于 GLM-5 API 不支持并发，必须使用队列确保串行调用。
"""

import asyncio
import logging
from typing import Callable, Any, Awaitable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueTask:
    """队列任务"""
    id: str
    name: str
    func: Callable[..., Awaitable[Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 0  # 优先级，数字越大优先级越高
    created_at: datetime = field(default_factory=datetime.now)
    agent_type: str = ""

    # 运行时状态
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None

    def __lt__(self, other):
        """优先级队列的排序规则"""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


class GLM5Queue:
    """GLM-5 串行队列管理器

    ⚠️ 重要：由于 GLM-5 API 不支持并发，必须使用队列确保串行调用。

    使用场景：
    - 所有 GLM-5 API 调用必须通过此队列
    - 自动管理请求队列，确保同一时间只有一个请求在执行
    - 支持任务优先级和重试机制
    """

    _instance = None  # 单例模式

    def __new__(cls, *args, **kwargs):
        """确保全局只有一个队列实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_concurrent: int = 1):
        """
        Args:
            max_concurrent: 最大并发数（GLM-5 必须为 1）
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: int = 0
        self._task_history: list[QueueTask] = []
        self._event_callbacks: dict[str, list[callable]] = {}
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._initialized = True

    def register_event_callback(self, event: str, callback: callable):
        """注册事件回调

        Args:
            event: 事件名称（task_submitted, task_started, task_completed, task_failed）
            callback: 回调函数
        """
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)

    async def submit(
        self,
        task_id: str,
        task_name: str,
        func: Callable[..., Awaitable[Any]],
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 0,
        agent_type: str = "",
    ) -> Any:
        """提交任务到队列

        Args:
            task_id: 任务唯一 ID
            task_name: 任务名称
            func: 异步函数
            args: 位置参数
            kwargs: 关键字参数
            priority: 优先级（0-10，数字越大优先级越高）
            agent_type: Agent 类型

        Returns:
            任务执行结果
        """
        task = QueueTask(
            id=task_id,
            name=task_name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            agent_type=agent_type,
        )

        # 触发任务提交事件
        await self._trigger_event("task_submitted", task)

        # 加入队列
        await self._queue.put(task)

        # 等待任务完成
        result = await self._wait_for_completion(task)

        return result

    async def _wait_for_completion(self, task: QueueTask) -> Any:
        """等待任务完成"""
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            await asyncio.sleep(0.1)

        if task.status == TaskStatus.FAILED:
            raise Exception(task.error)

        return task.result

    async def start(self):
        """启动队列处理"""
        if self._is_running:
            self.logger.warning("队列已经在运行中")
            return

        self._is_running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        self.logger.info("GLM-5 API队列已启动")

    async def stop(self):
        """停止队列处理"""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
        self.logger.info("GLM-5 API队列已停止")

    async def _process_queue(self):
        """处理队列中的任务"""
        while self._is_running:
            # 等待队列中有任务
            if self._queue.empty():
                await asyncio.sleep(0.1)
                continue

            # 检查并发限制
            if self._running_tasks >= self.max_concurrent:
                await asyncio.sleep(0.1)
                continue

            # 获取下一个任务
            task = await self._queue.get()

            # 增加运行中的任务数
            self._running_tasks += 1

            # 异步执行任务
            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: QueueTask):
        """执行任务"""
        try:
            # 更新状态
            task.status = TaskStatus.RUNNING
            await self._trigger_event("task_started", task)

            # 执行任务
            result = await task.func(*task.args, **task.kwargs)

            # 保存结果
            task.result = result
            task.status = TaskStatus.COMPLETED

            # 触发完成事件
            await self._trigger_event("task_completed", task)

        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

            # 触发失败事件
            await self._trigger_event("task_failed", task)

            self.logger.error(f"任务 {task.id} 执行失败: {e}")

        finally:
            # 减少运行中的任务数
            self._running_tasks -= 1

            # 加入历史记录
            self._task_history.append(task)

    async def _trigger_event(self, event: str, task: QueueTask):
        """触发事件回调"""
        if event in self._event_callbacks:
            for callback in self._event_callbacks[event]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)

    def get_queue_status(self) -> dict:
        """获取队列状态"""
        return {
            "queue_size": self._queue.qsize(),
            "running_tasks": self._running_tasks,
            "max_concurrent": self.max_concurrent,
            "completed_tasks": len([t for t in self._task_history if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in self._task_history if t.status == TaskStatus.FAILED]),
            "recent_tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "agent_type": t.agent_type,
                    "status": t.status.value,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat(),
                }
                for t in self._task_history[-10:]  # 最近 10 个任务
            ],
        }

    def clear_history(self):
        """清空任务历史"""
        self._task_history.clear()


# 全局队列实例
glm5_queue = GLM5Queue(max_concurrent=1)
