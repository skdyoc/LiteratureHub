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
LiteratureHub 核心包

提供文献搜索、分析、PPT生成的完整工作流。

模块：
- core: 核心功能模块（Agent工厂、工作流引擎、工具集）
- gui: 图形用户界面
- ui: UI组件
- data: 数据管理
- analysis: 文献分析
- search: 文献搜索
- ppt: PPT生成
- workflow: 工作流管理
"""

__version__ = "1.0.0"
__author__ = "LiteratureHub Team"

# 延迟导入，避免循环依赖
__all__ = [
    # 核心模块
    "core",
    # GUI模块
    "gui",
    "ui",
    # 数据模块
    "data",
    # 分析模块
    "analysis",
    # 搜索模块
    "search",
    # PPT模块
    "ppt",
    # 工作流模块
    "workflow"
]


def get_version() -> str:
    """获取版本号

    Returns:
        str: 版本号字符串
    """
    return __version__


def get_modules() -> list:
    """获取所有模块列表

    Returns:
        list: 模块名称列表
    """
    return __all__.copy()
