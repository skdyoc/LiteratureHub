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
Agent 模块

提供多Agent系统的类型定义和注册管理。

主要组件：
- AgentType: Agent类型枚举
- LiteratureAgent: 文献Agent基类
- AGENT_REGISTRY: Agent注册表
- ORDERED_AGENT_LIST: 有序Agent列表

支持的Agent类型：
- LITERATURE_SEARCH: 文献搜索
- LITERATURE_ANALYSIS: 文献分析
- INNOVATION_EXTRACTION: 创新点提取
- MOTIVATION_ANALYSIS: 研究动机分析
- TECHNICAL_ROADMAP: 技术路线
- MECHANISM_INTERPRETATION: 机理解析
- IMPACT_ASSESSMENT: 影响评估
- HISTORICAL_CONTEXT: 历史脉络
- PPT_GENERATE: PPT生成
"""

from .types import AgentType, AGENT_REGISTRY, ORDERED_AGENT_LIST
from ..factory.base import LiteratureAgent

__all__ = [
    "AgentType",
    "LiteratureAgent",
    "AGENT_REGISTRY",
    "ORDERED_AGENT_LIST"
]
