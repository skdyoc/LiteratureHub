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
配置面板

提供可视化配置编辑界面。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
from typing import Dict, Any, List


class ConfigPanel(ttk.Frame):
    """配置面板

    提供可视化配置编辑。

    使用示例：
    ```python
    panel = ConfigPanel(parent, config_manager)
    panel.load_config("project_config.json")
    panel.pack(fill=tk.BOTH, expand=True)
    ```
    """

    def __init__(self, parent, config_manager=None):
        """初始化配置面板

        Args:
            parent: 父窗口
            config_manager: 配置管理器
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.config_data: Dict[str, Any] = {}
        self.config_widgets: Dict[str, tk.Widget] = {}

        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=5)

        ttk.Button(toolbar, text="加载配置", command=self._load_config_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存配置", command=self._save_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置默认", command=self._reset_to_default).pack(side=tk.LEFT, padx=2)

        # 配置区域（带滚动条）
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 配置分类
        self._create_config_sections()

    def _create_config_sections(self):
        """创建配置分类区域"""
        # 1. 项目配置
        project_frame = ttk.LabelFrame(self.scrollable_frame, text="项目配置", padding=10)
        project_frame.pack(fill=tk.X, padx=5, pady=5)

        self._add_config_field(project_frame, "project_name", "项目名称:", "entry")
        self._add_config_field(project_frame, "project_path", "项目路径:", "entry_with_browse")
        self._add_config_field(project_frame, "description", "项目描述:", "text")

        # 2. 搜索配置
        search_frame = ttk.LabelFrame(self.scrollable_frame, text="搜索配置", padding=10)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        self._add_config_field(search_frame, "search_keywords", "搜索关键词:", "entry")
        self._add_config_field(search_frame, "search_databases", "搜索数据库:", "checkboxes",
                              options=["Elsevier", "arXiv", "IEEE", "Springer"])
        self._add_config_field(search_frame, "max_results", "最大结果数:", "spinbox",
                              from_=10, to=1000)

        # 3. 分析配置
        analysis_frame = ttk.LabelFrame(self.scrollable_frame, text="分析配置", padding=10)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)

        self._add_config_field(analysis_frame, "ai_model", "AI 模型:", "combobox",
                              options=["GLM-5", "DeepSeek-V3", "Claude-3"])
        self._add_config_field(analysis_frame, "analysis_depth", "分析深度:", "scale",
                              from_=1, to=5)
        self._add_config_field(analysis_frame, "enable_scoring", "启用评分:", "checkbox")

        # 4. PPT 配置
        ppt_frame = ttk.LabelFrame(self.scrollable_frame, text="PPT 配置", padding=10)
        ppt_frame.pack(fill=tk.X, padx=5, pady=5)

        self._add_config_field(ppt_frame, "template_path", "模板路径:", "entry_with_browse")
        self._add_config_field(ppt_frame, "output_format", "输出格式:", "radiobuttons",
                              options=["PPTX", "PDF", "HTML"])

    def _add_config_field(self, parent, key: str, label: str, field_type: str, **kwargs):
        """添加配置字段

        Args:
            parent: 父容器
            key: 配置键
            label: 标签文本
            field_type: 字段类型
            **kwargs: 其他参数
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)

        if field_type == "entry":
            widget = ttk.Entry(frame)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.config_widgets[key] = widget

        elif field_type == "entry_with_browse":
            entry = ttk.Entry(frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            browse_btn = ttk.Button(frame, text="浏览", command=lambda: self._browse_file(entry))
            browse_btn.pack(side=tk.LEFT, padx=2)

            self.config_widgets[key] = entry

        elif field_type == "text":
            widget = tk.Text(frame, height=3)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.config_widgets[key] = widget

        elif field_type == "checkbox":
            var = tk.BooleanVar()
            widget = ttk.Checkbutton(frame, variable=var)
            widget.pack(side=tk.LEFT)
            self.config_widgets[key] = var

        elif field_type == "spinbox":
            widget = ttk.Spinbox(frame, from_=kwargs.get("from_", 0), to=kwargs.get("to", 100))
            widget.pack(side=tk.LEFT)
            self.config_widgets[key] = widget

        elif field_type == "combobox":
            widget = ttk.Combobox(frame, values=kwargs.get("options", []), state="readonly")
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.config_widgets[key] = widget

        elif field_type == "scale":
            var = tk.IntVar()
            widget = ttk.Scale(frame, from_=kwargs.get("from_", 1), to=kwargs.get("to", 5),
                             variable=var, orient=tk.HORIZONTAL)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.config_widgets[key] = var

        elif field_type == "radiobuttons":
            var = tk.StringVar()
            for option in kwargs.get("options", []):
                rb = ttk.Radiobutton(frame, text=option, value=option, variable=var)
                rb.pack(side=tk.LEFT)
            self.config_widgets[key] = var

        elif field_type == "checkboxes":
            # 多个复选框
            vars_dict = {}
            for option in kwargs.get("options", []):
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(frame, text=option, variable=var)
                cb.pack(side=tk.LEFT)
                vars_dict[option] = var
            self.config_widgets[key] = vars_dict

    def _browse_file(self, entry: ttk.Entry):
        """浏览文件"""
        file_path = filedialog.askopenfilename()
        if file_path:
            entry.delete(0, tk.END)
            entry.insert(0, file_path)

    def _load_config_dialog(self):
        """加载配置对话框"""
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.load_config(file_path)

    def load_config(self, config_path: str):
        """加载配置文件

        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)

            # 更新界面
            self._update_widgets_from_config()
            messagebox.showinfo("成功", "配置加载成功！")

        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def _update_widgets_from_config(self):
        """从配置数据更新界面"""
        for key, widget in self.config_widgets.items():
            if key in self.config_data:
                value = self.config_data[key]

                if isinstance(widget, ttk.Entry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))

                elif isinstance(widget, tk.Text):
                    widget.delete(1.0, tk.END)
                    widget.insert(1.0, str(value))

                elif isinstance(widget, tk.BooleanVar):
                    widget.set(bool(value))

                elif isinstance(widget, tk.IntVar):
                    widget.set(int(value))

                elif isinstance(widget, tk.StringVar):
                    widget.set(str(value))

                elif isinstance(widget, ttk.Spinbox):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))

                elif isinstance(widget, ttk.Combobox):
                    widget.set(str(value))

                elif isinstance(widget, dict):
                    # checkboxes
                    if isinstance(value, list):
                        for option, var in widget.items():
                            var.set(option in value)

    def _save_config(self):
        """保存配置"""
        # 从界面收集数据
        for key, widget in self.config_widgets.items():
            if isinstance(widget, ttk.Entry):
                self.config_data[key] = widget.get()

            elif isinstance(widget, tk.Text):
                self.config_data[key] = widget.get(1.0, tk.END).strip()

            elif isinstance(widget, tk.BooleanVar):
                self.config_data[key] = widget.get()

            elif isinstance(widget, tk.IntVar):
                self.config_data[key] = widget.get()

            elif isinstance(widget, tk.StringVar):
                self.config_data[key] = widget.get()

            elif isinstance(widget, ttk.Spinbox):
                self.config_data[key] = widget.get()

            elif isinstance(widget, ttk.Combobox):
                self.config_data[key] = widget.get()

            elif isinstance(widget, dict):
                # checkboxes
                selected = [option for option, var in widget.items() if var.get()]
                self.config_data[key] = selected

        # 保存到文件
        file_path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", "配置保存成功！")

    def _reset_to_default(self):
        """重置为默认配置"""
        self.config_data = {
            "project_name": "",
            "project_path": "",
            "description": "",
            "search_keywords": "",
            "search_databases": ["Elsevier", "arXiv"],
            "max_results": 100,
            "ai_model": "GLM-5",
            "analysis_depth": 3,
            "enable_scoring": True,
            "template_path": "",
            "output_format": "PPTX"
        }
        self._update_widgets_from_config()
        messagebox.showinfo("成功", "已重置为默认配置！")
