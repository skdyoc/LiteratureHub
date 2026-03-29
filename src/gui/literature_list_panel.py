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
文献列表面板

显示和管理文献列表。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging


class LiteratureListPanel(ttk.Frame):
    """文献列表面板

    显示文献列表，支持搜索、筛选和操作。

    使用示例：
    ```python
    panel = LiteratureListPanel(parent, db_manager)
    panel.pack(fill=tk.BOTH, expand=True)

    # 刷新列表
    panel.refresh()

    # 获取选中的文献
    selected = panel.get_selected_papers()

    # 设置双击回调
    panel.set_double_click_callback(on_paper_double_click)
    ```
    """

    def __init__(self, parent, db_manager=None):
        """初始化文献列表面板

        Args:
            parent: 父窗口
            db_manager: 数据库管理器
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.papers: List[Dict[str, Any]] = []
        self.double_click_callback: Optional[Callable] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        self._create_widgets()
        self._load_papers()

    def _create_widgets(self):
        """创建界面组件"""
        # 顶部：搜索和筛选
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # 搜索框
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 筛选按钮
        ttk.Button(toolbar, text="高级筛选", command=self._show_filter_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=5)

        # 中部：文献列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建 Treeview
        columns = ("title", "authors", "year", "journal", "score", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")

        # 设置列标题
        self.tree.heading("title", text="标题")
        self.tree.heading("authors", text="作者")
        self.tree.heading("year", text="年份")
        self.tree.heading("journal", text="期刊")
        self.tree.heading("score", text="评分")
        self.tree.heading("status", text="状态")

        # 设置列宽
        self.tree.column("title", width=300)
        self.tree.column("authors", width=150)
        self.tree.column("year", width=60)
        self.tree.column("journal", width=150)
        self.tree.column("score", width=60)
        self.tree.column("status", width=80)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击事件
        self.tree.bind("<Double-1>", self._on_double_click)

        # 绑定右键菜单
        self.tree.bind("<Button-3>", self._show_context_menu)

        # 底部：操作按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="导入", command=self._import_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="导出", command=self._export_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="分析", command=self._analyze_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="删除", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

        # 统计信息
        self.stats_label = ttk.Label(button_frame, text="共 0 篇文献")
        self.stats_label.pack(side=tk.RIGHT, padx=5)

    def _load_papers(self):
        """加载文献列表"""
        if not self.db_manager:
            self.logger.warning("数据库管理器未配置")
            return

        try:
            # 从数据库加载文献
            self.papers = self.db_manager.query("papers", order_by="created_at DESC")
            self._update_tree()

        except Exception as e:
            self.logger.error(f"加载文献失败: {e}")
            messagebox.showerror("错误", f"加载文献失败: {e}")

    def _update_tree(self):
        """更新 Treeview"""
        # 清空现有项
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加文献
        for paper in self.papers:
            self.tree.insert("", tk.END, values=(
                paper.get("title", ""),
                ", ".join(paper.get("authors", [])[:3]),  # 只显示前 3 个作者
                paper.get("year", ""),
                paper.get("journal", ""),
                f"{paper.get('overall_score', 0):.1f}",
                paper.get("status", "未分析")
            ), tags=(paper.get("id"),))

        # 更新统计
        self.stats_label.config(text=f"共 {len(self.papers)} 篇文献")

    def _on_search(self, *args):
        """搜索回调"""
        query = self.search_var.get().lower()

        if not query:
            self._update_tree()
            return

        # 筛选文献
        filtered = []
        for paper in self.papers:
            if (query in paper.get("title", "").lower() or
                query in " ".join(paper.get("authors", [])).lower() or
                query in paper.get("abstract", "").lower()):
                filtered.append(paper)

        # 临时替换 papers 并更新
        original_papers = self.papers
        self.papers = filtered
        self._update_tree()
        self.papers = original_papers

    def _show_filter_dialog(self):
        """显示筛选对话框"""
        from tkinter import simpledialog

        # 简单的筛选对话框
        keyword = simpledialog.askstring("高级筛选", "请输入筛选关键词：")
        if keyword:
            self._filter_by_keyword(keyword)
            self.add_log(f"已筛选包含 '{keyword}' 的文献", "INFO")

    def refresh(self):
        """刷新文献列表"""
        self._load_papers()

    def get_selected_papers(self) -> List[Dict[str, Any]]:
        """获取选中的文献

        Returns:
            选中的文献列表
        """
        selected_ids = self.tree.selection()
        selected_papers = []

        for item_id in selected_ids:
            # 从 tags 中获取 paper id
            tags = self.tree.item(item_id, "tags")
            if tags:
                paper_id = tags[0]
                # 查找对应的 paper
                for paper in self.papers:
                    if paper.get("id") == paper_id:
                        selected_papers.append(paper)
                        break

        return selected_papers

    def set_double_click_callback(self, callback: Callable):
        """设置双击回调

        Args:
            callback: 回调函数(paper)
        """
        self.double_click_callback = callback

    def _on_double_click(self, event):
        """双击回调"""
        selected = self.get_selected_papers()
        if selected and self.double_click_callback:
            self.double_click_callback(selected[0])

    def _show_context_menu(self, event):
        """显示右键菜单"""
        # 选中右键点击的项
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)

        # 创建右键菜单
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="查看详情", command=lambda: self._view_details())
        menu.add_command(label="编辑", command=lambda: self._edit_paper())
        menu.add_separator()
        menu.add_command(label="标记为重要", command=lambda: self._mark_important())
        menu.add_command(label="标记为已读", command=lambda: self._mark_read())
        menu.add_separator()
        menu.add_command(label="删除", command=lambda: self._delete_selected())

        menu.post(event.x_root, event.y_root)

    def _import_papers(self):
        """导入文献

        支持的格式：
        - PDF: 提取文件名作为标题，需要用户补充其他信息
        - JSON: 完整的文献元数据
        - CSV: 文献表格数据
        - BibTeX: 引用格式（基础支持）
        """
        from tkinter import filedialog
        import os

        file_paths = filedialog.askopenfilenames(
            title="选择文献文件",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("BibTeX files", "*.bib"),
                ("All files", "*.*")
            ]
        )

        if file_paths:
            imported_count = 0
            for file_path in file_paths:
                try:
                    if file_path.endswith('.pdf'):
                        # PDF 导入：提取基本信息
                        paper = self._import_pdf(file_path)
                        if paper:
                            self.db_manager.insert("papers", paper)
                            imported_count += 1
                    elif file_path.endswith('.json'):
                        import json
                        with open(file_path, 'r', encoding='utf-8') as f:
                            papers = json.load(f)
                            for paper in (papers if isinstance(papers, list) else [papers]):
                                self.db_manager.insert("papers", paper)
                                imported_count += 1
                    elif file_path.endswith('.csv'):
                        import csv
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for paper in reader:
                                self.db_manager.insert("papers", paper)
                                imported_count += 1
                    elif file_path.endswith('.bib'):
                        papers = self._import_bibtex(file_path)
                        for paper in papers:
                            self.db_manager.insert("papers", paper)
                            imported_count += 1
                except Exception as e:
                    self.logger.error(f"导入失败 {file_path}: {e}")

            self.refresh()
            messagebox.showinfo("成功", f"成功导入 {imported_count} 篇文献")

    def _import_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """导入 PDF 文件

        Args:
            file_path: PDF 文件路径

        Returns:
            文献字典，包含从 PDF 提取的基本信息
        """
        import os
        from datetime import datetime

        # 从文件名提取标题
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]

        # 尝试从 PDF 提取元数据
        metadata = self._extract_pdf_metadata(file_path)

        paper = {
            "title": metadata.get("title") or title,
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year", datetime.now().year),
            "journal": metadata.get("journal", ""),
            "abstract": metadata.get("abstract", ""),
            "keywords": metadata.get("keywords", ""),
            "pdf_path": file_path
        }

        # 只有当 DOI 非空时才添加
        doi = metadata.get("doi", "").strip()
        if doi:
            paper["doi"] = doi

        return paper

    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """从 PDF 提取元数据

        Args:
            file_path: PDF 文件路径

        Returns:
            元数据字典
        """
        metadata = {}

        # 尝试使用 PyPDF2 提取元数据
        try:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                from pypdf import PdfReader

            reader = PdfReader(file_path)

            # 提取文档信息
            if reader.metadata:
                info = reader.metadata
                if info.title:
                    metadata["title"] = info.title
                if info.author:
                    metadata["authors"] = info.author
                if info.get("/CreationDate", ""):
                    # 提取年份
                    date_str = info.get("/CreationDate", "")
                    if date_str and len(date_str) >= 4:
                        try:
                            metadata["year"] = int(date_str[2:6])
                        except ValueError:
                            pass

            # 尝试从第一页提取摘要
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                text = first_page.extract_text() or ""
                # 简单的摘要提取（查找 Abstract 关键词）
                if "Abstract" in text:
                    start = text.find("Abstract")
                    abstract_text = text[start:start+1000]
                    # 清理文本
                    abstract_text = abstract_text.replace("Abstract", "").strip()[:500]
                    metadata["abstract"] = abstract_text

        except ImportError:
            self.logger.warning("PyPDF2 未安装，无法提取 PDF 元数据")
        except Exception as e:
            self.logger.warning(f"PDF 元数据提取失败: {e}")

        return metadata

    def _import_bibtex(self, file_path: str) -> List[Dict[str, Any]]:
        """导入 BibTeX 文件

        Args:
            file_path: BibTeX 文件路径

        Returns:
            文献列表
        """
        papers = []

        try:
            # 尝试使用 bibtexparser
            try:
                import bibtexparser
                with open(file_path, 'r', encoding='utf-8') as f:
                    bib_database = bibtexparser.load(f)
                    for entry in bib_database.entries:
                        paper = {
                            "title": entry.get("title", ""),
                            "authors": entry.get("author", ""),
                            "year": entry.get("year", ""),
                            "journal": entry.get("journal", ""),
                            "doi": entry.get("doi", ""),
                            "abstract": entry.get("abstract", ""),
                            "keywords": entry.get("keywords", "")
                        }
                        papers.append(paper)
            except ImportError:
                # 简单的正则解析
                import re
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取每个条目
                entries = re.findall(r'@\w+\{[^@]+\}', content, re.DOTALL)
                for entry in entries:
                    paper = {}
                    title_match = re.search(r'title\s*=\s*[{"\']([^}"\']+)[}"\']', entry)
                    if title_match:
                        paper["title"] = title_match.group(1)
                    author_match = re.search(r'author\s*=\s*[{"\']([^}"\']+)[}"\']', entry)
                    if author_match:
                        paper["authors"] = author_match.group(1)
                    year_match = re.search(r'year\s*=\s*[{"\']?(\d{4})[}"\']?', entry)
                    if year_match:
                        paper["year"] = int(year_match.group(1))
                    if paper.get("title"):
                        papers.append(paper)

        except Exception as e:
            self.logger.error(f"BibTeX 解析失败: {e}")

        return papers

    def _export_papers(self):
        """导出文献"""
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="导出文献",
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("BibTeX files", "*.bib")
            ]
        )

        if file_path:
            # 实现导出逻辑
            papers = self.get_selected_papers() or self.papers

            try:
                if file_path.endswith('.csv'):
                    import csv
                    with open(file_path, 'w', encoding='utf-8', newline='') as f:
                        if papers:
                            writer = csv.DictWriter(f, fieldnames=papers[0].keys())
                            writer.writeheader()
                            writer.writerows(papers)

                elif file_path.endswith('.xlsx'):
                    # Excel 导出需要 openpyxl
                    try:
                        from openpyxl import Workbook
                        wb = Workbook()
                        ws = wb.active
                        if papers:
                            ws.append(list(papers[0].keys()))
                            for paper in papers:
                                ws.append(list(paper.values()))
                        wb.save(file_path)
                    except ImportError:
                        messagebox.showerror("错误", "需要安装 openpyxl: pip install openpyxl")
                        return

                elif file_path.endswith('.bib'):
                    # BibTeX 导出
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for i, paper in enumerate(papers):
                            f.write(f"@article{{ref{i+1},\n")
                            f.write(f"  title = {{{paper.get('title', '')}}},\n")
                            f.write(f"  author = {{{paper.get('authors', '')}}},\n")
                            f.write(f"  year = {{{paper.get('year', '')}}},\n")
                            f.write("}\n\n")

                messagebox.showinfo("成功", f"成功导出 {len(papers)} 篇文献")

            except Exception as e:
                self.logger.error(f"导出失败: {e}")
                messagebox.showerror("错误", f"导出失败: {e}")

    def _analyze_selected(self):
        """分析选中的文献"""
        selected = self.get_selected_papers()
        if not selected:
            messagebox.showwarning("警告", "请先选择文献")
            return

        # 调用分析管理器
        try:
            from src.analysis.manager import AnalysisManager
            analysis_manager = AnalysisManager(self.db_manager)

            # 启动分析
            paper_ids = [p.get('id') for p in selected]
            analysis_manager.start_analysis(paper_ids)

            messagebox.showinfo("成功", f"已开始分析 {len(selected)} 篇文献")
        except Exception as e:
            self.logger.error(f"启动分析失败: {e}")
            messagebox.showerror("错误", f"启动分析失败: {e}")

    def _delete_selected(self):
        """删除选中的文献"""
        selected = self.get_selected_papers()
        if not selected:
            messagebox.showwarning("警告", "请先选择文献")
            return

        if messagebox.askyesno("确认", f"确定要删除 {len(selected)} 篇文献吗？"):
            # 实现删除逻辑
            for paper in selected:
                self.db_manager.delete("papers", {"id": paper.get("id")})

            self.refresh()
            messagebox.showinfo("成功", f"已删除 {len(selected)} 篇文献")

    def _view_details(self):
        """查看文献详情"""
        selected = self.get_selected_papers()
        if selected:
            paper = selected[0]

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
        selected = self.get_selected_papers()
        if selected:
            paper = selected[0]

            # 打开编辑窗口
            from tkinter import Toplevel, Entry, Label, Button, Text, Scrollbar
            edit_window = Toplevel(self)
            edit_window.title(f"编辑文献 - {paper.get('title', '')}")
            edit_window.geometry("600x500")

            # 添加编辑字段
            fields = {
                "标题": paper.get("title", ""),
                "作者": paper.get("authors", ""),
                "年份": paper.get("year", ""),
                "期刊/会议": paper.get("journal", ""),
                "DOI": paper.get("doi", ""),
                "关键词": ", ".join(paper.get("keywords", []))
            }

            entries = {}
            row = 0
            for label, value in fields.items():
                Label(edit_window, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="e")
                entry = Entry(edit_window, width=60)
                entry.insert(0, value)
                entry.grid(row=row, column=1, padx=5, pady=5)
                entries[label] = entry
                row += 1

            # 摘要字段（使用文本框）
            Label(edit_window, text="摘要").grid(row=row, column=0, padx=5, pady=5, sticky="ne")
            abstract_text = Text(edit_window, width=60, height=8)
            abstract_scrollbar = Scrollbar(edit_window, command=abstract_text.yview)
            abstract_text.configure(yscrollcommand=abstract_scrollbar.set)
            abstract_text.insert("1.0", paper.get("abstract", ""))
            abstract_text.grid(row=row, column=1, padx=5, pady=5)
            row += 1

            def save_changes():
                # 保存修改到数据库
                updated_data = {
                    "title": entries["标题"].get(),
                    "authors": entries["作者"].get(),
                    "year": entries["年份"].get(),
                    "journal": entries["期刊/会议"].get(),
                    "doi": entries["DOI"].get(),
                    "keywords": [k.strip() for k in entries["关键词"].get().split(",")],
                    "abstract": abstract_text.get("1.0", "end-1c")
                }
                self.db_manager.update("papers", updated_data, {"id": paper.get("id")})
                edit_window.destroy()
                self.refresh()
                messagebox.showinfo("成功", "文献信息已更新")

            Button(edit_window, text="保存", command=save_changes, width=20).grid(row=row, column=1, pady=10)

    def _mark_important(self):
        """标记为重要"""
        selected = self.get_selected_papers()
        for paper in selected:
            self.db_manager.update("papers", {"important": True}, {"id": paper.get("id")})

        self.refresh()
        messagebox.showinfo("成功", f"已标记 {len(selected)} 篇文献为重要")

    def _mark_read(self):
        """标记为已读"""
        selected = self.get_selected_papers()
        for paper in selected:
            self.db_manager.update("papers", {"read": True}, {"id": paper.get("id")})

        self.refresh()
        messagebox.showinfo("成功", f"已标记 {len(selected)} 篇文献为已读")
