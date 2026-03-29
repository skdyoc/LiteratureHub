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
队列管理模块

提供基于串行队列的异步任务管理功能。

主要组件：
- GLM5Queue: GLM-5 API 串行队列
- glm5_queue: 全局单例队列
- QueueTask: 队列任务类
- TaskStatus: 任务状态枚举

使用示例：
    from src.core.queue import glm5_queue, TaskStatus

    # 添加任务
    task_id = await glm5_queue.add_task(
        prompt="你的提示词",
        priority=1
    )

    # 获取结果
    result = await glm5_queue.get_result(task_id)

    # 检查状态
    status = glm5_queue.get_status(task_id)
"""

from .glm5_queue import GLM5Queue, glm5_queue, QueueTask, TaskStatus

__all__ = [
    "GLM5Queue",
    "glm5_queue",
    "QueueTask",
    "TaskStatus"
]
