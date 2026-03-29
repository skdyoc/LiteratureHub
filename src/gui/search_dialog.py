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
搜索对话框

提供高级文献搜索功能，支持关键词和排除关键词。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
import logging


class SearchDialog(tk.Toplevel):
    """搜索对话框

    支持高级搜索功能：
    - 必须包含的关键词
    - 排除的关键词
    - 年份范围
    - 数据库选择

    用法：
    ```python
    dialog = SearchDialog(parent)
    dialog.set_callback(on_search_complete)
    dialog.show()

    def on_search_complete(params):
        keywords = params['keywords']
        exclude = params['exclude_keywords']
        # 执行搜索...
    ```
    """

    def __init__(self, parent, title: str = "高级搜索"):
        """初始化搜索对话框

        Args:
            parent: 父窗口
            title: 对话框标题
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("500x450")
        self.resizable(False, False)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.callback: Optional[Callable] = None

        # 使对话框模态
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._center_window(parent)

    def _center_window(self, parent):
        """将窗口居中"""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === 关键词输入 ===
        kw_frame = ttk.LabelFrame(main_frame, text="搜索关键词", padding=10)
        kw_frame.pack(fill=tk.X, pady=5)

        # 关键词输入
        ttk.Label(kw_frame, text="必须包含的关键词:").pack(anchor=tk.W)
        self.keywords_entry = ttk.Entry(kw_frame, width=60)
        self.keywords_entry.pack(fill=tk.X, pady=2)
        ttk.Label(kw_frame, text="多个关键词用逗号分隔，例如：large scale, wind turbine, HAWT",
                  foreground="gray").pack(anchor=tk.W)

        # 排除关键词
        ttk.Label(kw_frame, text="\n排除的关键词:").pack(anchor=tk.W)
        self.exclude_entry = ttk.Entry(kw_frame, width=60)
        self.exclude_entry.pack(fill=tk.X, pady=2)
        ttk.Label(kw_frame, text="不想要的关键词，例如：vertical axis, VAWT, Darrieus",
                  foreground="gray").pack(anchor=tk.W)

        # === 搜索选项 ===
        options_frame = ttk.LabelFrame(main_frame, text="搜索选项", padding=10)
        options_frame.pack(fill=tk.X, pady=5)

        # 年份范围
        year_frame = ttk.Frame(options_frame)
        year_frame.pack(fill=tk.X, pady=2)
        ttk.Label(year_frame, text="年份范围:").pack(side=tk.LEFT)
        self.year_from = ttk.Spinbox(year_frame, from_=1990, to=2030, width=8)
        self.year_from.set(2020)
        self.year_from.pack(side=tk.LEFT, padx=5)
        ttk.Label(year_frame, text=" 至 ").pack(side=tk.LEFT)
        self.year_to = ttk.Spinbox(year_frame, from_=1990, to=2030, width=8)
        self.year_to.set(2026)
        self.year_to.pack(side=tk.LEFT, padx=5)

        # 最大结果数
        max_frame = ttk.Frame(options_frame)
        max_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_frame, text="最大结果数:").pack(side=tk.LEFT)
        self.max_results = ttk.Spinbox(max_frame, from_=10, to=500, width=8)
        self.max_results.set(100)
        self.max_results.pack(side=tk.LEFT, padx=5)

        # 精确匹配选项
        self.exact_match = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="精确匹配（要求所有关键词都出现）",
                        variable=self.exact_match).pack(anchor=tk.W, pady=2)

        # 数据库选择
        db_frame = ttk.Frame(options_frame)
        db_frame.pack(fill=tk.X, pady=2)
        ttk.Label(db_frame, text="搜索数据库:").pack(anchor=tk.W)
        self.db_vars = {}
        databases = ["Elsevier", "IEEE", "Springer", "arXiv"]
        for db in databases:
            var = tk.BooleanVar(value=True)
            self.db_vars[db] = var
            ttk.Checkbutton(db_frame, text=db, variable=var).pack(side=tk.LEFT, padx=10)

        # === 示例说明 ===
        example_frame = ttk.LabelFrame(main_frame, text="搜索示例", padding=10)
        example_frame.pack(fill=tk.X, pady=5)

        examples = [
            "搜索水平轴大型风机，排除垂直轴：",
            "  关键词: large scale, horizontal axis, wind turbine, HAWT",
            "  排除: vertical axis, VAWT, Darrieus, Savonius",
            "",
            "搜索海上风电叶片优化：",
            "  关键词: offshore wind, blade optimization, aerodynamic",
            "  排除: （留空）",
        ]
        for ex in examples:
            ttk.Label(example_frame, text=ex, foreground="gray").pack(anchor=tk.W)

        # === 按钮 ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=15)

        ttk.Button(btn_frame, text="开始搜索", command=self._on_search).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="清空", command=self._clear_inputs).pack(side=tk.RIGHT, padx=5)

    def _clear_inputs(self):
        """清空输入"""
        self.keywords_entry.delete(0, tk.END)
        self.exclude_entry.delete(0, tk.END)

    def _on_search(self):
        """开始搜索"""
        # 获取关键词
        keywords_text = self.keywords_entry.get().strip()
        if not keywords_text:
            messagebox.showwarning("提示", "请输入搜索关键词！")
            return

        # 解析关键词（逗号分隔）
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]

        # 解析排除关键词
        exclude_text = self.exclude_entry.get().strip()
        exclude_keywords = [kw.strip() for kw in exclude_text.split(",") if kw.strip()] if exclude_text else []

        # 获取年份范围
        try:
            year_from = int(self.year_from.get())
            year_to = int(self.year_to.get())
            year_range = (year_from, year_to) if year_from <= year_to else None
        except ValueError:
            year_range = None

        # 获取最大结果数
        try:
            max_results = int(self.max_results.get())
        except ValueError:
            max_results = 100

        # 获取选中的数据库
        databases = [db for db, var in self.db_vars.items() if var.get()]

        # 构建搜索参数
        search_params = {
            "keywords": keywords,
            "exclude_keywords": exclude_keywords,
            "year_range": year_range,
            "max_results": max_results,
            "require_all_keywords": self.exact_match.get(),
            "databases": databases
        }

        self.logger.info(f"搜索参数: {search_params}")

        # 回调
        if self.callback:
            self.callback(search_params)

        self.destroy()

    def _on_cancel(self):
        """取消"""
        self.destroy()

    def set_callback(self, callback: Callable):
        """设置搜索回调

        Args:
            callback: 回调函数，接收搜索参数字典
        """
        self.callback = callback

    def show(self):
        """显示对话框"""
        self.wait_window()


# 便捷函数
def show_search_dialog(parent, callback: Callable) -> SearchDialog:
    """显示搜索对话框

    Args:
        parent: 父窗口
        callback: 搜索回调函数

    Returns:
        对话框实例
    """
    dialog = SearchDialog(parent)
    dialog.set_callback(callback)
    dialog.show()
    return dialog
