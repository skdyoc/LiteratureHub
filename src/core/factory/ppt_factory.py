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
第3部分：PPT 生成 Agent 工厂

基于 Eigent Multi-Agent 架构
"""

from typing import Dict, Any, List
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.agents import (
    LiteratureAgent,
    AgentCapability,
    AgentType,
)
from src.core.tools.base import BaseToolkit
from src.modules.ppt import (
    ContentExtractor,
    OverviewAgent,
)


class LiteraturePPTAgent(LiteratureAgent):
    """
    PPT 内容生成 Agent

    基于 Wind-Aero-Literature-PPT-Helper 的三阶段流程
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            name="LiteraturePPTAgent",
            agent_type=AgentType.PPT_GENERATE,
            description="基于文献分析结果生成博士论文汇报PPT内容",
            config=config,
        )

        # 配置
        self.api_keys_file = config.get("glm_api_keys_file", "config/api_keys.txt")
        self.model = config.get("model", "glm-4-plus")
        self.agent_results_path = config.get(
            "agent_results_path",
            "D:/xfs/phd/github项目/Wind-Aero-Literature-Analysis-System/data/agent_results"
        )

        # 输出目录
        self.output_dir = Path(config.get("ppt_output_dir", "data/ppt_content"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_capabilities(self) -> List[AgentCapability]:
        """返回 Agent 能力列表"""
        return [
            AgentCapability(
                name="PPT内容生成",
                description="基于文献分析结果生成符合博士论文汇报标准的PPT内容",
                required_tools=["agent_results"],
            ),
        ]

    def get_required_tools(self) -> List[BaseToolkit]:
        """返回需要的工具列表"""
        return []

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 PPT 内容生成

        Args:
            input_data: 包含以下字段
                - phase: 执行哪个阶段（1/2/3）
                - min_domains: 最小领域数（可选）
                - max_domains: 最大领域数（可选）
                - max_papers: 最大文献数（可选）

        Returns:
            生成结果
        """
        phase = input_data.get("phase", 1)

        if phase == 1:
            return self._phase1_overview(input_data)
        elif phase == 2:
            return self._phase2_domain_analysis(input_data)
        elif phase == 3:
            return self._phase3_summary(input_data)
        else:
            return {
                "success": False,
                "error": f"无效的阶段: {phase}",
            }

    def _phase1_overview(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: 概览分析（总）"""
        try:
            # 准备数据
            extractor = ContentExtractor(
                agent_results_path=self.agent_results_path
            )
            paper_ids = extractor.get_available_paper_ids()

            max_papers = input_data.get("max_papers", 100)
            summaries = extractor.extract_all_summaries(paper_ids[:max_papers])
            agent_summaries = list(summaries.values())

            # 执行分析
            agent = OverviewAgent(
                keys_file=self.api_keys_file,
                model=self.model
            )

            min_domains = input_data.get("min_domains", 5)
            max_domains = input_data.get("max_domains", 10)

            input_data_agent = {
                "agent_results_summaries": agent_summaries,
                "min_domains": min_domains,
                "max_domains": max_domains,
            }

            result = agent.analyze(input_data_agent)

            # 保存结果
            output_file = self.output_dir / "phase1_overview.json"
            agent.save_result(result, str(output_file))

            return {
                "success": True,
                "phase": "overview",
                "result": result,
                "output_file": str(output_file),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _phase2_domain_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: 领域深度分析（分）"""
        # TODO: 实现领域深度分析
        return {
            "success": False,
            "error": "Phase 2 尚未完全实现",
        }

    def _phase3_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: 综合总结（总）"""
        # TODO: 实现综合总结
        return {
            "success": False,
            "error": "Phase 3 尚未完全实现",
        }


class LiteraturePPTAgentFactory:
    """PPT 生成 Agent 工厂"""

    @staticmethod
    def create_agent(config: Dict[str, Any]) -> LiteraturePPTAgent:
        """
        创建 PPT 生成 Agent

        Args:
            config: 配置字典

        Returns:
            LiteraturePPTAgent 实例
        """
        return LiteraturePPTAgent(config)


# 注册到工厂系统
__all__ = [
    "LiteraturePPTAgent",
    "LiteraturePPTAgentFactory",
]
