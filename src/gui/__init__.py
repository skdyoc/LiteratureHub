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
GUI 模块

提供统一的图形用户界面，包括：
- 主窗口（MainWindow）
- 项目管理面板（ProjectPanel）
- 工作流面板（WorkflowPanel）
- 配置面板（ConfigPanel）
- 监控面板（MonitorPanel）
"""

from .manager import GUIManager
from .main_window import MainWindow

__all__ = [
    'GUIManager',
    'MainWindow',
]
