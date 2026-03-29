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
文献分析模块

提供 AI 驱动的深度文献分析、评分和分类功能。
"""

from .manager import AnalysisManager
from .ai_analyzer import AIDeepAnalyzer
from .scoring import ScoringSystem
from .classifier import DomainClassifier

__all__ = [
    'AnalysisManager',
    'AIDeepAnalyzer',
    'ScoringSystem',
    'DomainClassifier'
]
