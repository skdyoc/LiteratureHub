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
工作流引擎模块

提供任务编排和依赖管理，包括：
- WorkflowEngine（工作流引擎）
- TaskOrchestrator（任务编排器）
- DependencyManager（依赖管理器）
- StateTracker（状态追踪器）
- BatchPaperClassifier（批量文献分类器）
"""

from .engine import WorkflowEngine
from .batch_classify import BatchPaperClassifier

__all__ = [
    'WorkflowEngine',
    'BatchPaperClassifier',
]
