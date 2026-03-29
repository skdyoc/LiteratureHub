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
Page 1 GUI - 文献下载与管理（中文界面）

用法：
    python scripts/page1_gui.py
"""

import sys
import json
import threading
import asyncio
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Page1GUI:
    """Page 1 GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LiteratureHub - 统一学术文献研究系统")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)

        # Default project directory
        self.project_dir = project_root / "data" / "projects" / "wind_aero"
        self.workflow = None
        self.papers = []
        self.filtered_papers = []

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("Page1GUI")

        # Build UI
        self._setup_styles()
        self._build_ui()
        self._load_project_data()

    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Microsoft YaHei", 14, "bold"))
        style.configure("Header.TLabel", font=("Microsoft YaHei", 11, "bold"))
        style.configure("Stats.TLabel", font=("Microsoft YaHei", 10))
        style.configure("Success.TLabel", foreground="green", font=("Microsoft YaHei", 10, "bold"))
        style.configure("Warning.TLabel", foreground="orange", font=("Microsoft YaHei", 10, "bold"))
        style.configure("Error.TLabel", foreground="red", font=("Microsoft YaHei", 10, "bold"))
        style.configure("Action.TButton", font=("Microsoft YaHei", 10))
        style.configure("Big.TButton", font=("Microsoft YaHei", 10, "bold"), padding=6)

    def _build_ui(self):
        """Build the complete UI"""
        self._create_menu()

        # ⭐ NEW: 创建 Notebook 用于页面切换
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Page 1: 文献管理
        self.page1_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.page1_frame, text="📚 文献管理")

        # 在 Page 1 上构建原有内容
        # Main paned window
        main_paned = ttk.PanedWindow(self.page1_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        self._build_left_panel(left_frame)

        # Right panel
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        self._build_right_panel(right_frame)

        # Page 2: AI 分析
        try:
            from src.gui.page2_gui import Page2GUI
            self.page2 = Page2GUI(self.notebook, self.project_dir)
            self.notebook.add(self.page2.frame, text="🧠 AI 分析")
        except ImportError as e:
            self.logger.error(f"无法导入 Page 2: {e}")
            print(f"[!] 无法导入 Page 2: {e}")

        # Status bar（在 Notebook 下方）
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开项目...", command=self._open_project)
        file_menu.add_command(label="刷新数据", command=self._load_project_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        workflow_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工作流", menu=workflow_menu)
        workflow_menu.add_command(label="1. Elsevier 搜索...", command=self._action_search)
        workflow_menu.add_command(label="2. SciHub 下载", command=self._action_download)
        workflow_menu.add_command(label="3. 处理临时 PDF", command=self._action_process_temp)
        workflow_menu.add_command(label="4. 手动下载列表", command=self._action_manual_list)
        workflow_menu.add_command(label="5. 文献分类...", command=self._action_classify)
        workflow_menu.add_command(label="6. MinerU 转换", command=self._action_convert)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=lambda: messagebox.showinfo(
            "关于", "LiteratureHub v1.0\nPage 1: 文献管理\n\n(c) 2025-2026"
        ))

    def _build_left_panel(self, parent):
        """Build left panel"""
        # === Statistics Dashboard ===
        stats_frame = ttk.LabelFrame(parent, text="仪表盘", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.project_label = ttk.Label(stats_frame, text="项目: --", style="Header.TLabel")
        self.project_label.pack(anchor=tk.W)

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, pady=5)

        labels = [
            ("文献总数:", "total_papers"),
            ("已下载:", "pdf_downloaded"),
            ("下载率:", "download_rate"),
            ("已分类:", "classified"),
            ("分类数:", "categories"),
            ("Markdown:", "markdown"),
        ]
        self.stat_labels = {}
        for i, (text, key) in enumerate(labels):
            row, col = divmod(i, 2)
            ttk.Label(stats_grid, text=text, style="Stats.TLabel").grid(
                row=row, column=col * 2, sticky=tk.W, padx=5, pady=2
            )
            lbl = ttk.Label(stats_grid, text="--", style="Stats.TLabel")
            lbl.grid(row=row, column=col * 2 + 1, sticky=tk.W, padx=5, pady=2)
            self.stat_labels[key] = lbl

        # === Data Management ===
        manage_frame = ttk.LabelFrame(parent, text="数据管理", padding=10)
        manage_frame.pack(fill=tk.X, padx=5, pady=5)

        manage_info = ttk.Label(manage_frame, text="未下载文献占用大量空间，建议定期清理",
                                style="Warning.TLabel", wraplength=200)
        manage_info.pack(pady=(0, 5))

        manage_btn = ttk.Button(manage_frame, text="🗑️ 隔离未下载文献",
                               command=self._action_isolate_undownloaded,
                               style="Action.TButton")
        manage_btn.pack(fill=tk.X, pady=2)

        # === Workflow Actions ===
        actions_frame = ttk.LabelFrame(parent, text="工作流操作", padding=10)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        buttons = [
            ("1. Elsevier 搜索", self._action_search),
            ("2. SciHub 下载", self._action_download),
            ("3. 处理临时文件", self._action_process_temp),
            ("4. 手动下载列表", self._action_manual_list),
            ("5. 文献分类", self._action_classify),
            ("6. MinerU 转换", self._action_convert),
        ]
        for text, cmd in buttons:
            btn = ttk.Button(actions_frame, text=text, command=cmd, style="Big.TButton")
            btn.pack(fill=tk.X, pady=2)

        # === Progress ===
        progress_frame = ttk.LabelFrame(parent, text="进度", padding=5)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=2)
        self.progress_label = ttk.Label(progress_frame, text="空闲")
        self.progress_label.pack(anchor=tk.W)

        # === Log ===
        log_frame = ttk.LabelFrame(parent, text="日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_container, height=10, wrap=tk.WORD, font=("Microsoft YaHei", 9))
        log_scroll = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")

    def _build_right_panel(self, parent):
        """Build right panel"""
        # Search bar
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.filter_var = tk.StringVar(value="all")
        filters = [("全部", "all"), ("已下载", "downloaded"), ("未下载", "not_downloaded")]
        for text, value in filters:
            ttk.Radiobutton(
                search_frame, text=text, value=value,
                variable=self.filter_var, command=self._apply_filter
            ).pack(side=tk.LEFT, padx=3)

        ttk.Button(search_frame, text="刷新", command=self._load_project_data).pack(side=tk.RIGHT, padx=5)

        # Paper count
        self.count_label = ttk.Label(parent, text="0 篇文献")
        self.count_label.pack(anchor=tk.W, padx=10)

        # Paper list (Treeview)
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("year", "title", "authors", "journal", "downloaded", "doi")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("year", text="年份")
        self.tree.heading("title", text="标题")
        self.tree.heading("authors", text="作者")
        self.tree.heading("journal", text="期刊")
        self.tree.heading("downloaded", text="PDF")
        self.tree.heading("doi", text="DOI")

        self.tree.column("year", width=60, anchor=tk.CENTER)
        self.tree.column("title", width=350, minwidth=200)
        self.tree.column("authors", width=180, minwidth=100)
        self.tree.column("journal", width=150, minwidth=80)
        self.tree.column("downloaded", width=60, anchor=tk.CENTER)
        self.tree.column("doi", width=120, minwidth=80)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_paper_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_paper_select)

        # Detail panel
        detail_frame = ttk.LabelFrame(parent, text="文献详情", padding=5)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)

        self.detail_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, font=("Microsoft YaHei", 9))
        self.detail_text.pack(fill=tk.BOTH, expand=True)

    # ==================== Data Loading ====================

    def _load_project_data(self):
        """Load project metadata and update UI"""
        try:
            metadata_file = self.project_dir / "pdfs" / "all" / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.papers = json.load(f)
                self._log(f"已加载 {len(self.papers)} 篇文献", "SUCCESS")
            else:
                self.papers = []
                self._log("未找到 metadata.json", "WARNING")

            self.project_label.config(text=f"项目: {self.project_dir.name}")

            # Load categories
            cat_dir = self.project_dir / "pdfs" / "categories"
            categories = [d.name for d in cat_dir.iterdir() if d.is_dir()] if cat_dir.exists() else []

            classified_count = 0
            for cat_name in categories:
                tilu_file = cat_dir / cat_name / "\u9898\u5f55.json"
                if tilu_file.exists():
                    with open(tilu_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # 题录.json 可能是 list 或 dict 格式
                        if isinstance(data, list):
                            # 新格式：直接是文献列表
                            classified_count += len(data)
                        elif isinstance(data, dict):
                            # 旧格式：{"total": N, "papers": [...]}
                            classified_count += data.get("total", len(data.get("papers", [])))
                        else:
                            # 其他格式：尝试获取长度
                            try:
                                classified_count += len(data)
                            except:
                                pass

            md_dir = self.project_dir / "markdown"
            md_count = len(list(md_dir.rglob("*.md"))) if md_dir.exists() else 0

            total = len(self.papers)
            downloaded = sum(1 for p in self.papers if p.get("pdf_downloaded"))
            rate = f"{downloaded/total*100:.1f}%" if total > 0 else "0%"

            self.stat_labels["total_papers"].config(text=str(total))
            self.stat_labels["pdf_downloaded"].config(text=f"{downloaded}/{total}")
            self.stat_labels["download_rate"].config(text=rate)
            self.stat_labels["classified"].config(text=str(classified_count))
            self.stat_labels["categories"].config(text=str(len(categories)))
            self.stat_labels["markdown"].config(text=str(md_count))

            self._apply_filter()
            self._log("仪表盘已更新", "INFO")

        except Exception as e:
            self._log(f"加载项目数据失败: {e}", "ERROR")

    def _apply_filter(self):
        """Apply search filter and update tree"""
        query = self.search_var.get().lower()
        filter_type = self.filter_var.get()

        self.filtered_papers = []
        for p in self.papers:
            if filter_type == "downloaded" and not p.get("pdf_downloaded"):
                continue
            if filter_type == "not_downloaded" and p.get("pdf_downloaded"):
                continue

            if query:
                title = p.get("title", "").lower()
                authors = " ".join(p.get("authors", [])).lower()
                abstract = p.get("abstract", "").lower()
                doi = p.get("doi", "").lower()
                combined = f"{title} {authors} {abstract} {doi}"
                if query not in combined:
                    continue

            self.filtered_papers.append(p)

        self._update_tree()
        self.count_label.config(text=f"{len(self.filtered_papers)} 篇 (共 {len(self.papers)} 篇)")

    def _update_tree(self):
        """Update treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 安全获取年份为数字用于排序
        def get_year_num(paper):
            y = paper.get("year")
            if y is None:
                return 0
            if isinstance(y, int):
                return y
            if isinstance(y, str) and y.isdigit():
                return int(y)
            return 0

        sorted_papers = sorted(
            self.filtered_papers,
            key=get_year_num,
            reverse=True
        )

        for i, paper in enumerate(sorted_papers):
            title = paper.get("title", "")[:80]
            authors = "; ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " 等"
            year = paper.get("year", "")
            # 标准化年份显示
            if year and isinstance(year, int):
                year = str(year)
            elif year and isinstance(year, str):
                year = year if year.isdigit() else ""
            else:
                year = ""
            journal = paper.get("journal", "") or ""
            if journal and len(journal) > 30:
                journal = journal[:27] + "..."
            downloaded = "是" if paper.get("pdf_downloaded") else "否"
            doi = paper.get("doi", "") or ""

            self.tree.insert("", tk.END, iid=str(i), values=(
                year, title, authors, journal, downloaded, doi
            ))

    def _on_search(self, *args):
        self._apply_filter()

    def _on_paper_select(self, event):
        selection = self.tree.selection()
        if selection:
            idx = int(selection[0])
            if 0 <= idx < len(self.filtered_papers):
                paper = self.filtered_papers[idx]
                self._show_paper_detail(paper)

    def _on_paper_double_click(self, event):
        self._on_paper_select(event)

    def _show_paper_detail(self, paper):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)

        lines = [
            f"标题: {paper.get('title', 'N/A')}",
            f"作者: {'; '.join(paper.get('authors', []))}",
            f"年份: {paper.get('year', 'N/A')}",
            f"期刊: {paper.get('journal', 'N/A')}",
            f"DOI: {paper.get('doi', 'N/A')}",
            f"PDF: {'已下载' if paper.get('pdf_downloaded') else '未下载'}",
            f"关键词: {'; '.join(paper.get('keywords', []))}",
            "",
            f"摘要: {paper.get('abstract', 'N/A')[:500]}",
        ]
        self.detail_text.insert(1.0, "\n".join(lines))
        self.detail_text.config(state=tk.DISABLED)

    # ==================== Workflow Actions ====================

    def _get_workflow(self):
        if self.workflow is None:
            try:
                from src.workflow.page1_workflow import Page1Workflow
                self.workflow = Page1Workflow(
                    project_dir=str(self.project_dir),
                    api_key="12c246d28f9c4eed838447b78644356a"
                )
                self._log("Page1Workflow 已初始化", "SUCCESS")
            except Exception as e:
                self._log(f"初始化工作流失败: {e}", "ERROR")
                return None
        return self.workflow

    def _run_in_thread(self, func, *args, **kwargs):
        self._log(f"[DEBUG] _run_in_thread 被调用, func={func.__name__}", "INFO")

        def wrapper():
            self._log(f"[DEBUG] wrapper 函数开始执行", "INFO")
            try:
                self._log(f"[DEBUG] 准备调用 {func.__name__}()", "INFO")
                func(*args, **kwargs)
                self._log(f"[DEBUG] {func.__name__}() 执行完成", "INFO")
            except Exception as e:
                self._log(f"[DEBUG] {func.__name__}() 抛出异常: {e}", "ERROR")
                import traceback
                self._log(f"[DEBUG] 异常堆栈:\n{traceback.format_exc()}", "ERROR")
                self.root.after(0, lambda: self._log(f"错误: {e}", "ERROR"))
                self.root.after(0, lambda: self.status_label.config(text=f"错误: {e}"))

        self._log(f"[DEBUG] 创建 daemon 线程", "INFO")
        thread = threading.Thread(target=wrapper, daemon=True)
        self._log(f"[DEBUG] 启动线程", "INFO")
        thread.start()
        self._log(f"[DEBUG] 线程已启动", "INFO")

    def _action_search(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Elsevier 搜索")
        dialog.geometry("600x550")  # 增加高度确保所有选项可见
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="关键词（逗号分隔，支持中文自动翻译）:").pack(anchor=tk.W)
        kw_entry = ttk.Entry(frame, width=60)
        kw_entry.pack(fill=tk.X, pady=2)
        kw_entry.insert(0, "大型风机, 气动性能")

        # 翻译预览区域
        trans_frame = ttk.LabelFrame(frame, text="翻译预览", padding=5)
        trans_frame.pack(fill=tk.X, pady=5)
        trans_label = ttk.Label(trans_frame, text="点击「翻译预览」查看英文关键词", foreground="gray")
        trans_label.pack(anchor=tk.W)

        def do_translate_preview():
            """翻译预览"""
            from src.search.keyword_translator import KeywordTranslationAgent
            import re

            raw = kw_entry.get()
            keywords = [k.strip() for k in raw.split(",") if k.strip()]

            # 检测是否包含中文
            has_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)

            if not has_chinese:
                trans_label.config(text=f"纯英文关键词（无需翻译）: {', '.join(keywords)}", foreground="green")
                return

            # 使用翻译 Agent
            try:
                translator = KeywordTranslationAgent()
                translated = translator.translate_keywords(keywords)
                trans_label.config(
                    text=f"{', '.join(keywords)}  →  {', '.join(translated)}",
                    foreground="blue"
                )
            except Exception as e:
                trans_label.config(text=f"翻译失败: {e}", foreground="red")

        ttk.Button(trans_frame, text="翻译预览", command=do_translate_preview).pack(anchor=tk.E, pady=2)

        ttk.Label(frame, text="排除关键词（逗号分隔）:").pack(anchor=tk.W, pady=(10, 0))
        ex_entry = ttk.Entry(frame, width=60)
        ex_entry.pack(fill=tk.X, pady=2)
        ex_entry.insert(0, "vertical axis, VAWT, Darrieus, Savonius")

        year_frame = ttk.Frame(frame)
        year_frame.pack(fill=tk.X, pady=10)
        ttk.Label(year_frame, text="年份 从:").pack(side=tk.LEFT)
        year_from = ttk.Spinbox(year_frame, from_=1990, to=2030, width=6)
        year_from.set(2020)
        year_from.pack(side=tk.LEFT, padx=5)
        ttk.Label(year_frame, text="到:").pack(side=tk.LEFT)
        year_to = ttk.Spinbox(year_frame, from_=1990, to=2030, width=6)
        year_to.set(2026)
        year_to.pack(side=tk.LEFT, padx=5)

        max_frame = ttk.Frame(frame)
        max_frame.pack(fill=tk.X, pady=5)
        ttk.Label(max_frame, text="最大结果数:").pack(side=tk.LEFT)
        max_entry = ttk.Spinbox(max_frame, from_=10, to=500, width=6)
        max_entry.set(100)
        max_entry.pack(side=tk.LEFT, padx=5)

        # 匹配模式选项
        match_frame = ttk.LabelFrame(frame, text="匹配模式", padding=5)
        match_frame.pack(fill=tk.X, pady=10)

        # 匹配字段复选框
        fields_frame = ttk.Frame(match_frame)
        fields_frame.pack(fill=tk.X, pady=2)
        ttk.Label(fields_frame, text="匹配字段:").pack(side=tk.LEFT, padx=5)

        match_title_var = tk.BooleanVar(value=True)
        match_keywords_var = tk.BooleanVar(value=True)
        match_abstract_var = tk.BooleanVar(value=True)

        # 使用 tk.Checkbutton 显示传统对勾符号
        tk.Checkbutton(fields_frame, text="标题", variable=match_title_var,
                       bg="#f0f0f0", activebackground="#e0e0e0",
                       fg="#000000", selectcolor="#e1f5ff").pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(fields_frame, text="关键词", variable=match_keywords_var,
                       bg="#f0f0f0", activebackground="#e0e0e0",
                       fg="#000000", selectcolor="#e1f5ff").pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(fields_frame, text="摘要", variable=match_abstract_var,
                       bg="#f0f0f0", activebackground="#e0e0e0",
                       fg="#000000", selectcolor="#e1f5ff").pack(side=tk.LEFT, padx=5)

        # 添加状态标签显示当前选择
        match_status_var = tk.StringVar(value="当前选择: 标题 + 关键词 + 摘要")
        match_status_label = ttk.Label(fields_frame, textvariable=match_status_var, foreground="blue")
        match_status_label.pack(side=tk.LEFT, padx=10)

        def update_match_status(*args):
            """更新匹配状态显示"""
            selected = []
            if match_title_var.get():
                selected.append("标题")
            if match_keywords_var.get():
                selected.append("关键词")
            if match_abstract_var.get():
                selected.append("摘要")

            if selected:
                combo_str = " + ".join(selected)
                match_status_var.set(f"当前选择: {combo_str}")
            else:
                match_status_var.set("当前选择: (未选择)")

        # 绑定复选框状态变化
        match_title_var.trace_add("write", update_match_status)
        match_keywords_var.trace_add("write", update_match_status)
        match_abstract_var.trace_add("write", update_match_status)

        # 组合模式
        combo_frame = ttk.Frame(match_frame)
        combo_frame.pack(fill=tk.X, pady=5)
        ttk.Label(combo_frame, text="组合模式:").pack(side=tk.LEFT, padx=5)

        combo_mode_var = tk.StringVar(value="all")
        tk.Radiobutton(combo_frame, text="全部匹配(AND)", variable=combo_mode_var, value="all",
                     bg="#f0f0f0", activebackground="#e0e0e0", fg="#000000").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(combo_frame, text="至少一个(OR)", variable=combo_mode_var, value="any",
                     bg="#f0f0f0", activebackground="#e0e0e0", fg="#000000").pack(side=tk.LEFT, padx=5)

        def do_search():
            keywords = [k.strip() for k in kw_entry.get().split(",") if k.strip()]
            exclude = [k.strip() for k in ex_entry.get().split(",") if k.strip()]
            try:
                yr_from = int(year_from.get())
                yr_to = int(year_to.get())
                year_range = (yr_from, yr_to)
            except ValueError:
                year_range = None
            try:
                max_res = int(max_entry.get())
            except ValueError:
                max_res = 100

            # 收集匹配模式
            match_fields = []
            if match_title_var.get():
                match_fields.append("title")
            if match_keywords_var.get():
                match_fields.append("keywords")
            if match_abstract_var.get():
                match_fields.append("abstract")

            # 如果没有选择任何字段，默认全部
            if not match_fields:
                match_fields = ["title", "keywords", "abstract"]

            match_mode = {
                "fields": match_fields,
                "combination": combo_mode_var.get()  # "all" or "any"
            }

            dialog.destroy()
            self._execute_search(keywords, exclude, year_range, max_res, match_mode)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="搜索", command=do_search, style="Big.TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _execute_search(self, keywords, exclude, year_range, max_results, match_mode=None):
        workflow = self._get_workflow()
        if not workflow:
            return

        # 构建匹配模式描述
        if match_mode:
            fields_desc = ", ".join({
                "title": "标题",
                "keywords": "关键词",
                "abstract": "摘要"
            }.get(f, f) for f in match_mode["fields"])
            combo_desc = "全部匹配" if match_mode["combination"] == "all" else "至少一个"
            mode_desc = f"{fields_desc} - {combo_desc}"
            self._log(f"开始 Elsevier 搜索: {keywords} | 模式: {mode_desc}", "INFO")
        else:
            self._log(f"开始 Elsevier 搜索: {keywords}", "INFO")

        self.status_label.config(text="搜索中...")

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    workflow.search_elsevier(
                        keywords=keywords,
                        max_results=max_results,
                        year_range=year_range,
                        exclude_keywords=exclude if exclude else None,
                        match_mode=match_mode
                    )
                )
                self.root.after(0, lambda: self._log(f"搜索完成: 找到 {len(results)} 篇文献", "SUCCESS"))
                self.root.after(0, lambda: self.status_label.config(text=f"搜索完成: {len(results)} 篇"))
                self.root.after(0, self._load_project_data)
            except Exception as e:
                self.root.after(0, lambda: self._log(f"搜索失败: {e}", "ERROR"))
                self.root.after(0, lambda: self.status_label.config(text="搜索失败"))
            finally:
                loop.close()

        self._run_in_thread(run)

    def _action_download(self):
        workflow = self._get_workflow()
        if not workflow:
            return

        if not messagebox.askyesno("确认", "开始 SciHub 下载工作流？\n这可能需要较长时间。"):
            return

        self._log("开始下载工作流...", "INFO")
        self.status_label.config(text="下载中...")

        def run():
            results = workflow.run_download_workflow(
                progress_callback=lambda cur, total, res: self.root.after(
                    0, lambda: self._update_progress(cur, total, f"下载中 {cur}/{total}")
                )
            )
            self.root.after(0, lambda: self._log(
                f"下载完成: 成功 {results.get('success', 0)} 篇, 失败 {results.get('failed', 0)} 篇",
                "SUCCESS"
            ))
            self.root.after(0, lambda: self.status_label.config(text="下载完成"))
            self.root.after(0, self._load_project_data)

        self._run_in_thread(run)

    def _action_process_temp(self):
        workflow = self._get_workflow()
        if not workflow:
            return

        self._log("处理临时 PDF 文件...", "INFO")
        self.status_label.config(text="处理中...")

        def run():
            count = workflow.process_temp_pdfs()
            self.root.after(0, lambda: self._log(f"已处理 {count} 个临时 PDF", "SUCCESS"))
            self.root.after(0, lambda: self.status_label.config(text=f"已处理 {count} 个文件"))
            self.root.after(0, self._load_project_data)

        self._run_in_thread(run)

    def _action_manual_list(self):
        workflow = self._get_workflow()
        if not workflow:
            return

        try:
            output = workflow.generate_manual_download_list()
            self._log(f"手动下载列表已生成: {output}", "SUCCESS")
            messagebox.showinfo("成功", f"手动下载列表已保存至:\n{output}")
        except Exception as e:
            self._log(f"操作失败: {e}", "ERROR")
            messagebox.showerror("错误", str(e))

    def _action_classify(self):
        workflow = self._get_workflow()
        if not workflow:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("文献分类")
        dialog.geometry("550x400")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # 说明
        info_label = ttk.Label(
            frame,
            text="AI 批量分类：输入您关心的技术领域，Agent 判断每篇论文的相关度",
            font=("", 9)
        )
        info_label.pack(pady=10)

        # === 领域输入 ===
        domain_frame = ttk.LabelFrame(frame, text="技术领域（每行一个）", padding=10)
        domain_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(domain_frame, text="请输入您关心的技术领域，每行一个：").pack(anchor=tk.W)

        domain_text = tk.Text(domain_frame, height=6, width=50)
        domain_text.pack(fill=tk.BOTH, expand=True, pady=5)
        domain_text.insert("1.0", "气动优化\n海上风电\n控制系统\n结构设计")

        domain_help = ttk.Label(
            domain_frame,
            text="提示：Agent 会判断每篇论文与这些领域的相关度（0-1.0）\n相关度 ≥ 70% 的论文会自动归类到对应文件夹",
            font=("", 8),
            foreground="gray"
        )
        domain_help.pack(anchor=tk.W)

        # === 批量分类设置 ===
        batch_frame = ttk.LabelFrame(frame, text="批量分类设置", padding=10)
        batch_frame.pack(fill=tk.X, pady=5)

        ttk.Label(batch_frame, text="每批处理文献数量 (10-50):").pack(anchor=tk.W)
        batch_size_entry = ttk.Entry(batch_frame, width=20)
        batch_size_entry.pack(fill=tk.X, pady=2)
        batch_size_entry.insert(0, "50")

        batch_help = ttk.Label(
            batch_frame,
            text="推荐值：50（平衡速度与稳定性）",
            font=("", 8),
            foreground="gray"
        )
        batch_help.pack(anchor=tk.W)

        def do_classify():
            # AI 批量分类
            # 1. 获取用户输入的领域列表
            domain_input = domain_text.get("1.0", "end-1c")
            domains = [line.strip() for line in domain_input.split("\n") if line.strip()]

            if not domains:
                messagebox.showwarning("提示", "请输入至少一个技术领域")
                return

            # 2. 获取批次大小
            try:
                user_batch_size = int(batch_size_entry.get())
                if user_batch_size < 10:
                    user_batch_size = 10
                elif user_batch_size > 50:
                    user_batch_size = 50
            except ValueError:
                user_batch_size = 50

            domain_list = "\n".join([f"  • {d}" for d in domains])
            if not messagebox.askyesno("确认", f"开始 AI 批量分类？\n\n技术领域（共 {len(domains)} 个）：\n{domain_list}\n\n设置：每批 {user_batch_size} 篇文献\n\n是否继续？"):
                return

            dialog.destroy()
            self._log(f"正在启动 AI 批量分类，领域：{domains}", "INFO")
            self.status_label.config(text="批量分类中...")

            def progress_callback(current, total, message):
                def update():
                    if total == 0:
                        self._log(message, "INFO")
                    else:
                        self._log(f"[{current}/{total}] {message}", "INFO")
                self.root.after(0, update)

            def run_batch():
                self._log("[DEBUG] run_batch 函数开始执行", "INFO")
                try:
                    self._log("[DEBUG] 准备调用 workflow.classify_papers_ai_batch()", "INFO")
                    self._log(f"[DEBUG] domains={domains}, batch_size={user_batch_size}", "INFO")
                    stats = workflow.classify_papers_ai_batch(
                        domains=domains,
                        progress_callback=progress_callback,
                        batch_size=user_batch_size
                    )
                    self._log("[DEBUG] workflow.classify_papers_ai_batch() 返回", "INFO")

                    def show_result():
                        if "error" in stats:
                            self._log(f"批量分类失败: {stats['error']}", "ERROR")
                            messagebox.showerror("错误", stats['error'])
                        else:
                            msg = f"AI 批量分类完成！\n\n"
                            msg += f"统计信息：\n"
                            msg += f"  总文献数: {stats['total']}\n"
                            msg += f"  本次分类: {stats['classified']}\n"
                            msg += f"  已分类: {stats['already_classified']}\n"
                            if stats.get('failed', 0) > 0:
                                msg += f"  失败: {stats['failed']}\n"

                            msg += f"\n领域分布：\n"
                            for domain, count in sorted(stats['domain_distribution'].items(), key=lambda x: x[1], reverse=True):
                                msg += f"  {domain}: {count} 篇\n"

                            messagebox.showinfo("批量分类完成", msg)
                            self._log(f"AI 批量分类完成: {stats['classified']} 篇", "SUCCESS")
                            self.status_label.config(text=f"已分类 {stats['classified']} 篇")
                            self._load_project_data

                    self.root.after(0, show_result)

                except Exception as e:
                    def show_error():
                        self._log(f"批量分类出错: {e}", "ERROR")
                        messagebox.showerror("错误", f"批量分类失败：{e}")
                    self.root.after(0, show_error)

            self._log("[DEBUG] 准备启动后台线程...", "INFO")
            self._run_in_thread(run_batch)
            self._log("[DEBUG] _run_in_thread() 调用完成", "INFO")

        ttk.Button(frame, text="开始分类", command=do_classify).pack(pady=10)

    def _action_convert(self):
        workflow = self._get_workflow()
        if not workflow:
            return

        # 获取可用的分类列表
        categories_dir = self.project_dir / "pdfs" / "categories"
        available_categories = ["all"]  # 默认选项

        if categories_dir.exists():
            for item in categories_dir.iterdir():
                if item.is_dir():
                    available_categories.append(item.name)

        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择要转换的目录")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="请选择要转换为 Markdown 的目录：", font=("", 10, "bold")).pack(pady=10)

        # 目录选择列表
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        category_var = tk.StringVar(value="all")

        for category in available_categories:
            rb = ttk.Radiobutton(
                list_frame,
                text=f"{'📁 ' + category if category != 'all' else '📚 all (全部文献)'}",
                variable=category_var,
                value=category
            )
            rb.pack(anchor=tk.W, pady=2)

        # PDF 统计信息
        info_frame = ttk.LabelFrame(dialog, text="目录信息", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        def show_info():
            selected = category_var.get()
            if selected == "all":
                source_dir = self.project_dir / "pdfs" / "all"
            else:
                source_dir = categories_dir / selected

            pdf_count = len(list(source_dir.glob("*.pdf"))) if source_dir.exists() else 0
            info_label.config(text=f"📊 {selected} 目录包含 {pdf_count} 个 PDF 文件")

        info_label = ttk.Label(info_frame, text="请选择一个目录", font=("", 9))
        info_label.pack()

        # 绑定选择事件
        for widget in list_frame.winfo_children():
            if isinstance(widget, ttk.Radiobutton):
                widget.configure(command=show_info)

        # 初始化显示
        show_info()

        def do_convert():
            selected = category_var.get()
            dialog.destroy()

            confirm_msg = f"开始 MinerU 转换？\n\n"
            confirm_msg += f"目标目录: {selected}\n"
            confirm_msg += f"这可能需要非常长的时间。"

            if not messagebox.askyesno("确认", confirm_msg):
                return

            category_name = None if selected == "all" else selected

            self._log(f"开始 MinerU 转换: {selected} 目录...", "INFO")
            self.status_label.config(text="转换中...")

            def run():
                count = workflow.convert_to_markdown(
                    category_name=category_name,
                    progress_callback=lambda cur, total, name: self.root.after(
                        0, lambda: self._update_progress(cur, total, f"转换中: {name}")
                    )
                )
                self.root.after(0, lambda: self._log(f"已转换 {count} 个 PDF 为 Markdown", "SUCCESS"))
                self.root.after(0, lambda: self.status_label.config(text=f"已转换 {count} 个文件"))
                self.root.after(0, self._load_project_data)

            self._run_in_thread(run)

        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(btn_frame, text="开始转换", command=do_convert).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def _action_isolate_undownloaded(self):
        """隔离未下载的文献到归档文件"""
        # 统计未下载文献
        undownloaded = [p for p in self.papers if not p.get("pdf_downloaded", False)]
        downloaded = [p for p in self.papers if p.get("pdf_downloaded", False)]

        if not undownloaded:
            messagebox.showinfo("提示", "所有文献都已下载，无需清理！")
            return

        # 确认对话框
        msg = f"发现 {len(undownloaded)} 篇未下载文献：\n\n"
        msg += f"✅ 已下载: {len(downloaded)} 篇\n"
        msg += f"❌ 未下载: {len(undownloaded)} 篇\n\n"
        msg += "是否隔离这些未下载的文献？\n"
        msg += "（它们将被移至 archived_undownloaded.json，不再显示在列表中）"

        if not messagebox.askyesno("确认隔离", msg):
            return

        self._log(f"开始隔离 {len(undownloaded)} 篇未下载文献...", "INFO")

        try:
            # 1. 备份未下载文献到归档文件
            metadata_file = self.project_dir / "pdfs" / "all" / "metadata.json"
            archive_file = self.project_dir / "pdfs" / "all" / "archived_undownloaded.json"

            # 读取现有归档
            archived = []
            if archive_file.exists():
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archived = json.load(f)

            # 追加新的未下载文献
            archived.extend(undownloaded)

            # 保存归档
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(archived, f, ensure_ascii=False, indent=2)

            # 2. 更新 metadata.json（只保留已下载的）
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(downloaded, f, ensure_ascii=False, indent=2)

            # 3. 刷新数据
            self.papers = downloaded
            self._load_project_data()

            # 4. 成功提示
            self._log(f"已隔离 {len(undownloaded)} 篇未下载文献", "SUCCESS")
            messagebox.showinfo("完成",
                               f"成功隔离 {len(undownloaded)} 篇文献！\n\n"
                               f"保留文献: {len(downloaded)} 篇\n"
                               f"归档文件: {archive_file.name}")

        except Exception as e:
            self._log(f"隔离失败: {e}", "ERROR")
            messagebox.showerror("错误", f"隔离失败：{e}")

    # ==================== Utilities ====================

    def _update_progress(self, current, total, message=""):
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar["value"] = pct
            self.progress_label.config(text=f"{current}/{total} ({pct}%) {message}")
        self.root.update_idletasks()

    def _log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n", level)
        self.log_text.see(tk.END)

    def _open_project(self):
        path = filedialog.askdirectory(title="选择项目目录")
        if path:
            self.project_dir = Path(path)
            self.workflow = None
            self._log(f"已打开项目: {self.project_dir}", "INFO")
            self._load_project_data()

    def run(self):
        self._log("LiteratureHub Page 1 GUI 已启动", "SUCCESS")
        self.root.mainloop()


def main():
    app = Page1GUI()
    app.run()


if __name__ == "__main__":
    main()
