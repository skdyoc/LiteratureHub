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
Agent 工厂模式

参考 Eigent 的 Agent 工厂设计，实现标准化的 Agent 创建流程。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any
from pathlib import Path

from ..agents.types import AgentType, get_agent_display_info
from ..tools.base import BaseToolkit


class LiteratureAgent:
    """文献 Agent 基类

    基于 Eigent 的 ListenChatAgent 设计。
    """

    def __init__(
        self,
        agent_type: AgentType,
        system_message: str,
        model: Any,  # GLMAPIClient
        tools: List[Any],
        agent_id: Optional[str] = None,
    ):
        """
        Args:
            agent_type: Agent 类型
            system_message: System Prompt
            model: AI 模型客户端（GLM-5）
            tools: 工具列表
            agent_id: Agent 唯一 ID
        """
        self.agent_type = agent_type
        self.system_message = system_message
        self.model = model
        self.tools = tools
        self.agent_id = agent_id or self._generate_agent_id()

        # 获取显示信息
        self.display_info = get_agent_display_info(agent_type)

    def _generate_agent_id(self) -> str:
        """生成唯一的 Agent ID"""
        import uuid
        return f"{self.agent_type.value}_{uuid.uuid4().hex[:8]}"

    async def execute(self, task: dict) -> dict:
        """执行任务

        Args:
            task: 任务字典

        Returns:
            dict: 执行结果
        """
        # 这里实现具体的任务执行逻辑
        # 实际实现会调用 GLM-5 API
        raise NotImplementedError("Subclass must implement execute()")


class BaseAgentFactory(ABC):
    """Agent 工厂基类

    参考 Eigent 的工厂模式设计，实现标准化的 Agent 创建流程。
    """

    def __init__(self, agent_type: AgentType, api_client: Any, config: dict = None):
        """
        Args:
            agent_type: Agent 类型
            api_client: AI 模型客户端（GLM-5）
            config: 配置字典
        """
        self.agent_type = agent_type
        self.api_client = api_client
        self.config = config or {}
        self.toolkits: List[BaseToolkit] = []

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取 System Prompt

        Returns:
            str: System Prompt 内容
        """
        pass

    @abstractmethod
    def register_toolkits(self) -> None:
        """注册工具集

        子类实现此方法，注册需要的工具集。
        """
        pass

    def create_agent(self) -> LiteratureAgent:
        """创建 Agent

        标准化的 Agent 创建流程：
        1. 注册工具
        2. 构建工具列表
        3. 创建 Agent 实例

        Returns:
            LiteratureAgent: Agent 实例
        """
        # 1. 注册工具
        self.register_toolkits()

        # 2. 构建工具列表
        tools = self._build_tools()

        # 3. 获取 System Prompt
        system_message = self.get_system_prompt()

        # 4. 创建 Agent
        agent = LiteratureAgent(
            agent_type=self.agent_type,
            system_message=system_message,
            model=self.api_client,
            tools=tools,
        )

        return agent

    def _build_tools(self) -> List[Any]:
        """构建工具列表

        从所有注册的工具集中提取工具。

        Returns:
            List[Any]: 工具列表
        """
        tools = []
        for toolkit in self.toolkits:
            tools.extend(toolkit.get_tools())
        return tools

    def get_toolkit(self, toolkit_name: str) -> Optional[BaseToolkit]:
        """获取指定的工具集

        Args:
            toolkit_name: 工具集名称

        Returns:
            Optional[BaseToolkit]: 工具集实例，不存在则返回 None
        """
        for toolkit in self.toolkits:
            if toolkit.get_name() == toolkit_name:
                return toolkit
        return None

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            Any: 配置值
        """
        return self.config.get(key, default)


class AgentFactoryRegistry:
    """Agent 工厂注册表

    管理所有 Agent 工厂的注册和创建。
    """

    _factories: dict[AgentType, type] = {}

    @classmethod
    def register(cls, agent_type: AgentType, factory_class: type):
        """注册 Agent 工厂

        Args:
            agent_type: Agent 类型
            factory_class: 工厂类
        """
        cls._factories[agent_type] = factory_class

    @classmethod
    def create_factory(
        cls,
        agent_type: AgentType,
        api_client: Any,
        config: dict = None
    ) -> BaseAgentFactory:
        """创建 Agent 工厂实例

        Args:
            agent_type: Agent 类型
            api_client: AI 模型客户端
            config: 配置字典

        Returns:
            BaseAgentFactory: 工厂实例

        Raises:
            ValueError: 如果 Agent 类型未注册
        """
        factory_class = cls._factories.get(agent_type)
        if factory_class is None:
            raise ValueError(f"Agent type {agent_type} not registered")
        return factory_class(agent_type, api_client, config)

    @classmethod
    def list_registered(cls) -> List[AgentType]:
        """列出所有已注册的 Agent 类型

        Returns:
            List[AgentType]: Agent 类型列表
        """
        return list(cls._factories.keys())

    @classmethod
    def is_registered(cls, agent_type: AgentType) -> bool:
        """检查 Agent 类型是否已注册

        Args:
            agent_type: Agent 类型

        Returns:
            bool: 是否已注册
        """
        return agent_type in cls._factories


def register_agent_factory(agent_type: AgentType):
    """Agent 工厂注册装饰器

    用法：
    ```python
    @register_agent_factory(AgentType.LITERATURE_SEARCH)
    class LiteratureSearchAgentFactory(BaseAgentFactory):
        pass
    ```

    Args:
        agent_type: Agent 类型

    Returns:
        装饰器函数
    """
    def decorator(factory_class: type) -> type:
        AgentFactoryRegistry.register(agent_type, factory_class)
        return factory_class
    return decorator
