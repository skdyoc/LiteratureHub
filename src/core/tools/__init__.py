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
工具集模块

基于 Eigent 框架的 Toolkit 模式实现，提供统一的工具抽象。

主要组件：
- BaseToolkit: 工具集基类
- ToolkitRegistry: 工具集注册表
- LiteratureSearchToolkit: 文献搜索工具集
- LiteratureDownloadToolkit: 文献下载工具集
- LiteratureAnalysisToolkit: 文献分析工具集
- NoteTakingToolkit: 笔记记录工具集

使用示例：
    from src.core.tools import ToolkitRegistry, LiteratureSearchToolkit

    # 注册工具集
    toolkit = LiteratureSearchToolkit()
    ToolkitRegistry.register(toolkit)

    # 获取工具集
    toolkit = ToolkitRegistry.get("LiteratureSearchToolkit")

    # 列出所有工具集
    all_toolkits = ToolkitRegistry.list_all()

    # 获取所有工具
    all_tools = ToolkitRegistry.get_all_tools()
"""

from .base import BaseToolkit, ToolkitRegistry
from .literature import (
    LiteratureSearchToolkit,
    LiteratureDownloadToolkit,
    LiteratureAnalysisToolkit
)
from .note import NoteTakingToolkit


__all__ = [
    # 基类
    "BaseToolkit",
    "ToolkitRegistry",
    # 文献工具集
    "LiteratureSearchToolkit",
    "LiteratureDownloadToolkit",
    "LiteratureAnalysisToolkit",
    # 笔记工具集
    "NoteTakingToolkit"
]
