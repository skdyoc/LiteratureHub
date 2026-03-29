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
项目面板组件

显示和管理项目信息。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import logging
from datetime import datetime


class ProjectPanel(ttk.Frame):
    """项目面板

    显示和管理当前项目的详细信息。

    功能：
    - 项目基本信息显示
    - 项目统计信息
    - 项目配置管理
    - 快捷操作按钮
    - 项目历史记录
    """

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        on_project_change: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """初始化项目面板

        Args:
            parent: 父组件
            db_manager: 数据库管理器
            on_project_change: 项目变更回调
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.on_project_change = on_project_change
        self.current_project: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(self.__class__.__name__)

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            title_frame,
            text="项目信息",
            font=("", 12, "bold")
        ).pack(side=tk.LEFT)

        # 项目名称
        name_frame = ttk.Frame(self)
        name_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(name_frame, text="项目名称:").pack(side=tk.LEFT)
        self.name_label = ttk.Label(name_frame, text="未选择项目")
        self.name_label.pack(side=tk.LEFT, padx=5)

        # 项目描述
        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(desc_frame, text="项目描述:").pack(anchor=tk.W)
        self.desc_text = tk.Text(desc_frame, height=3, width=40)
        self.desc_text.pack(fill=tk.X, pady=5)

        # 统计信息
        stats_frame = ttk.LabelFrame(self, text="统计信息")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)

        # 文献数量
        papers_frame = ttk.Frame(stats_frame)
        papers_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(papers_frame, text="文献总数:").pack(side=tk.LEFT)
        self.papers_count_label = ttk.Label(papers_frame, text="0")
        self.papers_count_label.pack(side=tk.RIGHT)

        # 已分析数量
        analyzed_frame = ttk.Frame(stats_frame)
        analyzed_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(analyzed_frame, text="已分析:").pack(side=tk.LEFT)
        self.analyzed_count_label = ttk.Label(analyzed_frame, text="0")
        self.analyzed_count_label.pack(side=tk.RIGHT)

        # PPT数量
        ppt_frame = ttk.Frame(stats_frame)
        ppt_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(ppt_frame, text="PPT数量:").pack(side=tk.LEFT)
        self.ppt_count_label = ttk.Label(ppt_frame, text="0")
        self.ppt_count_label.pack(side=tk.RIGHT)

        # 创建时间
        created_frame = ttk.Frame(stats_frame)
        created_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(created_frame, text="创建时间:").pack(side=tk.LEFT)
        self.created_label = ttk.Label(created_frame, text="-")
        self.created_label.pack(side=tk.RIGHT)

        # 操作按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="新建项目",
            command=self._create_project
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="打开项目",
            command=self._open_project
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="保存项目",
            command=self._save_project
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="导出报告",
            command=self._export_report
        ).pack(side=tk.LEFT, padx=5)

    def load_project(self, project_id: str):
        """加载项目

        Args:
            project_id: 项目ID
        """
        try:
            # 从数据库加载项目
            projects = self.db_manager.query(
                "projects",
                filters={"id": project_id}
            )

            if not projects:
                messagebox.showwarning("警告", f"项目不存在: {project_id}")
                return

            self.current_project = projects[0]
            self._update_display()

            # 触发回调
            if self.on_project_change:
                self.on_project_change(self.current_project)

            self.logger.info(f"已加载项目: {project_id}")

        except Exception as e:
            self.logger.error(f"加载项目失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"加载项目失败: {e}")

    def _update_display(self):
        """更新显示"""
        if not self.current_project:
            return

        # 更新项目名称
        self.name_label.config(text=self.current_project.get("name", "未命名"))

        # 更新项目描述
        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(1.0, self.current_project.get("description", ""))

        # 更新统计信息
        self.papers_count_label.config(
            text=str(self.current_project.get("papers_count", 0))
        )
        self.analyzed_count_label.config(
            text=str(self.current_project.get("analyzed_count", 0))
        )
        self.ppt_count_label.config(
            text=str(self.current_project.get("ppt_count", 0))
        )

        # 更新创建时间
        created_at = self.current_project.get("created_at")
        if created_at:
            self.created_label.config(text=created_at)

    def _create_project(self):
        """创建新项目"""
        # 创建对话框
        dialog = tk.Toplevel(self)
        dialog.title("新建项目")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # 项目名称
        ttk.Label(dialog, text="项目名称:").grid(row=0, column=0, padx=10, pady=10)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        # 项目描述
        ttk.Label(dialog, text="项目描述:").grid(row=1, column=0, padx=10, pady=10)
        desc_text = tk.Text(dialog, height=5, width=30)
        desc_text.grid(row=1, column=1, padx=10, pady=10)

        # 按钮
        def on_create():
            name = name_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()

            if not name:
                messagebox.showwarning("警告", "请输入项目名称")
                return

            # 创建项目
            project = {
                "id": f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "name": name,
                "description": description,
                "papers_count": 0,
                "analyzed_count": 0,
                "ppt_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            try:
                self.db_manager.insert("projects", project)
                self.current_project = project
                self._update_display()

                if self.on_project_change:
                    self.on_project_change(project)

                dialog.destroy()
                messagebox.showinfo("成功", f"项目创建成功: {name}")

            except Exception as e:
                messagebox.showerror("错误", f"创建项目失败: {e}")

        ttk.Button(dialog, text="创建", command=on_create).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(dialog, text="取消", command=dialog.destroy).grid(row=2, column=1, padx=10, pady=10)

    def _open_project(self):
        """打开项目"""
        try:
            # 查询所有项目
            projects = self.db_manager.query("projects")

            if not projects:
                messagebox.showinfo("提示", "没有可用的项目")
                return

            # 创建选择对话框
            dialog = tk.Toplevel(self)
            dialog.title("打开项目")
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()

            # 项目列表
            ttk.Label(dialog, text="选择项目:").pack(padx=10, pady=10)

            listbox = tk.Listbox(dialog, height=10, width=40)
            listbox.pack(padx=10, pady=5)

            for project in projects:
                listbox.insert(tk.END, f"{project['name']} ({project['created_at'][:10]})")

            def on_select():
                selection = listbox.curselection()
                if not selection:
                    messagebox.showwarning("警告", "请选择一个项目")
                    return

                index = selection[0]
                selected_project = projects[index]
                self.load_project(selected_project["id"])
                dialog.destroy()

            ttk.Button(dialog, text="打开", command=on_select).pack(pady=10)
            ttk.Button(dialog, text="取消", command=dialog.destroy).pack()

        except Exception as e:
            self.logger.error(f"打开项目失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"打开项目失败: {e}")

    def _save_project(self):
        """保存项目"""
        if not self.current_project:
            messagebox.showwarning("警告", "没有打开的项目")
            return

        try:
            # 更新项目信息
            self.current_project["description"] = self.desc_text.get(1.0, tk.END).strip()
            self.current_project["updated_at"] = datetime.now().isoformat()

            # 保存到数据库
            self.db_manager.update(
                "projects",
                self.current_project,
                {"id": self.current_project["id"]}
            )

            messagebox.showinfo("成功", "项目保存成功")

        except Exception as e:
            self.logger.error(f"保存项目失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"保存项目失败: {e}")

    def _export_report(self):
        """导出项目报告"""
        if not self.current_project:
            messagebox.showwarning("警告", "没有打开的项目")
            return

        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="导出项目报告",
            defaultextension=".md",
            filetypes=[
                ("Markdown 文件", "*.md"),
                ("JSON 文件", "*.json"),
                ("所有文件", "*.*")
            ]
        )

        if not file_path:
            return

        try:
            # 生成报告内容
            report_content = f"""# 项目报告：{self.current_project['name']}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 项目信息

- **项目名称**: {self.current_project['name']}
- **创建时间**: {self.current_project.get('created_at', '-')}
- **更新时间**: {self.current_project.get('updated_at', '-')}

## 项目描述

{self.current_project.get('description', '无描述')}

## 统计信息

- **文献总数**: {self.current_project.get('papers_count', 0)}
- **已分析**: {self.current_project.get('analyzed_count', 0)}
- **PPT数量**: {self.current_project.get('ppt_count', 0)}

---
*本报告由 LiteratureHub 自动生成*
"""

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            messagebox.showinfo("成功", f"报告已导出: {file_path}")

        except Exception as e:
            self.logger.error(f"导出报告失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"导出报告失败: {e}")

    def refresh(self):
        """刷新项目信息"""
        if self.current_project:
            self.load_project(self.current_project["id"])
