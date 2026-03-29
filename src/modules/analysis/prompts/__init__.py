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
Analysis Prompts 模块

包含5个分析器的 Prompt 模板
"""

import os
from pathlib import Path

# 获取 prompts 目录
PROMPTS_DIR = Path(__file__).parent


def load_prompt(prompt_name: str) -> str:
    """
    加载 Prompt 模板

    Args:
        prompt_name: Prompt 文件名（不含扩展名）
                     例如: "innovation_analyzer"

    Returns:
        Prompt 内容字符串
    """
    prompt_file = PROMPTS_DIR / f"{prompt_name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


# 可用的 Prompt 列表
AVAILABLE_PROMPTS = [
    "innovation_analyzer",
    "motivation_detector",
    "roadmap_analyzer",
    "mechanism_analyzer",
    "impact_assessor",
]

__all__ = [
    "load_prompt",
    "AVAILABLE_PROMPTS",
]
