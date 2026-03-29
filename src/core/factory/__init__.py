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
Agent 工厂模块

基于 Eigent 框架的 Agent 工厂模式实现。

主要组件：
- BaseAgentFactory: Agent 工厂基类
- AgentFactoryRegistry: Agent 工厂注册表
- register_agent_factory: Agent 工厂注册装饰器

使用示例：
    @register_agent_factory(AgentType.LITERATURE_SEARCH)
    class LiteratureSearchAgentFactory(BaseAgentFactory):
        def get_system_prompt(self) -> str:
            return "你的系统提示词"

        def register_toolkits(self) -> None:
            # 注册工具集
            pass

    # 获取工厂
    factory = AgentFactoryRegistry.get(AgentType.LITERATURE_SEARCH)
    agent = factory.create_agent()
"""

from .base import BaseAgentFactory, AgentFactoryRegistry, register_agent_factory

# 导入所有工厂实现以触发装饰器注册
from . import analyze_factory
from . import ppt_factory

__all__ = [
    "BaseAgentFactory",
    "AgentFactoryRegistry",
    "register_agent_factory"
]
