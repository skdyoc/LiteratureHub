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
工具集基础类

参考 Eigent 的 Toolkit 模式，实现统一的工具抽象。
"""

from abc import ABC, abstractmethod
from typing import List, Any, Callable


class BaseToolkit(ABC):
    """工具集基类

    参考 Eigent 的 Toolkit 设计模式。
    """

    @abstractmethod
    def get_name(self) -> str:
        """获取工具集名称

        Returns:
            str: 工具集名称
        """
        pass

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """获取所有工具

        Returns:
            List[Any]: 工具列表
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具集描述

        Returns:
            str: 描述
        """
        pass


class ToolkitRegistry:
    """工具集注册表"""

    _toolkits: dict[str, BaseToolkit] = {}

    @classmethod
    def register(cls, toolkit: BaseToolkit):
        """注册工具集

        Args:
            toolkit: 工具集实例
        """
        cls._toolkits[toolkit.get_name()] = toolkit

    @classmethod
    def get(cls, name: str) -> BaseToolkit:
        """获取工具集

        Args:
            name: 工具集名称

        Returns:
            BaseToolkit: 工具集实例
        """
        return cls._toolkits.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有工具集

        Returns:
            List[str]: 工具集名称列表
        """
        return list(cls._toolkits.keys())

    @classmethod
    def get_all_tools(cls) -> dict[str, List[Any]]:
        """获取所有工具集的工具

        Returns:
            dict: {toolkit_name: [tools]}
        """
        return {
            name: toolkit.get_tools()
            for name, toolkit in cls._toolkits.items()
        }
