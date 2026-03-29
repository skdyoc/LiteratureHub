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
依赖管理器

管理工作流任务之间的依赖关系。
"""

import logging
from typing import List, Dict, Set, Any, Tuple
from collections import defaultdict, deque


class DependencyManager:
    """依赖管理器

    管理任务之间的依赖关系，支持依赖检查、循环检测和拓扑排序。

    功能：
    - 依赖关系注册
    - 循环依赖检测
    - 拓扑排序
    - 依赖图可视化
    - 依赖影响分析
    """

    def __init__(self):
        """初始化依赖管理器"""
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # task -> dependencies
        self.dependents: Dict[str, Set[str]] = defaultdict(set)  # task -> dependents
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_dependency(self, task: str, depends_on: str):
        """添加依赖关系

        Args:
            task: 任务名称
            depends_on: 依赖的任务名称
        """
        if task == depends_on:
            raise ValueError(f"任务不能依赖自己: {task}")

        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)

        self.logger.debug(f"添加依赖: {task} -> {depends_on}")

    def remove_dependency(self, task: str, depends_on: str):
        """移除依赖关系

        Args:
            task: 任务名称
            depends_on: 依赖的任务名称
        """
        self.dependencies[task].discard(depends_on)
        self.dependents[depends_on].discard(task)

        self.logger.debug(f"移除依赖: {task} -> {depends_on}")

    def get_dependencies(self, task: str) -> Set[str]:
        """获取任务的所有依赖

        Args:
            task: 任务名称

        Returns:
            依赖任务集合
        """
        return self.dependencies[task].copy()

    def get_dependents(self, task: str) -> Set[str]:
        """获取依赖此任务的所有任务

        Args:
            task: 任务名称

        Returns:
            依赖此任务的任务集合
        """
        return self.dependents[task].copy()

    def has_cycle(self) -> Tuple[bool, List[str]]:
        """检测是否存在循环依赖

        Returns:
            (是否存在循环, 循环路径)
        """
        # 使用 DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = defaultdict(int)
        parent = {}

        def dfs(node: str, path: List[str]) -> Tuple[bool, List[str]]:
            color[node] = GRAY
            path.append(node)

            for neighbor in self.dependencies[node]:
                if color[neighbor] == GRAY:
                    # 找到环，提取环路径
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:]

                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    has_cycle, cycle = dfs(neighbor, path)
                    if has_cycle:
                        return True, cycle

            path.pop()
            color[node] = BLACK
            return False, []

        # 检查所有节点
        for task in set(self.dependencies.keys()) | set(self.dependents.keys()):
            if color[task] == WHITE:
                has_cycle, cycle = dfs(task, [])
                if has_cycle:
                    self.logger.error(f"检测到循环依赖: {' -> '.join(cycle)}")
                    return True, cycle

        return False, []

    def topological_sort(self) -> List[str]:
        """拓扑排序

        Returns:
            排序后的任务列表

        Raises:
            ValueError: 如果存在循环依赖
        """
        # 先检查循环
        has_cycle, cycle = self.has_cycle()
        if has_cycle:
            raise ValueError(f"存在循环依赖，无法进行拓扑排序: {' -> '.join(cycle)}")

        # Kahn 算法
        in_degree = defaultdict(int)
        all_tasks = set(self.dependencies.keys()) | set(self.dependents.keys())

        # 计算入度
        for task in all_tasks:
            in_degree[task] = len(self.dependencies[task])

        # 队列
        queue = deque([task for task in all_tasks if in_degree[task] == 0])
        result = []

        while queue:
            task = queue.popleft()
            result.append(task)

            # 减少依赖此任务的节点的入度
            for dependent in self.dependents[task]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(all_tasks):
            raise ValueError("拓扑排序失败，可能存在未检测到的循环依赖")

        return result

    def get_execution_layers(self) -> List[List[str]]:
        """获取执行层级

        将任务分层，每层的任务可以并行执行。

        Returns:
            层级列表，每层是一个任务列表
        """
        # 先检查循环
        has_cycle, cycle = self.has_cycle()
        if has_cycle:
            raise ValueError(f"存在循环依赖: {' -> '.join(cycle)}")

        # 分层
        layers = []
        remaining = set(self.dependencies.keys()) | set(self.dependents.keys())
        completed = set()

        while remaining:
            # 找出所有依赖已满足的任务
            layer = [
                task for task in remaining
                if all(dep in completed for dep in self.dependencies[task])
            ]

            if not layer:
                # 如果没有任务可以执行，说明有问题
                break

            layers.append(layer)
            completed.update(layer)
            remaining -= set(layer)

        return layers

    def get_impact(self, task: str) -> Set[str]:
        """获取任务变更的影响范围

        Args:
            task: 任务名称

        Returns:
            受影响的任务集合
        """
        impacted = set()
        queue = deque([task])

        while queue:
            current = queue.popleft()

            for dependent in self.dependents[current]:
                if dependent not in impacted:
                    impacted.add(dependent)
                    queue.append(dependent)

        return impacted

    def get_critical_path(self) -> List[str]:
        """获取关键路径

        Returns:
            关键路径上的任务列表
        """
        # 实现基于任务持续时间的关键路径算法
        # 使用拓扑排序和动态规划计算关键路径

        all_tasks = set(self.dependencies.keys()) | set(self.dependents.keys())

        # 如果没有持续时间数据，使用最长依赖链
        if not hasattr(self, 'task_durations'):
            # 使用最长依赖链算法
            def get_depth(task: str, visited: Set[str]) -> int:
                if task in visited:
                    return 0

                visited.add(task)
                deps = self.dependencies.get(task, set())

                if not deps:
                    return 1

                return 1 + max(get_depth(dep, visited.copy()) for dep in deps)

            # 找到深度最大的任务链
            max_depth = 0
            critical_task = None

            for task in all_tasks:
                depth = get_depth(task, set())
                if depth > max_depth:
                    max_depth = depth
                    critical_task = task

            # 回溯构建关键路径
            path = []
            if critical_task:
                current = critical_task
                while current:
                    path.append(current)
                    deps = self.dependencies.get(current, set())
                    current = max(deps, key=lambda t: get_depth(t, set())) if deps else None

            return path[::-1]  # 反转路径

        # 有持续时间数据，使用标准关键路径算法
        # 1. 计算最早开始时间（ES）
        es = {}
        for task in self.topological_sort():
            deps = self.dependencies.get(task, set())
            es[task] = max((es.get(d, 0) + self.task_durations.get(d, 1) for d in deps), default=0)

        # 2. 计算最晚开始时间（LS）
        ls = {}
        max_es = max(es.values()) if es else 0
        for task in reversed(list(self.topological_sort())):
            dependents = self.dependents.get(task, set())
            if not dependents:
                ls[task] = max_es - self.task_durations.get(task, 1)
            else:
                ls[task] = min((ls.get(d, max_es) - self.task_durations.get(task, 1) for d in dependents), default=max_es)

        # 3. 找到关键任务（ES == LS）
        critical_tasks = [task for task in all_tasks if es.get(task, 0) == ls.get(task, 0)]

        # 4. 按依赖关系排序关键任务
        return [t for t in self.topological_sort() if t in critical_tasks]

        def get_depth(task: str, visited: Set[str]) -> int:
            if task in visited:
                return 0

            visited.add(task)
            deps = self.dependencies[task]

            if not deps:
                return 1

            return 1 + max(get_depth(dep, visited.copy()) for dep in deps)

        # 找到深度最大的任务
        depths = {task: get_depth(task, set()) for task in all_tasks}

        # 构建路径
        path = []
        current = max(depths.items(), key=lambda x: x[1])[0]

        while current:
            path.append(current)
            deps = self.dependencies[current]

            if not deps:
                break

            # 选择深度最大的依赖
            current = max(deps, key=lambda t: depths[t])

        return list(reversed(path))

    def clear(self):
        """清空所有依赖关系"""
        self.dependencies.clear()
        self.dependents.clear()

        self.logger.info("已清空所有依赖关系")

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典

        Returns:
            依赖关系字典
        """
        return {
            "dependencies": {
                task: list(deps)
                for task, deps in self.dependencies.items()
            },
            "dependents": {
                task: list(deps)
                for task, deps in self.dependents.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]):
        """从字典导入

        Args:
            data: 依赖关系字典
        """
        self.clear()

        for task, deps in data.get("dependencies", {}).items():
            for dep in deps:
                self.add_dependency(task, dep)

        self.logger.info(f"已导入 {len(self.dependencies)} 个任务的依赖关系")
