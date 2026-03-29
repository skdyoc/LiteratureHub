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
KeywordTranslationAgent - 中文关键词智能翻译 Agent

使用 LLM（GLM API）将用户输入的中文关键词智能翻译为学术英文关键词，
以便在 Elsevier API 搜索中使用。

核心特点：
    1. Agent 驱动：使用 LLM 进行智能翻译，而非硬编码字典
    2. 学术领域适配：Prompt 引导 LLM 输出学术标准用语
    3. 缓存机制：已翻译的关键词会被缓存，避免重复调用 API
    4. 回退机制：API 不可用时回退到基础规则翻译
    5. 自动语言检测：纯英文关键词直接放行
"""

import json
import logging
import re
import yaml
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("KeywordTranslator")

# 缓存目录
_cache_dir = Path(__file__).parent.parent / "data" / "cache" / "keyword_translations"
_cache_dir.mkdir(parents=True, exist_ok=True)

# 配置文件路径
_config_file = Path(__file__).parent.parent.parent / "config" / "api_keys.yaml"

# 基础学术词典（回退模式使用）
_FALLBACK_DICT = {
    # 风能领域
    "大型风机": "large-scale wind turbine",
    "风力发电机": "wind turbine",
    "风机": "wind turbine",
    "风电": "wind power",
    "风力发电": "wind power generation",
    "海上风电": "offshore wind power",
    "陆上风电": "onshore wind power",
    "气动": "aerodynamic",
    "气动性能": "aerodynamic performance",
    "气动特性": "aerodynamic characteristics",
    "气动优化": "aerodynamic optimization",
    "气动设计": "aerodynamic design",
    "叶片": "blade",
    "叶片设计": "blade design",
    "翼型": "airfoil",
    "尾流": "wake",
    "尾流效应": "wake effect",
    "尾流模型": "wake model",
    "升力": "lift",
    "阻力": "drag",
    "失速": "stall",
    "涡": "vortex",
    "湍流": "turbulence",
    "计算流体力学": "CFD",
    "CFD": "CFD",
    "数值模拟": "numerical simulation",
    "性能预测": "performance prediction",
    "功率曲线": "power curve",
    "发电量": "power output",
    "风速": "wind speed",
    "风场": "wind farm",
    "布局优化": "layout optimization",

    # 通用学术
    "优化": "optimization",
    "设计": "design",
    "分析": "analysis",
    "研究": "research",
    "性能": "performance",
    "模型": "model",
    "方法": "method",
    "系统": "system",
    "控制": "control",
    "实验": "experiment",
    "测试": "test",
    "评估": "evaluation",
    "改进": "improvement",
    "应用": "application",
    "发展": "development",
}

# 系统提示词
_SYSTEM_PROMPT = """你是一位专业的学术关键词翻译助手。你的任务是将用户输入的中文关键词翻译为适合在学术数据库（如 Elsevier Scopus）中搜索的英文关键词。

翻译规则：
1. 输出必须是学术文献中常用的标准英文术语
2. 如果输入已经是英文，直接返回原词
3. 对于复合词，保持为一个完整短语（如"大型风机" -> "large-scale wind turbine"）
4. 不要添加解释或多余内容
5. 如果输入包含多个关键词（用逗号分隔），每个关键词单独翻译
6. 翻译应考虑学术搜索场景，优先使用在论文标题和摘要中常见的表达方式

示例：
- 大型风机 -> large-scale wind turbine
- 气动性能 -> aerodynamic performance
- 海上风电 -> offshore wind power
- 叶片优化设计 -> blade design optimization
- 机器学习, 神经网络 -> machine learning, neural network
- wind turbine aerodynamic -> wind turbine aerodynamic（英文直接返回）"""


class KeywordTranslationAgent:
    """中文关键词智能翻译 Agent

    使用 LLM API 将中文关键词翻译为学术英文关键词。
    """

    def __init__(self, api_key: str = None):
        """初始化翻译 Agent

        Args:
            api_key: GLM API 密钥（可选，不提供则自动从配置文件读取）
        """
        self.logger = logging.getLogger("KeywordTranslator")

        # API 密钥优先级：参数 > 配置文件 > None
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_api_key_from_config()

        self._cache = self._load_cache()
        self._client = None

        # 尝试初始化 LLM 客户端
        if self.api_key:
            self._init_client()

    def _load_api_key_from_config(self) -> Optional[str]:
        """从配置文件加载 API 密钥

        Returns:
            API 密钥，失败返回 None
        """
        try:
            if not _config_file.exists():
                return None

            with open(_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 读取 GLM API 密钥
            glm_config = config.get('glm', {})
            api_keys = glm_config.get('api_keys', [])

            if api_keys and api_keys[0] != 'your_glm_api_key_1':
                key = api_keys[0].strip()
                self.logger.info("已从配置文件加载 GLM API 密钥")
                return key

        except Exception as e:
            self.logger.warning(f"从配置文件加载 API 密钥失败: {e}")

        return None

    def _init_client(self):
        """初始化 LLM 客户端"""
        try:
            from zhipuai import ZhipuAI
            self._client = ZhipuAI(api_key=self.api_key)
            self._model = "glm-4-plus"  # GLM-4.7 对应的模型名称
            self.logger.info("GLM-4.7 翻译 Agent 初始化成功")
        except ImportError:
            self.logger.warning("zhipuai 未安装，翻译 Agent 将使用回退模式")
            self._client = None
        except Exception as e:
            self.logger.warning(f"GLM 客户端初始化失败: {e}，将使用回退模式")
            self._client = None

    def _load_cache(self) -> dict:
        """加载翻译缓存"""
        cache_file = _cache_dir / "translations.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """保存翻译缓存"""
        cache_file = _cache_dir / "translations.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")

    @staticmethod
    def _is_english(text: str) -> bool:
        """判断文本是否为纯英文"""
        return bool(re.match(r"^[a-zA-Z0-9\s\-_.,]+$", text.strip()))

    def _translate_via_llm(self, keyword: str) -> Optional[str]:
        """通过 LLM 翻译关键词

        Args:
            keyword: 待翻译的关键词

        Returns:
            翻译后的英文关键词，失败返回 None
        """
        if not self._client:
            return None

        try:
            response = self._client.chat.completions.create(
                model=getattr(self, '_model', 'glm-4-plus'),  # GLM-4.7
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"翻译以下关键词为学术英文: {keyword}"},
                ],
                temperature=0.1,
                max_tokens=256,
            )

            result = response.choices[0].message.content.strip()
            # 清理可能的多余内容
            result = result.strip("\"'").strip()

            if result:
                self.logger.info(f"LLM 翻译: {keyword} -> {result}")
                return result

        except Exception as e:
            self.logger.warning(f"LLM 翻译失败: {e}")

        return None

    def _fallback_translate(self, keyword: str) -> str:
        """基础回退翻译（无 API 时使用）

        使用内置学术词典 + 简单规则翻译。

        Args:
            keyword: 待翻译的关键词

        Returns:
            翻译后的关键词
        """
        if self._is_english(keyword):
            return keyword

        # 1. 尝试精确匹配词典
        if keyword in _FALLBACK_DICT:
            return _FALLBACK_DICT[keyword]

        # 2. 尝试分词匹配（处理复合词）
        result = keyword
        for cn, en in _FALLBACK_DICT.items():
            if cn in result:
                result = result.replace(cn, f" {en} ")

        # 3. 清理并返回
        result = result.strip()
        # 如果完全没有匹配，返回原词（但已记录警告）
        if result == keyword:
            self.logger.warning(f"回退词典未找到翻译: {keyword}")

        return result

    def translate_keyword(self, keyword: str) -> str:
        """翻译单个关键词

        流程：缓存 -> LLM -> 回退

        Args:
            keyword: 输入关键词（中文或英文）

        Returns:
            英文关键词
        """
        keyword = keyword.strip()
        if not keyword:
            return keyword

        # 纯英文直接放行
        if self._is_english(keyword):
            return keyword

        # 检查缓存
        if keyword in self._cache:
            self.logger.debug(f"缓存命中: {keyword} -> {self._cache[keyword]}")
            return self._cache[keyword]

        # 尝试 LLM 翻译
        result = self._translate_via_llm(keyword)
        if result:
            self._cache[keyword] = result
            self._save_cache()
            return result

        # 回退
        fallback = self._fallback_translate(keyword)
        self.logger.info(f"回退翻译: {keyword} -> {fallback}")
        return fallback

    def translate_keywords(self, keywords: List[str]) -> List[str]:
        """翻译关键词列表（公共接口）

        Args:
            keywords: 关键词列表（支持中英文混合）

        Returns:
            英文关键词列表（保持原顺序）
        """
        translated = []
        for kw in keywords:
            t = self.translate_keyword(kw)
            translated.append(t)
            if t != kw:
                self.logger.info(f"翻译: {kw} -> {t}")
        return translated
