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
核心模块

提供Agent系统、工具集、工作流引擎等核心功能。

子模块：
- agents: Agent类型定义和工厂
- factory: Agent工厂（基于Eigent框架）
- tools: 工具集
- queue: 队列管理
- workflow: 工作流引擎
"""

from .agents import (
    AgentType,
    LiteratureAgent
)

from .factory import (
    BaseAgentFactory,
    AgentFactoryRegistry,
    register_agent_factory
)

__all__ = [
    # Agent
    "AgentType",
    "LiteratureAgent",
    # Factory
    "BaseAgentFactory",
    "AgentFactoryRegistry",
    "register_agent_factory"
]
