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
文献面板组件

提供文献显示、搜索、过滤和操作的统一界面。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import logging

from src.data.database_manager import DatabaseManager


class LiteraturePanel(ttk.Frame):
    """文献面板

    显示文献列表，支持搜索、过滤、排序和批量操作。

    功能：
    - 文献列表显示（支持多种视图模式）
    - 实时搜索和高级过滤
    - 排序功能（按标题、作者、年份、影响因子等）
    - 右键菜单（查看详情、编辑、删除、导出等）
    - 批量操作（批量删除、批量标记、批量导出）
    - 拖拽排序
    """

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: DatabaseManager,
        on_paper_select: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_paper_double_click: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """初始化文献面板

        Args:
            parent: 父组件
            db_manager: 数据库管理器
            on_paper_select: 文献选中回调
            on_paper_double_click: 文献双击回调
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.on_paper_select = on_paper_select
        self.on_paper_double_click = on_paper_double_click
        self.logger = logging.getLogger(self.__class__.__name__)

        # 数据存储
        self.papers: List[Dict[str, Any]] = []
        self.filtered_papers: List[Dict[str, Any]] = []
        self.selected_papers: List[Dict[str, Any]] = []

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 搜索栏
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 视图切换按钮
        ttk.Button(search_frame, text="列表", command=lambda: self._switch_view("list")).pack(side=tk.RIGHT, padx=2)
        ttk.Button(search_frame, text="表格", command=lambda: self._switch_view("table")).pack(side=tk.RIGHT, padx=2)

        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(toolbar, text="导入", command=self._import_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出", command=self._export_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

        # 状态标签
        self.status_label = ttk.Label(toolbar, text="共 0 篇文献")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # 文献列表（表格视图）
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建 Treeview
        columns = ("title", "authors", "year", "journal", "score", "status")
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # 设置列
        self.tree.heading("title", text="标题", command=lambda: self._sort_by("title"))
        self.tree.heading("authors", text="作者", command=lambda: self._sort_by("authors"))
        self.tree.heading("year", text="年份", command=lambda: self._sort_by("year"))
        self.tree.heading("journal", text="期刊", command=lambda: self._sort_by("journal"))
        self.tree.heading("score", text="评分", command=lambda: self._sort_by("score"))
        self.tree.heading("status", text="状态", command=lambda: self._sort_by("status"))

        self.tree.column("title", width=300)
        self.tree.column("authors", width=150)
        self.tree.column("year", width=60, anchor=tk.CENTER)
        self.tree.column("journal", width=150)
        self.tree.column("score", width=60, anchor=tk.CENTER)
        self.tree.column("status", width=80, anchor=tk.CENTER)

        # 滚动条
        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        self.tree.bind("<ButtonRelease-1>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # 右键菜单
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="查看详情", command=self._view_details)
        self.context_menu.add_command(label="编辑", command=self._edit_paper)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="标记为重要", command=self._mark_important)
        self.context_menu.add_command(label="标记为已读", command=self._mark_read)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除", command=self._delete_selected)
        self.context_menu.add_command(label="导出", command=self._export_papers)

    def refresh(self):
        """刷新文献列表"""
        try:
            # 从数据库加载文献
            self.papers = self.db_manager.query("papers")
            self.filtered_papers = self.papers.copy()

            # 更新显示
            self._update_tree()

            # 更新状态
            self.status_label.config(text=f"共 {len(self.papers)} 篇文献")

            self.logger.info(f"已刷新文献列表: {len(self.papers)} 篇")

        except Exception as e:
            self.logger.error(f"刷新文献列表失败: {e}")
            messagebox.showerror("错误", f"刷新失败: {e}")

    def _update_tree(self):
        """更新 Treeview 显示"""
        # 清空现有项
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加文献
        for paper in self.filtered_papers:
            self.tree.insert(
                "",
                tk.END,
                iid=paper.get("id"),
                values=(
                    paper.get("title", ""),
                    paper.get("authors", ""),
                    paper.get("year", ""),
                    paper.get("journal", ""),
                    paper.get("score", ""),
                    paper.get("status", "未读")
                )
            )

    def _on_search(self, *args):
        """搜索文献"""
        query = self.search_var.get().lower()

        if not query:
            self.filtered_papers = self.papers.copy()
        else:
            self.filtered_papers = [
                p for p in self.papers
                if query in p.get("title", "").lower()
                or query in p.get("authors", "").lower()
                or query in p.get("abstract", "").lower()
            ]

        self._update_tree()
        self.status_label.config(text=f"共 {len(self.filtered_papers)} 篇（筛选自 {len(self.papers)} 篇）")

    def _sort_by(self, column: str):
        """按列排序"""
        # 切换排序方向
        if hasattr(self, f'_sort_reverse_{column}'):
            setattr(self, f'_sort_reverse_{column}', not getattr(self, f'_sort_reverse_{column}'))
        else:
            setattr(self, f'_sort_reverse_{column}', False)

        reverse = getattr(self, f'_sort_reverse_{column}', False)

        # 排序
        self.filtered_papers.sort(
            key=lambda p: p.get(column, ""),
            reverse=reverse
        )

        self._update_tree()

    def _switch_view(self, view_type: str):
        """切换视图模式"""
        self.logger.info(f"切换到 {view_type} 视图")

        # 根据视图类型设置不同的列显示
        if view_type == "compact":
            # 紧凑视图：只显示标题和作者
            for col in self.tree["columns"]:
                if col not in ["title", "authors"]:
                    self.tree.column(col, width=0, stretch=False)
        elif view_type == "detailed":
            # 详细视图：显示所有列
            for col in self.tree["columns"]:
                self.tree.column(col, width=150, stretch=True)
        elif view_type == "reading":
            # 阅读视图：显示标题、摘要、状态
            for col in self.tree["columns"]:
                if col in ["title", "abstract", "status"]:
                    self.tree.column(col, width=200, stretch=True)
                else:
                    self.tree.column(col, width=0, stretch=False)

    def _on_tree_select(self, event):
        """处理选择事件"""
        selected_ids = self.tree.selection()
        self.selected_papers = [p for p in self.papers if p.get("id") in selected_ids]

        if self.selected_papers and self.on_paper_select:
            self.on_paper_select(self.selected_papers[0])

    def _on_tree_double_click(self, event):
        """处理双击事件"""
        selected_ids = self.tree.selection()
        if selected_ids and self.on_paper_double_click:
            paper = next((p for p in self.papers if p.get("id") == selected_ids[0]), None)
            if paper:
                self.on_paper_double_click(paper)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _view_details(self):
        """查看文献详情"""
        if self.selected_papers:
            paper = self.selected_papers[0]

            # 创建详情窗口
            from tkinter import Toplevel, Text, Scrollbar
            detail_window = Toplevel(self)
            detail_window.title(f"文献详情 - {paper.get('title', '无标题')}")
            detail_window.geometry("600x400")

            # 添加滚动文本框
            text = Text(detail_window, wrap="word", padx=10, pady=10)
            scrollbar = Scrollbar(detail_window, command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)

            # 填充详情内容
            details = f"""标题: {paper.get('title', '无')}
作者: {paper.get('authors', '无')}
年份: {paper.get('year', '无')}
期刊/会议: {paper.get('journal', '无')}
DOI: {paper.get('doi', '无')}

摘要:
{paper.get('abstract', '无摘要')}

关键词: {', '.join(paper.get('keywords', []))}

状态: {paper.get('status', '未读')}
"""
            text.insert("1.0", details)
            text.config(state="disabled")

            scrollbar.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)

    def _edit_paper(self):
        """编辑文献"""
        if self.selected_papers:
            paper = self.selected_papers[0]
            self.logger.info(f"编辑文献: {paper.get('id')}")

            # 创建编辑窗口
            from tkinter import Toplevel, Entry, Label, Button
            edit_window = Toplevel(self)
            edit_window.title(f"编辑文献 - {paper.get('title', '')}")
            edit_window.geometry("500x400")

            # 添加编辑字段
            fields = {
                "标题": paper.get("title", ""),
                "作者": paper.get("authors", ""),
                "年份": paper.get("year", ""),
                "期刊": paper.get("journal", ""),
                "DOI": paper.get("doi", ""),
                "关键词": ", ".join(paper.get("keywords", []))
            }

            entries = {}
            for i, (label, value) in enumerate(fields.items()):
                Label(edit_window, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
                entry = Entry(edit_window, width=50)
                entry.insert(0, value)
                entry.grid(row=i, column=1, padx=5, pady=5)
                entries[label] = entry

            def save_changes():
                # 保存修改到数据库
                updated_data = {
                    "title": entries["标题"].get(),
                    "authors": entries["作者"].get(),
                    "year": entries["年份"].get(),
                    "journal": entries["期刊"].get(),
                    "doi": entries["DOI"].get(),
                    "keywords": [k.strip() for k in entries["关键词"].get().split(",")]
                }
                self.db_manager.update("papers", updated_data, {"id": paper.get("id")})
                edit_window.destroy()
                self.refresh()

            Button(edit_window, text="保存", command=save_changes).grid(row=len(fields), column=1, pady=10)

    def _mark_important(self):
        """标记为重要"""
        for paper in self.selected_papers:
            self.db_manager.update(
                "papers",
                {"status": "重要"},
                {"id": paper.get("id")}
            )

        self.refresh()

    def _mark_read(self):
        """标记为已读"""
        for paper in self.selected_papers:
            self.db_manager.update(
                "papers",
                {"status": "已读"},
                {"id": paper.get("id")}
            )

        self.refresh()

    def _delete_selected(self):
        """删除选中的文献"""
        if not self.selected_papers:
            return

        if messagebox.askyesno("确认删除", f"确定要删除 {len(self.selected_papers)} 篇文献吗？"):
            for paper in self.selected_papers:
                self.db_manager.delete("papers", {"id": paper.get("id")})

            self.refresh()

    def _import_papers(self):
        """导入文献"""
        file_path = filedialog.askopenfilename(
            title="导入文献",
            filetypes=[
                ("JSON 文件", "*.json"),
                ("CSV 文件", "*.csv"),
                ("BibTeX 文件", "*.bib"),
                ("所有文件", "*.*")
            ]
        )

        if file_path:
            self.logger.info(f"导入文献: {file_path}")

            try:
                import json
                import csv

                papers = []

                # 根据文件类型解析
                if file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        papers = data if isinstance(data, list) else [data]

                elif file_path.endswith('.csv'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        papers = list(reader)

                elif file_path.endswith('.bib'):
                    # BibTeX 格式暂不支持，提示用户使用其他格式
                    self.logger.warning("BibTeX 解析功能开发中")
                    messagebox.showwarning("警告", "BibTeX 格式暂不支持，请使用 JSON 或 CSV")
                    return

                # 导入到数据库
                for paper in papers:
                    self.db_manager.insert("papers", paper)

                self.refresh()
                messagebox.showinfo("成功", f"成功导入 {len(papers)} 篇文献")

            except Exception as e:
                self.logger.error(f"导入失败: {e}")
                messagebox.showerror("错误", f"导入失败: {e}")

    def _export_papers(self):
        """导出文献"""
        if not self.selected_papers:
            self.selected_papers = self.filtered_papers

        file_path = filedialog.asksaveasfilename(
            title="导出文献",
            defaultextension=".json",
            filetypes=[
                ("JSON 文件", "*.json"),
                ("CSV 文件", "*.csv"),
                ("BibTeX 文件", "*.bib")
            ]
        )

        if file_path:
            self.logger.info(f"导出 {len(self.selected_papers)} 篇文献到: {file_path}")

            try:
                import json
                import csv

                # 根据文件类型导出
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.selected_papers, f, ensure_ascii=False, indent=2)

                elif file_path.endswith('.csv'):
                    with open(file_path, 'w', encoding='utf-8', newline='') as f:
                        if self.selected_papers:
                            writer = csv.DictWriter(f, fieldnames=self.selected_papers[0].keys())
                            writer.writeheader()
                            writer.writerows(self.selected_papers)

                elif file_path.endswith('.bib'):
                    # BibTeX 导出
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for i, paper in enumerate(self.selected_papers):
                            f.write(f"@article{{ref{i+1},\n")
                            f.write(f"  title = {{{paper.get('title', '')}}},\n")
                            f.write(f"  author = {{{paper.get('authors', '')}}},\n")
                            f.write(f"  year = {{{paper.get('year', '')}}},\n")
                            f.write(f"  journal = {{{paper.get('journal', '')}}},\n")
                            f.write("}\n\n")

                messagebox.showinfo("成功", f"成功导出 {len(self.selected_papers)} 篇文献")

            except Exception as e:
                self.logger.error(f"导出失败: {e}")
                messagebox.showerror("错误", f"导出失败: {e}")
