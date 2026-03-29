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
GUI 对话框组件

提供各种对话框组件。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path


class ProgressDialog(tk.Toplevel):
    """进度对话框

    显示长时间操作的进度。

    使用示例：
    ```python
    dialog = ProgressDialog(parent, title="导入文献", total=100)
    dialog.update_progress(50, "正在处理第 50 篇...")
    dialog.close()
    ```
    """

    def __init__(self, parent, title: str = "处理中", total: int = 100):
        """初始化进度对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            total: 总数
        """
        super().__init__(parent)

        self.title(title)
        self.total = total
        self.current = 0

        # 设置为模态对话框
        self.transient(parent)
        self.grab_set()

        # 创建组件
        self._create_widgets()

        # 居中显示
        self._center_window()

    def _create_widgets(self):
        """创建界面组件"""
        # 消息标签
        self.message_label = ttk.Label(self, text="准备中...")
        self.message_label.pack(pady=10, padx=20)

        # 进度条
        self.progress_bar = ttk.Progressbar(
            self,
            mode='determinate',
            length=300,
            maximum=self.total
        )
        self.progress_bar.pack(pady=10, padx=20)

        # 百分比标签
        self.percent_label = ttk.Label(self, text="0%")
        self.percent_label.pack(pady=5)

        # 取消按钮
        self.cancel_button = ttk.Button(self, text="取消", command=self._on_cancel)
        self.cancel_button.pack(pady=10)

        self.cancelled = False

    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def update_progress(self, current: int, message: str = None):
        """更新进度

        Args:
            current: 当前进度
            message: 消息（可选）
        """
        self.current = current
        self.progress_bar['value'] = current

        percent = int((current / self.total) * 100) if self.total > 0 else 0
        self.percent_label.config(text=f"{percent}%")

        if message:
            self.message_label.config(text=message)

        self.update_idletasks()

    def _on_cancel(self):
        """取消按钮回调"""
        self.cancelled = True
        self.grab_release()
        self.destroy()

    def close(self):
        """关闭对话框"""
        self.grab_release()
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """设置对话框

    编辑应用程序设置。

    使用示例：
    ```python
    dialog = SettingsDialog(parent, current_settings)
    if dialog.result:
        apply_settings(dialog.result)
    ```
    """

    def __init__(self, parent, current_settings: Dict[str, Any] = None):
        """初始化设置对话框

        Args:
            parent: 父窗口
            current_settings: 当前设置
        """
        super().__init__(parent)

        self.title("设置")
        self.current_settings = current_settings or {}
        self.result = None

        # 设置为模态对话框
        self.transient(parent)
        self.grab_set()

        # 创建组件
        self._create_widgets()

        # 居中显示
        self._center_window()

        # 等待关闭
        self.wait_window(self)

    def _create_widgets(self):
        """创建界面组件"""
        # 创建 Notebook
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 常规设置页
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="常规")
        self._create_general_tab(general_frame)

        # API 设置页
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API")
        self._create_api_tab(api_frame)

        # 界面设置页
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="界面")
        self._create_ui_tab(ui_frame)

        # 按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="应用", command=self._on_apply).pack(side=tk.RIGHT, padx=5)

    def _create_general_tab(self, parent):
        """创建常规设置页"""
        # 项目路径
        frame = ttk.LabelFrame(parent, text="项目设置", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame, text="默认项目路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.project_path_var = tk.StringVar(value=self.current_settings.get("project_path", ""))
        ttk.Entry(frame, textvariable=self.project_path_var, width=40).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(frame, text="浏览", command=self._browse_project_path).grid(row=0, column=2, pady=5)

        # 语言
        ttk.Label(frame, text="语言:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar(value=self.current_settings.get("language", "zh_CN"))
        ttk.Combobox(frame, textvariable=self.language_var, values=["zh_CN", "en_US"], state="readonly").grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

    def _create_api_tab(self, parent):
        """创建 API 设置页"""
        # GLM API
        frame = ttk.LabelFrame(parent, text="GLM API", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame, text="API 密钥:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.glm_api_key_var = tk.StringVar(value=self.current_settings.get("glm_api_key", ""))
        ttk.Entry(frame, textvariable=self.glm_api_key_var, width=40, show="*").grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(frame, text="模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.glm_model_var = tk.StringVar(value=self.current_settings.get("glm_model", "glm-5"))
        ttk.Combobox(frame, textvariable=self.glm_model_var, values=["glm-4", "glm-5"], state="readonly").grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        # Elsevier API
        frame2 = ttk.LabelFrame(parent, text="Elsevier API", padding=10)
        frame2.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame2, text="API 密钥:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.elsevier_api_key_var = tk.StringVar(value=self.current_settings.get("elsevier_api_key", ""))
        ttk.Entry(frame2, textvariable=self.elsevier_api_key_var, width=40, show="*").grid(row=0, column=1, pady=5, padx=5)

    def _create_ui_tab(self, parent):
        """创建界面设置页"""
        # 主题
        frame = ttk.LabelFrame(parent, text="主题", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame, text="主题:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.theme_var = tk.StringVar(value=self.current_settings.get("theme", "default"))
        ttk.Combobox(frame, textvariable=self.theme_var, values=["default", "dark", "light"], state="readonly").grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # 字体
        ttk.Label(frame, text="字体大小:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.font_size_var = tk.IntVar(value=self.current_settings.get("font_size", 10))
        ttk.Spinbox(frame, from_=8, to=16, textvariable=self.font_size_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

    def _browse_project_path(self):
        """浏览项目路径"""
        path = filedialog.askdirectory(title="选择项目路径")
        if path:
            self.project_path_var.set(path)

    def _on_ok(self):
        """确定按钮回调"""
        self.result = self._collect_settings()
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        """取消按钮回调"""
        self.result = None
        self.grab_release()
        self.destroy()

    def _on_apply(self):
        """应用按钮回调"""
        self.result = self._collect_settings()

    def _collect_settings(self) -> Dict[str, Any]:
        """收集设置

        Returns:
            设置字典
        """
        return {
            "project_path": self.project_path_var.get(),
            "language": self.language_var.get(),
            "glm_api_key": self.glm_api_key_var.get(),
            "glm_model": self.glm_model_var.get(),
            "elsevier_api_key": self.elsevier_api_key_var.get(),
            "theme": self.theme_var.get(),
            "font_size": self.font_size_var.get()
        }

    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        width = 500
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


class AboutDialog(tk.Toplevel):
    """关于对话框

    显示应用程序信息。
    """

    def __init__(self, parent):
        """初始化关于对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        self.title("关于 LiteratureHub")

        # 创建组件
        self._create_widgets()

        # 居中显示
        self._center_window()

    def _create_widgets(self):
        """创建界面组件"""
        # 图标和标题
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="LiteratureHub", font=("Arial", 20, "bold")).pack(pady=10)
        ttk.Label(frame, text="统一文献管理与汇报系统", font=("Arial", 12)).pack(pady=5)
        ttk.Label(frame, text="版本 1.0.0", font=("Arial", 10)).pack(pady=5)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 描述
        description = """LiteratureHub 是一个专为博士研究生设计的文献管理与汇报系统。

主要功能：
• 文献搜索与下载
• AI 深度分析
• PPT 自动生成
• 项目管理

版权所有 © 2025-2026 LiteratureHub
 Licensed under the Apache License, Version 2.0"""

        ttk.Label(frame, text=description, justify=tk.LEFT).pack(pady=10)

        # 按钮
        ttk.Button(frame, text="确定", command=self.destroy).pack(pady=10)

    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        width = 400
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
