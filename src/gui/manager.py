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
GUI 管理器

提供统一的 GUI 管理接口。
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from pathlib import Path

from ..data.manager import DatabaseManager
from ..data.file_manager import FileManager


class GUIManager:
    """GUI 管理器

    统一管理所有 GUI 组件和交互。

    用法：
    ```python
    gui = GUIManager()
    gui.initialize()
    gui.run()
    ```
    """

    def __init__(self, db_manager: DatabaseManager = None, file_manager: FileManager = None):
        """初始化 GUI 管理器

        Args:
            db_manager: 数据库管理器
            file_manager: 文件管理器
        """
        self.db_manager = db_manager or DatabaseManager()
        self.file_manager = file_manager or FileManager()

        self.root: Optional[tk.Tk] = None
        self.main_window: Optional[tk.Tk] = None
        self.panels: Dict[str, ttk.Frame] = {}

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def initialize(self):
        """初始化 GUI"""
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("LiteratureHub - 统一文献管理与汇报系统")
        self.root.geometry("1200x800")

        # 设置主题样式
        self._setup_styles()

        # 创建菜单栏
        self._create_menu()

        # 创建主框架
        self._create_main_frame()

        # 创建状态栏
        self._create_status_bar()

        self.logger.info("GUI 初始化完成")

    def _setup_styles(self):
        """设置主题样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 使用 clam 主题

        # 自定义样式
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 10))
        style.configure('Success.TButton', foreground='green')

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建项目", command=self._new_project)
        file_menu.add_command(label="打开项目", command=self._open_project)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="配置", command=self._open_config)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _create_main_frame(self):
        """创建主框架"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：项目管理面板
        left_frame = ttk.LabelFrame(main_frame, text="项目管理", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 项目列表
        self.project_listbox = tk.Listbox(left_frame)
        self.project_listbox.pack(fill=tk.BOTH, expand=True)
        self.project_listbox.bind('<<ListboxSelect>>', self._on_project_select)

        # 右侧：工作流面板
        right_frame = ttk.LabelFrame(main_frame, text="工作流", padding="5")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 工作流按钮
        ttk.Button(right_frame, text="1. 文献搜索", command=self._start_search).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="2. 文献分析", command=self._start_analysis).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="3. PPT 生成", command=self._start_ppt_generation).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="4. 全流程", command=self._start_full_workflow).pack(fill=tk.X, pady=2)

        # 进度显示
        ttk.Label(right_frame, text="进度：").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(right_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        # 日志显示
        ttk.Label(right_frame, text="日志：").pack(anchor=tk.W)
        self.log_text = tk.Text(right_frame, height=10, width=40)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

    def _new_project(self):
        """新建项目"""
        from tkinter import simpledialog

        project_name = simpledialog.askstring("新建项目", "项目名称：")
        if project_name:
            self._log(f"创建项目: {project_name}")
            self._refresh_project_list()

    def _open_project(self):
        """打开项目"""
        from tkinter import filedialog

        project_dir = filedialog.askdirectory(title="选择项目目录")
        if project_dir:
            self._log(f"打开项目: {project_dir}")

    def _open_config(self):
        """打开配置"""
        self._log("打开配置界面")

    def _show_about(self):
        """显示关于对话框"""
        from tkinter import messagebox

        messagebox.showinfo(
            "关于 LiteratureHub",
            "LiteratureHub v1.0\n统一文献管理与汇报系统\n\n"
            "基于 PRD 设计的博士研究工具"
        )

    def _on_project_select(self, event):
        """项目选择事件"""
        selection = self.project_listbox.curselection()
        if selection:
            project_name = self.project_listbox.get(selection[0])
            self._log(f"选择项目: {project_name}")

    def _start_search(self):
        """启动文献搜索"""
        self._log("启动文献搜索...")
        self.status_label.config(text="文献搜索中...")

    def _start_analysis(self):
        """启动文献分析"""
        self._log("启动文献分析...")
        self.status_label.config(text="文献分析中...")

    def _start_ppt_generation(self):
        """启动 PPT 生成"""
        self._log("启动 PPT 生成...")
        self.status_label.config(text="PPT 生成中...")

    def _start_full_workflow(self):
        """启动全流程"""
        self._log("启动全流程...")
        self.status_label.config(text="全流程执行中...")

    def _log(self, message: str):
        """记录日志"""
        self.log_text.insert(tk.END, f"{message}\\n")
        self.log_text.see(tk.END)
        self.logger.info(message)

    def _refresh_project_list(self):
        """刷新项目列表"""
        self.project_listbox.delete(0, tk.END)

        # 查询数据库中的项目
        projects = self.db_manager.query('projects')
        for project in projects:
            self.project_listbox.insert(tk.END, project['name'])

    def run(self):
        """运行 GUI 主循环"""
        if not self.root:
            self.initialize()

        # 刷新项目列表
        self._refresh_project_list()

        # 启动主循环
        self.root.mainloop()

    def update_progress(self, value: int, max_value: int = 100):
        """更新进度条

        Args:
            value: 当前进度
            max_value: 最大值
        """
        self.progress_bar['value'] = (value / max_value) * 100
        self.root.update_idletasks()

    def show_message(self, title: str, message: str, type: str = "info"):
        """显示消息框

        Args:
            title: 标题
            message: 消息内容
            type: 类型（info, warning, error）
        """
        from tkinter import messagebox

        if type == "info":
            messagebox.showinfo(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)
        elif type == "error":
            messagebox.showerror(title, message)
