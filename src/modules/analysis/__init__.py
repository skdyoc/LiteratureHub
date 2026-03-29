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
第2部分：文献分析模块

基于 Wind-Aero-Literature-Analysis-System 的核心逻辑
支持双层并发分析（10篇论文 × 5个分析器 = 50并发）
"""

from .api.deepseek_client import DeepSeekClient, DeepSeekParallelAnalyzer
from .core.database import LiteratureDatabase
from .core.paper import Paper

__all__ = [
    "DeepSeekClient",
    "DeepSeekParallelAnalyzer",
    "LiteratureDatabase",
    "Paper",
]
