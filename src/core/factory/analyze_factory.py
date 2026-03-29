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
文献分析 Agent 工厂实现

展示如何使用工厂模式创建具体的 Agent。
"""

from typing import List, Dict, Any
from pathlib import Path
import json
import logging

from ..agents.types import AgentType
from .base import BaseAgentFactory, register_agent_factory, LiteratureAgent
from ..tools.note import NoteTakingToolkit
from ...prompts.agent_prompts import LITERATURE_ANALYZE_AGENT_PROMPT, LITERATURE_CLASSIFY_AGENT_PROMPT


logger = logging.getLogger(__name__)


@register_agent_factory(AgentType.LITERATURE_ANALYZE)
class LiteratureAnalyzeAgentFactory(BaseAgentFactory):
    """文献分析 Agent 工厂

    基于 Eigent 的 developer_agent 工厂设计。
    """

    def __init__(self, agent_type: AgentType, api_client, config: dict = None):
        """
        Args:
            agent_type: Agent 类型
            api_client: GLMAPIClient 实例
            config: 配置字典，必须包含 analyze_type
        """
        super().__init__(agent_type, api_client, config)
        self.analyze_type = config.get("analyze_type", "innovation") if config else "innovation"
        self.working_directory = config.get("working_directory", "data/projects") if config else "data/projects"

    def get_system_prompt(self) -> str:
        """获取 System Prompt

        使用结构化的 XML 标签格式，基于 Eigent 的 prompt.py 设计。
        """
        return LITERATURE_ANALYZE_AGENT_PROMPT.format(
            analyze_type=self.analyze_type,
            working_directory=self.working_directory,
        )

    def register_toolkits(self) -> None:
        """注册工具集

        基于 Eigent 的 toolkit 模式：
        - NoteTakingToolkit: 用于记录和共享分析结果
        - LiteratureQueryToolkit: 用于查询文献内容
        """
        # 1. NoteTakingToolkit - 记录和共享分析结果
        note_toolkit = NoteTakingToolkit(
            agent_name=self.agent_type.value,
            working_directory=self.working_directory,
        )
        self.toolkits.append(note_toolkit)

        # 2. LiteratureQueryToolkit - 查询文献内容
        query_toolkit = LiteratureQueryToolkit()
        self.toolkits.append(query_toolkit)

    def get_analyze_type(self) -> str:
        """获取分析类型"""
        return self.analyze_type

    def set_analyze_type(self, analyze_type: str):
        """设置分析类型

        Args:
            analyze_type: 分析类型（innovation, motivation, mechanism, etc.）
        """
        self.analyze_type = analyze_type


# 其他 Agent 工厂类型

@register_agent_factory(AgentType.LITERATURE_SEARCH)
class LiteratureSearchAgentFactory(BaseAgentFactory):
    """文献搜索 Agent 工厂"""

    def get_system_prompt(self) -> str:
        return """\
<role>
你是一位专业的学术文献搜索专家，擅长使用多个学术数据库搜索相关文献。
</role>

<capabilities>
- 搜索 Elsevier、IEEE、Springer、arXiv 等数据库
- 根据关键词和筛选条件精确搜索
- 去重和合并搜索结果
- 导出多种格式的搜索结果
</capabilities>
"""

    def register_toolkits(self) -> None:
        """注册文献搜索相关的工具集

        实现说明：
        - 注册学术数据库搜索工具
        - 注册文件下载工具
        - 注册搜索结果管理工具
        """
        # 导入工具集（如果可用）
        try:
            from src.core.tools.literature import LiteratureSearchToolkit
            self.toolkits.append(LiteratureSearchToolkit())
        except ImportError:
            # 如果工具集未实现，记录警告
            import logging
            logging.warning("LiteratureSearchToolkit 未实现，跳过注册")


@register_agent_factory(AgentType.PPT_GENERATE)
class PPTGenerateAgentFactory(BaseAgentFactory):
    """PPT 生成 Agent 工厂"""

    def get_system_prompt(self) -> str:
        return """\
<role>
你是一位专业的学术 PPT 制作专家，擅长将文献分析结果转化为清晰的汇报材料。
</role>

<capabilities>
- 总分总结构组织内容
- 提炼关键创新点
- 设计清晰的逻辑流程
- 使用专业的学术语言
</capabilities>
"""

    def register_toolkits(self) -> None:
        """注册 PPT 生成相关的工具集

        实现说明：
        - 注册PPT模板管理工具
        - 注册幻灯片生成工具
        - 注册版本控制工具
        """
        # 导入工具集（如果可用）
        try:
            from src.core.tools.ppt import PPTGenerationToolkit
            self.toolkits.append(PPTGenerationToolkit())
        except ImportError:
            # 如果工具集未实现，记录警告
            import logging
            logging.warning("PPTGenerationToolkit 未实现，跳过注册")


# ==================== 文献分类 Agent ====================

class LiteratureClassifyAgent(LiteratureAgent):
    """文献分类 Agent

    基于文献的标题、摘要和关键词，使用 AI 模型进行领域分类。

    输入：metadata 中的 title, abstract, keywords
    输出：primary_domain, secondary_domains, subdomains, confidence
    """

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行分类任务

        Args:
            task: 任务字典，包含：
                - paper_metadata: 文献元数据（title, abstract, keywords）
                - paper_id: 文献 ID（可选）

        Returns:
            分类结果字典
        """
        paper_metadata = task.get("paper_metadata", {})
        paper_id = task.get("paper_id", "unknown")

        # 提取必要字段
        title = paper_metadata.get("title", "")
        abstract = paper_metadata.get("abstract", "")
        keywords = paper_metadata.get("keywords", [])

        # 构造输入消息
        user_message = f"""请对以下文献进行分类：

标题（Title）：{title}

摘要（Abstract）：{abstract}

关键词：{', '.join(keywords) if keywords else 'N/A'}

请严格按照指定的 JSON 格式输出分类结果。"""

        # 调用 AI 模型
        try:
            response = await self.model.generate(
                system_message=self.system_message,
                user_message=user_message
            )

            # 解析 AI 返回的 JSON
            classification_result = self._parse_classification_result(response)

            # 添加元数据
            classification_result["paper_id"] = paper_id
            classification_result["input_title"] = title

            logger.info(f"文献 {paper_id} 分类完成: {classification_result.get('primary_domain', 'Unknown')}")
            return classification_result

        except Exception as e:
            logger.error(f"文献 {paper_id} 分类失败: {e}")
            return {
                "paper_id": paper_id,
                "input_title": title,
                "primary_domain": "Unclassified",
                "primary_domain_cn": "未分类",
                "confidence": 0.0,
                "error": str(e)
            }

    def _parse_classification_result(self, response: str) -> Dict[str, Any]:
        """解析 AI 返回的分类结果

        Args:
            response: AI 模型返回的文本（应该包含 JSON）

        Returns:
            解析后的分类结果字典
        """
        # 尝试提取 JSON
        import re

        # 查找 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 如果没有代码块，尝试直接解析
            json_str = response.strip()

        # 解析 JSON
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 尝试修复")

            # 简单的修复尝试：移除可能的 markdown 残留
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)

            try:
                result = json.loads(json_str)
                return result
            except:
                # 如果仍然失败，返回默认结果
                logger.error(f"无法解析 AI 返回结果: {response[:200]}...")
                return {
                    "primary_domain": "Unclassified",
                    "primary_domain_cn": "未分类",
                    "secondary_domains": [],
                    "subdomains": [],
                    "confidence": 0.0,
                    "reasoning": "JSON 解析失败",
                    "key_indicators": {}
                }


@register_agent_factory(AgentType.LITERATURE_CLASSIFY)
class LiteratureClassifyAgentFactory(BaseAgentFactory):
    """文献分类 Agent 工厂

    创建基于 AI 的文献分类 Agent。
    """

    def __init__(self, agent_type: AgentType, api_client, config: dict = None):
        """
        Args:
            agent_type: Agent 类型（应该是 LITERATURE_CLASSIFY）
            api_client: GLMAPIClient 实例
            config: 配置字典
        """
        super().__init__(agent_type, api_client, config)

    def get_system_prompt(self) -> str:
        """获取 System Prompt"""
        return LITERATURE_CLASSIFY_AGENT_PROMPT

    def register_toolkits(self) -> None:
        """注册工具集

        分类 Agent 不需要特殊的工具集。
        如果需要保存分类结果，可以注册 NoteTakingToolkit。
        """
        # 可选：注册 NoteTakingToolkit 用于记录分类结果
        # working_dir = self.config.get("working_directory", "data/projects") if self.config else "data/projects"
        # note_toolkit = NoteTakingToolkit(
        #     agent_name=self.agent_type.value,
        #     working_directory=working_dir,
        # )
        # self.toolkits.append(note_toolkit)
        pass

    def create_agent(self) -> LiteratureAgent:
        """创建文献分类 Agent

        覆盖父类方法，返回 LiteratureClassifyAgent 实例。
        """
        # 获取 System Prompt
        system_message = self.get_system_prompt()

        # 注册工具（如果需要）
        self.register_toolkits()

        # 构建工具列表
        tools = self._build_tools()

        # 创建 ClassifyAgent
        agent = LiteratureClassifyAgent(
            agent_type=self.agent_type,
            system_message=system_message,
            model=self.api_client,
            tools=tools,
        )

        return agent
