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
AI 深度分析器

使用 GLM-5 API 进行文献深度分析。
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

try:
    from zhipuai import ZhipuAI
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False


class AIDeepAnalyzer:
    """AI 深度分析器

    使用 GLM-5 API 从 6 个维度深度分析文献。

    使用示例：
    ```python
    analyzer = AIDeepAnalyzer(api_key="your_api_key")

    # 分析创新点
    result = await analyzer.analyze(
        paper_content="# Paper Title\\n...",
        analysis_type="innovation"
    )

    # 支持的分析类型：
    # - innovation: 创新点分析（三元组：问题+方法+效果）
    # - motivation: 研究动机分析（5个关键问题）
    # - roadmap: 技术路线分析（方法演进）
    # - mechanism: 机理解析（原理深入）
    # - impact: 影响评估（学术+实践影响）
    # - history: 历史脉络（领域发展）
    ```
    """

    ANALYSIS_PROMPTS = {
        "innovation": """请深度分析以下学术文献的创新点，按照"创新点三元组"格式输出：

**文献内容：**
{content}

**分析要求：**
1. 识别文献的核心创新点（2-5个）
2. 对每个创新点，按照以下格式分析：
   - **问题（Problem）**：该创新点解决了什么具体问题？
   - **方法（Method）**：提出了什么新颖的方法或技术？
   - **效果（Effect）**：相比现有方法有什么显著改进？

**输出格式（JSON）：**
{{
  "innovations": [
    {{
      "id": 1,
      "title": "创新点标题",
      "problem": "解决的问题",
      "method": "提出的方法",
      "effect": "达到的效果",
      "evidence": "文献中的支撑证据（引用具体段落）",
      "novelty_score": 0.85,
      "significance": "high/medium/low"
    }}
  ],
  "overall_innovation_level": "high/medium/low",
  "key_contributions": ["贡献1", "贡献2"]
}}
""",

        "motivation": """请深度分析以下学术文献的研究动机，回答 5 个关键问题：

**文献内容：**
{content}

**分析要求：**
回答以下 5 个关键问题：
1. **Why Now?**：为什么在现在这个时间点研究这个问题？（时机）
2. **Why This?**：为什么选择这个具体问题？（重要性）
3. **Why So?**：为什么采用这种研究方法？（合理性）
4. **Why Not?**：为什么没有采用其他方法？（对比）
5. **What If?**：如果成功会有什么影响？（意义）

**输出格式（JSON）：**
{{
  "why_now": {{
    "answer": "时机分析",
    "evidence": "文献证据",
    "context": "领域背景"
  }},
  "why_this": {{
    "answer": "重要性分析",
    "evidence": "文献证据",
    "urgency": "high/medium/low"
  }},
  "why_so": {{
    "answer": "方法合理性",
    "evidence": "文献证据",
    "alternatives_considered": ["备选方法1", "备选方法2"]
  }},
  "why_not": {{
    "answer": "方法对比",
    "evidence": "文献证据",
    "limitations_of_others": ["其他方法的局限1", "局限2"]
  }},
  "what_if": {{
    "answer": "成功影响",
    "academic_impact": "学术影响",
    "practical_impact": "实践影响"
  }},
  "motivation_strength": "strong/medium/weak"
}}
""",

        "roadmap": """请分析以下学术文献的技术路线和方法演进：

**文献内容：**
{content}

**分析要求：**
1. 识别文献采用的主要技术路线
2. 分析方法的演进逻辑
3. 识别关键技术步骤
4. 评估技术可行性

**输出格式（JSON）：**
{{
  "main_approach": {{
    "name": "方法名称",
    "category": "方法类别",
    "description": "方法描述"
  }},
  "technical_steps": [
    {{
      "step_id": 1,
      "name": "步骤名称",
      "description": "步骤描述",
      "input": "输入",
      "output": "输出",
      "techniques": ["使用的技术1", "技术2"]
    }}
  ],
  "evolution_logic": {{
    "from_methods": ["演进自方法1", "方法2"],
    "improvements": ["改进点1", "改进点2"],
    "novel_combinations": ["新颖组合1", "组合2"]
  }},
  "feasibility": {{
    "score": 0.85,
    "complexity": "high/medium/low",
    "resource_requirements": "资源需求",
    "potential_challenges": ["挑战1", "挑战2"]
  }}
}}
""",

        "mechanism": """请深度解析以下学术文献的技术机理：

**文献内容：**
{content}

**分析要求：**
1. 解析核心机理和原理
2. 识别关键技术细节
3. 分析理论依据
4. 评估机理的创新性

**输出格式（JSON）：**
{{
  "core_mechanism": {{
    "name": "机理名称",
    "principle": "核心原理",
    "theoretical_basis": "理论依据"
  }},
  "key_components": [
    {{
      "component": "组件名称",
      "function": "功能",
      "implementation": "实现方式",
      "importance": "high/medium/low"
    }}
  ],
  "technical_details": {{
    "algorithms": ["算法1", "算法2"],
    "models": ["模型1", "模型2"],
    "data_structures": ["数据结构1", "数据结构2"]
  }},
  "innovation_analysis": {{
    "novel_mechanisms": ["新颖机理1", "机理2"],
    "improved_mechanisms": ["改进机理1", "机理2"],
    "mechanism_advantages": ["优势1", "优势2"]
  }}
}}
""",

        "impact": """请评估以下学术文献的影响：

**文献内容：**
{content}

**分析要求：**
1. 评估学术影响
2. 评估实践影响
3. 识别潜在应用场景
4. 评估长期价值

**输出格式（JSON）：**
{{
  "academic_impact": {{
    "score": 0.85,
    "contribution_areas": ["贡献领域1", "领域2"],
    "potential_citations": "high/medium/low",
    "influence_on_field": "领域影响描述"
  }},
  "practical_impact": {{
    "score": 0.80,
    "application_areas": ["应用领域1", "领域2"],
    "industry_relevance": "high/medium/low",
    "implementation_feasibility": "feasibility描述"
  }},
  "potential_applications": [
    {{
      "application": "应用场景",
      "domain": "应用领域",
      "readiness": "ready/near-term/long-term",
      "challenges": ["挑战1", "挑战2"]
    }}
  ],
  "long_term_value": {{
    "sustainability": "high/medium/low",
    "extension_potential": "扩展潜力",
    "future_directions": ["未来方向1", "方向2"]
  }}
}}
""",

        "history": """请分析以下学术文献在领域历史脉络中的位置：

**文献内容：**
{content}

**分析要求：**
1. 识别文献在领域发展中的位置
2. 分析历史演进脉络
3. 识别关键里程碑文献
4. 预测未来发展趋势

**输出格式（JSON）：**
{{
  "historical_position": {{
    "era": "时代（如：深度学习时代）",
    "stage": "阶段（如：成熟期、发展期）",
    "significance": "历史意义"
  }},
  "evolution_context": {{
    "predecessors": [
      {{
        "work": "前序工作",
        "year": 2020,
        "contribution": "贡献",
        "relationship": "关系"
      }}
    ],
    "contemporaries": [
      {{
        "work": "同期工作",
        "year": 2023,
        "similarity": "相似点",
        "difference": "差异点"
      }}
    ]
  }},
  "key_milestones": [
    {{
      "milestone": "里程碑事件",
      "year": 2020,
      "significance": "意义"
    }}
  ],
  "future_trends": {{
    "predicted_directions": ["预测方向1", "方向2"],
    "emerging_challenges": ["新兴挑战1", "挑战2"],
    "research_opportunities": ["研究机会1", "机会2"]
  }}
}}
"""
    }

    def __init__(self, api_key: str = None, model: str = "glm-5"):
        """初始化 AI 分析器

        Args:
            api_key: GLM API 密钥（可从环境变量读取）
            model: 使用的模型（默认：glm-5）
        """
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 初始化客户端
        if ZHIPU_AVAILABLE and api_key:
            self.client = ZhipuAI(api_key=api_key)
        else:
            self.client = None
            self.logger.warning("智谱 AI SDK 未安装或 API 密钥未提供，AI 分析功能将不可用")

        # 串行队列（确保 API 调用串行执行）
        self._api_queue = asyncio.Queue()
        self._queue_processor_task = None

    async def analyze(
        self,
        paper_content: str,
        analysis_type: str
    ) -> Dict[str, Any]:
        """执行分析

        Args:
            paper_content: 文献内容（Markdown 格式）
            analysis_type: 分析类型

        Returns:
            分析结果
        """
        if analysis_type not in self.ANALYSIS_PROMPTS:
            raise ValueError(f"不支持的分析类型: {analysis_type}")

        if not self.client:
            raise RuntimeError("AI 客户端未初始化，无法执行分析")

        self.logger.info(f"开始 {analysis_type} 分析")

        # 构建提示词
        prompt = self.ANALYSIS_PROMPTS[analysis_type].format(content=paper_content[:8000])  # 限制长度

        try:
            # 调用 API（通过串行队列）
            response = await self._call_api_with_queue(prompt)

            # 解析结果
            result = self._parse_response(response, analysis_type)

            self.logger.info(f"{analysis_type} 分析完成")
            return result

        except Exception as e:
            self.logger.error(f"{analysis_type} 分析失败: {e}")
            raise

    async def _call_api_with_queue(self, prompt: str) -> str:
        """通过串行队列调用 API

        Args:
            prompt: 提示词

        Returns:
            API 响应
        """
        # 创建 Future
        future = asyncio.Future()

        # 加入队列
        await self._api_queue.put((prompt, future))

        # 启动队列处理器（如果未启动）
        if not self._queue_processor_task or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_queue())

        # 等待结果
        return await future

    async def _process_queue(self):
        """处理 API 调用队列（串行执行）"""
        while True:
            try:
                # 获取任务
                prompt, future = await self._api_queue.get()

                try:
                    # 调用 API
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=2000
                    )

                    # 返回结果
                    result_text = response.choices[0].message.content
                    future.set_result(result_text)

                except Exception as e:
                    future.set_exception(e)

                finally:
                    self._api_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"队列处理错误: {e}")

    def _parse_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """解析 API 响应

        Args:
            response: API 响应文本
            analysis_type: 分析类型

        Returns:
            解析后的结果
        """
        try:
            # 尝试提取 JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                # 添加元数据
                result["analysis_type"] = analysis_type
                result["analyzed_at"] = datetime.now().isoformat()

                return result
            else:
                raise ValueError("响应中未找到有效的 JSON")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            # 返回原始响应
            return {
                "analysis_type": analysis_type,
                "raw_response": response,
                "parse_error": str(e),
                "analyzed_at": datetime.now().isoformat()
            }

    async def batch_analyze(
        self,
        paper_contents: List[str],
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """批量分析

        Args:
            paper_contents: 文献内容列表
            analysis_type: 分析类型

        Returns:
            分析结果列表
        """
        results = []
        for i, content in enumerate(paper_contents):
            try:
                result = await self.analyze(content, analysis_type)
                results.append(result)
                self.logger.info(f"批量分析进度: {i+1}/{len(paper_contents)}")
            except Exception as e:
                results.append({
                    "error": str(e),
                    "status": "failed",
                    "index": i
                })

        return results

    def validate_api_key(self) -> bool:
        """验证 API 密钥

        Returns:
            是否有效
        """
        if not self.client:
            return False

        try:
            # 发送测试请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "测试"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            self.logger.error(f"API 密钥验证失败: {e}")
            return False
