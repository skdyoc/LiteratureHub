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
主窗口

提供应用程序的主窗口界面。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import logging


class MainWindow:
    """主窗口

    应用程序的主界面窗口。

    使用示例：
    ```python
    window = MainWindow()
    window.show()
    ```
    """

    def __init__(self, title: str = "LiteratureHub"):
        """初始化主窗口

        Args:
            title: 窗口标题
        """
        self.window = tk.Tk()
        self.window.title(title)
        self.window.geometry("1200x800")

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 初始化组件
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI 组件"""
        # 创建菜单栏
        self._create_menubar()

        # 创建工具栏
        self._create_toolbar()

        # 创建主内容区域
        self._create_content()

        # 创建状态栏
        self._create_statusbar()

    def _create_menubar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建项目", command=self._on_new_project)
        file_menu.add_command(label="打开项目", command=self._on_open_project)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.window.quit)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._on_about)

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="新建", command=self._on_new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="打开", command=self._on_open_project).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="搜索", command=self._on_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="分析", command=self._on_analyze).pack(side=tk.LEFT, padx=2)

    def _create_content(self):
        """创建主内容区域"""
        # 使用 PanedWindow 分割左右区域
        paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板：项目列表
        left_frame = ttk.LabelFrame(paned, text="项目列表", padding=5)
        paned.add(left_frame, weight=1)

        self.project_list = tk.Listbox(left_frame)
        self.project_list.pack(fill=tk.BOTH, expand=True)
        self.project_list.bind('<<ListboxSelect>>', self._on_project_select)

        # 右侧面板：工作流控制
        right_frame = ttk.LabelFrame(paned, text="工作流控制", padding=5)
        paned.add(right_frame, weight=2)

        # 工作流按钮
        workflow_frame = ttk.Frame(right_frame)
        workflow_frame.pack(fill=tk.X, pady=5)

        ttk.Button(workflow_frame, text="1. 文献搜索", command=self._start_search).pack(fill=tk.X, pady=2)
        ttk.Button(workflow_frame, text="2. 文献分析", command=self._start_analysis).pack(fill=tk.X, pady=2)
        ttk.Button(workflow_frame, text="3. PPT 生成", command=self._start_ppt).pack(fill=tk.X, pady=2)

        # 进度显示
        progress_frame = ttk.LabelFrame(right_frame, text="进度", padding=5)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)

        # 日志显示
        log_frame = ttk.LabelFrame(right_frame, text="日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_statusbar(self):
        """创建状态栏"""
        statusbar = ttk.Frame(self.window)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(statusbar, text="就绪")
        self.status_label.pack(side=tk.LEFT)

    def _on_new_project(self):
        """新建项目事件"""
        self._log("创建新项目")

    def _on_open_project(self):
        """打开项目事件"""
        self._log("打开现有项目")

    def _on_about(self):
        """关于事件"""
        messagebox.showinfo("关于", "LiteratureHub v1.0\\n统一文献管理与汇报系统")

    def _on_search(self):
        """搜索事件"""
        self._log("启动搜索")

    def _on_analyze(self):
        """分析事件"""
        self._log("启动分析")

    def _on_project_select(self, event):
        """项目选择事件"""
        selection = self.project_list.curselection()
        if selection:
            project = self.project_list.get(selection[0])
            self._log(f"选择项目: {project}")

    def _start_search(self):
        """启动搜索"""
        from .search_dialog import SearchDialog

        def on_search_complete(params):
            keywords = params.get('keywords', [])
            exclude_keywords = params.get('exclude_keywords', [])
            year_range = params.get('year_range')
            max_results = params.get('max_results', 100)
            require_all = params.get('require_all_keywords', True)
            databases = params.get('databases', [])

            self._log(f"搜索关键词: {', '.join(keywords)}")
            if exclude_keywords:
                self._log(f"排除关键词: {', '.join(exclude_keywords)}")
            self._log(f"精确匹配: {'是' if require_all else '否'}")
            if year_range:
                self._log(f"年份范围: {year_range[0]}-{year_range[1]}")
            if databases:
                self._log(f"搜索数据库: {', '.join(databases)}")

            self.status_label.config(text=f"搜索中: {', '.join(keywords)}...")

            # TODO: 调用 SearchManager 执行实际搜索
            # self._execute_search(params)

        dialog = SearchDialog(self.window)
        dialog.set_callback(on_search_complete)
        dialog.show()

    def _start_analysis(self):
        """启动分析"""
        self._log("启动文献分析")
        self.status_label.config(text="分析中...")

    def _start_ppt(self):
        """启动 PPT 生成"""
        self._log("启动 PPT 生成")
        self.status_label.config(text="生成 PPT 中...")

    def _log(self, message: str):
        """记录日志"""
        self.log_text.insert(tk.END, f"{message}\\n")
        self.log_text.see(tk.END)
        self.logger.info(message)

    def show(self):
        """显示窗口"""
        self.window.mainloop()

    def close(self):
        """关闭窗口"""
        self.window.quit()
