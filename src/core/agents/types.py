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
Agent 类型系统

参考 Eigent Multi-Agent 架构，实现类型安全的 Agent 类型定义。
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any


class AgentType(str, Enum):
    """文献管理系统的 Agent 类型

    基于 Eigent 的类型安全设计，使用枚举确保 Agent 类型的一致性。
    """
    LITERATURE_SEARCH = "literature_search_agent"      # 文献搜索
    LITERATURE_DOWNLOAD = "literature_download_agent"  # 文献下载
    LITERATURE_PARSE = "literature_parse_agent"        # 文献解析（PDF → Markdown）
    LITERATURE_ANALYZE = "literature_analyze_agent"    # 文献分析
    LITERATURE_CLASSIFY = "literature_classify_agent"  # 文献分类
    KNOWLEDGE_GRAPH = "knowledge_graph_agent"          # 知识图谱构建
    PPT_GENERATE = "ppt_generate_agent"                # PPT 内容生成
    CITATION_MANAGE = "citation_manage_agent"          # 引用管理

    def __str__(self) -> str:
        return self.value


@dataclass
class AgentDisplayInfo:
    """Agent 显示信息

    基于 Eigent 的 agentMap 设计，分离 Agent 能力与显示属性。
    """
    name: str                              # 英文名称
    name_cn: str                           # 中文名称
    description: str                       # 描述
    icon: str                              # 图标名称或路径
    color: str                             # 主题颜色（HEX）
    capabilities: List[str]                # 能力列表
    dependencies: List[str] = None         # 依赖的其他 Agent

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


# Agent 类型到显示信息的映射
# 基于 Eigent 的 agentMap 设计模式
AGENT_REGISTRY: Dict[AgentType, AgentDisplayInfo] = {
    AgentType.LITERATURE_SEARCH: AgentDisplayInfo(
        name="Literature Search Agent",
        name_cn="文献搜索代理",
        description="搜索学术论文（支持 Elsevier、arXiv、IEEE 等多个数据库）",
        icon="search",
        color="#3B82F6",  # 蓝色
        capabilities=[
            "search_papers",
            "filter_by_keywords",
            "export_results",
            "deduplicate_papers"
        ],
        dependencies=[]
    ),
    AgentType.LITERATURE_DOWNLOAD: AgentDisplayInfo(
        name="Literature Download Agent",
        name_cn="文献下载代理",
        description="批量下载学术论文 PDF（支持 SciHub、NoteExpress 等多种方式）",
        icon="download",
        color="#10B981",  # 绿色
        capabilities=[
            "download_pdf",
            "retry_failed",
            "verify_integrity",
            "track_progress"
        ],
        dependencies=[AgentType.LITERATURE_SEARCH.value]
    ),
    AgentType.LITERATURE_PARSE: AgentDisplayInfo(
        name="Literature Parse Agent",
        name_cn="文献解析代理",
        description="解析 PDF 为 Markdown/JSON（基于 MinerU，保留公式、图表、结构）",
        icon="file-text",
        color="#F59E0B",  # 橙色
        capabilities=[
            "parse_pdf",
            "extract_metadata",
            "preserve_structure",
            "ocr_support"
        ],
        dependencies=[AgentType.LITERATURE_DOWNLOAD.value]
    ),
    AgentType.LITERATURE_ANALYZE: AgentDisplayInfo(
        name="Literature Analyze Agent",
        name_cn="文献分析代理",
        description="AI 深度分析文献（创新点、动机、机理、影响、脉络等 6 个维度）",
        icon="brain",
        color="#8B5CF6",  # 紫色
        capabilities=[
            "analyze_innovation",
            "extract_motivation",
            "identify_mechanism",
            "assess_impact",
            "trace_history",
            "extract_roadmap"
        ],
        dependencies=[AgentType.LITERATURE_PARSE.value]
    ),
    AgentType.LITERATURE_CLASSIFY: AgentDisplayInfo(
        name="Literature Classify Agent",
        name_cn="文献分类代理",
        description="AI 推断研究领域并自动分类（支持多标签分类和层次化分类）",
        icon="tag",
        color="#EC4899",  # 粉色
        capabilities=[
            "classify_domain",
            "assign_topics",
            "build_taxonomy",
            "suggest_categories"
        ],
        dependencies=[AgentType.LITERATURE_PARSE.value]
    ),
    AgentType.KNOWLEDGE_GRAPH: AgentDisplayInfo(
        name="Knowledge Graph Agent",
        name_cn="知识图谱代理",
        description="构建领域知识图谱（基于 LightRAG，支持实体关系抽取和可视化）",
        icon="git-graph",
        color="#14B8A6",  # 青色
        capabilities=[
            "build_graph",
            "query_relations",
            "visualize_graph",
            "discover_patterns"
        ],
        dependencies=[
            AgentType.LITERATURE_ANALYZE.value,
            AgentType.LITERATURE_CLASSIFY.value
        ]
    ),
    AgentType.PPT_GENERATE: AgentDisplayInfo(
        name="PPT Generate Agent",
        name_cn="PPT 生成代理",
        description="基于分析结果生成博士论文汇报 PPT（总分总结构，支持自定义模板）",
        icon="presentation",
        color="#EF4444",  # 红色
        capabilities=[
            "generate_outline",
            "create_slides",
            "export_pptx",
            "version_control"
        ],
        dependencies=[
            AgentType.LITERATURE_ANALYZE.value,
            AgentType.KNOWLEDGE_GRAPH.value
        ]
    ),
    AgentType.CITATION_MANAGE: AgentDisplayInfo(
        name="Citation Manage Agent",
        name_cn="引用管理代理",
        description="管理文献引用和格式化（支持多种引用格式：APA、MLA、Chicago 等）",
        icon="quote",
        color="#F97316",  # 深橙色
        capabilities=[
            "format_citation",
            "manage_references",
            "detect_duplicates",
            "export_bibliography"
        ],
        dependencies=[
            AgentType.LITERATURE_SEARCH.value,
            AgentType.LITERATURE_PARSE.value
        ]
    ),
}


def get_agent_display_info(agent_type: AgentType) -> AgentDisplayInfo:
    """获取 Agent 的显示信息

    Args:
        agent_type: Agent 类型

    Returns:
        AgentDisplayInfo: Agent 显示信息

    Raises:
        KeyError: 如果 Agent 类型不存在
    """
    return AGENT_REGISTRY[agent_type]


def list_all_agents() -> List[AgentType]:
    """列出所有可用的 Agent 类型

    Returns:
        List[AgentType]: Agent 类型列表
    """
    return list(AgentType)


def get_agent_dependencies(agent_type: AgentType) -> List[AgentType]:
    """获取 Agent 的依赖关系

    Args:
        agent_type: Agent 类型

    Returns:
        List[AgentType]: 依赖的 Agent 类型列表
    """
    info = get_agent_display_info(agent_type)
    deps = []
    for dep_str in info.dependencies:
        try:
            dep = AgentType(dep_str)
            deps.append(dep)
        except ValueError:
            # 忽略无效的依赖
            pass
    return deps


def validate_agent_workflow(agent_types: List[AgentType]) -> bool:
    """验证 Agent 工作流是否有效（检查依赖关系）

    Args:
        agent_types: Agent 类型列表（按执行顺序）

    Returns:
        bool: 工作流是否有效
    """
    executed = set()
    for agent_type in agent_types:
        # 检查依赖是否已执行
        deps = get_agent_dependencies(agent_type)
        for dep in deps:
            if dep not in executed:
                return False
        executed.add(agent_type)
    return True


# 有序列表：按照依赖关系排序的 Agent 列表
# 用于工作流编排和 UI 显示
ORDERED_AGENT_LIST: List[Dict[str, Any]] = [
    {
        "id": AgentType.LITERATURE_SEARCH,
        "name": AGENT_REGISTRY[AgentType.LITERATURE_SEARCH].name,
        "name_cn": AGENT_REGISTRY[AgentType.LITERATURE_SEARCH].name_cn,
        "icon": AGENT_REGISTRY[AgentType.LITERATURE_SEARCH].icon,
        "color": AGENT_REGISTRY[AgentType.LITERATURE_SEARCH].color,
    },
    {
        "id": AgentType.LITERATURE_DOWNLOAD,
        "name": AGENT_REGISTRY[AgentType.LITERATURE_DOWNLOAD].name,
        "name_cn": AGENT_REGISTRY[AgentType.LITERATURE_DOWNLOAD].name_cn,
        "icon": AGENT_REGISTRY[AgentType.LITERATURE_DOWNLOAD].icon,
        "color": AGENT_REGISTRY[AgentType.LITERATURE_DOWNLOAD].color,
    },
    {
        "id": AgentType.LITERATURE_PARSE,
        "name": AGENT_REGISTRY[AgentType.LITERATURE_PARSE].name,
        "name_cn": AGENT_REGISTRY[AgentType.LITERATURE_PARSE].name_cn,
        "icon": AGENT_REGISTRY[AgentType.LITERATURE_PARSE].icon,
        "color": AGENT_REGISTRY[AgentType.LITERATURE_PARSE].color,
    },
    {
        "id": AgentType.LITERATURE_ANALYZE,
        "name": AGENT_REGISTRY[AgentType.LITERATURE_ANALYZE].name,
        "name_cn": AGENT_REGISTRY[AgentType.LITERATURE_ANALYZE].name_cn,
        "icon": AGENT_REGISTRY[AgentType.LITERATURE_ANALYZE].icon,
        "color": AGENT_REGISTRY[AgentType.LITERATURE_ANALYZE].color,
    },
    {
        "id": AgentType.LITERATURE_CLASSIFY,
        "name": AGENT_REGISTRY[AgentType.LITERATURE_CLASSIFY].name,
        "name_cn": AGENT_REGISTRY[AgentType.LITERATURE_CLASSIFY].name_cn,
        "icon": AGENT_REGISTRY[AgentType.LITERATURE_CLASSIFY].icon,
        "color": AGENT_REGISTRY[AgentType.LITERATURE_CLASSIFY].color,
    },
    {
        "id": AgentType.KNOWLEDGE_GRAPH,
        "name": AGENT_REGISTRY[AgentType.KNOWLEDGE_GRAPH].name,
        "name_cn": AGENT_REGISTRY[AgentType.KNOWLEDGE_GRAPH].name_cn,
        "icon": AGENT_REGISTRY[AgentType.KNOWLEDGE_GRAPH].icon,
        "color": AGENT_REGISTRY[AgentType.KNOWLEDGE_GRAPH].color,
    },
    {
        "id": AgentType.PPT_GENERATE,
        "name": AGENT_REGISTRY[AgentType.PPT_GENERATE].name,
        "name_cn": AGENT_REGISTRY[AgentType.PPT_GENERATE].name_cn,
        "icon": AGENT_REGISTRY[AgentType.PPT_GENERATE].icon,
        "color": AGENT_REGISTRY[AgentType.PPT_GENERATE].color,
    },
    {
        "id": AgentType.CITATION_MANAGE,
        "name": AGENT_REGISTRY[AgentType.CITATION_MANAGE].name,
        "name_cn": AGENT_REGISTRY[AgentType.CITATION_MANAGE].name_cn,
        "icon": AGENT_REGISTRY[AgentType.CITATION_MANAGE].icon,
        "color": AGENT_REGISTRY[AgentType.CITATION_MANAGE].color,
    },
]
