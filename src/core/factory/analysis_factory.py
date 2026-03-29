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
第2部分：文献分析 Agent 工厂

基于 Eigent Multi-Agent 架构
"""

from typing import Dict, Any, List, Optional
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
from src.modules.analysis import (
    DeepSeekParallelAnalyzer,
    LiteratureDatabase,
)


class LiteratureAnalyzeAgent(LiteratureAgent):
    """
    文献深度分析 Agent

    基于 Wind-Aero-Literature-Analysis-System 的双层并发分析逻辑
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            name="LiteratureAnalyzeAgent",
            agent_type=AgentType.ANALYSIS,
            description="对文献进行AI深度分析（创新点、动机、路线、机理、影响）",
            config=config,
        )

        # 初始化 DeepSeek 并行分析器
        api_keys_file = config.get("deepseek_api_keys_file",
                                   "D:/xfs/phd/.私人信息/deepseek_api_keys_encrypted.txt")
        password = config.get("deepseek_password", "2580")
        max_workers = config.get("max_concurrent_analyzers", 5)

        try:
            self.analyzer = DeepSeekParallelAnalyzer(
                api_keys_file=api_keys_file,
                password=password,
                max_workers=max_workers,
            )
        except Exception as e:
            print(f"⚠️ DeepSeek API 客户端初始化失败: {e}")
            self.analyzer = None

        # 数据库路径
        self.db_path = config.get("database_path", "data/literature.db")

        # 输出目录
        self.output_dir = Path(config.get("output_dir", "data/agent_results"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_capabilities(self) -> List[AgentCapability]:
        """返回 Agent 能力列表"""
        return [
            AgentCapability(
                name="深度分析",
                description="对文献进行5维度AI分析（创新点、动机、路线、机理、影响）",
                required_tools=["metadata"],
            ),
        ]

    def get_required_tools(self) -> List[BaseToolkit]:
        """返回需要的工具列表"""
        return []

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文献深度分析

        Args:
            input_data: 包含以下字段
                - max_papers: 最大分析数量（可选）
                - skip_completed: 是否跳过已完成的分析（可选）
                - ranked_papers: 评分排名数据（可选）

        Returns:
            分析统计信息
        """
        if not self.analyzer:
            return {
                "success": False,
                "error": "DeepSeek API 客户端未初始化",
            }

        # 导入协调器
        from src.modules.analysis.core.coordinator import AgentAnalysisCoordinatorV2

        # 创建协调器
        coordinator = AgentAnalysisCoordinatorV2(
            database_path=self.db_path,
            output_dir=str(self.output_dir),
            max_concurrent_papers=10,
            max_concurrent_analyzers=5,
        )

        # 执行分析
        max_papers = input_data.get("max_papers", 10)
        skip_completed = input_data.get("skip_completed", True)
        ranked_papers = input_data.get("ranked_papers", None)

        stats = coordinator.batch_analyze(
            max_papers=max_papers,
            skip_completed=skip_completed,
            ranked_papers=ranked_papers,
        )

        return {
            "success": True,
            "stats": stats,
        }


class LiteratureAnalyzeAgentFactory:
    """文献分析 Agent 工厂"""

    @staticmethod
    def create_agent(config: Dict[str, Any]) -> LiteratureAnalyzeAgent:
        """
        创建文献分析 Agent

        Args:
            config: 配置字典

        Returns:
            LiteratureAnalyzeAgent 实例
        """
        return LiteratureAnalyzeAgent(config)


# 注册到工厂系统
__all__ = [
    "LiteratureAnalyzeAgent",
    "LiteratureAnalyzeAgentFactory",
]
