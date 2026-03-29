"""
Page 2 GUI: AI 深度分析界面（预处理 + 双层并发 + GLM-4.7 / DeepSeek）

⭐ V5 架构改进：
1. 预处理模块（MinerU 预检查逻辑：all/ vs categories/）
2. Agent 调用模块（双层并发）：
   - 外层并发：多篇论文同时处理（ThreadPoolExecutor）
   - 内层并发：每篇论文的 5 个分析器并发执行（由 api_client.analyze_paper 处理）
3. 支持 GLM-4.7 和 DeepSeek 混合模式（chat + reasoner）
4. 实时显示分析进度
5. 显示各分析器状态
6. 实时日志输出
7. 支持暂停/继续
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(project_root))

from src.workflow.analysis_coordinator_v5 import AgentAnalysisCoordinatorV5


class Page2GUI:
    """Page 2: AI 深度分析界面（双层并发 + GLM-4.7）"""

    def __init__(self, parent, project_dir):
        """
        Args:
            parent: 父级 Notebook 控件（用于页面切换）
            project_dir: 项目目录（从 Page 1 传递）
        """
        self.parent = parent
        self.project_dir = Path(project_dir)
        self.frame = ttk.Frame(parent)

        # 状态变量
        self.is_running = False
        self.is_paused = False
        self.current_paper = ""
        self.total_papers = 0
        self.completed_papers = 0

        # ⭐ NEW: Markdown 目录选择
        self.selected_markdown_dir = None  # 用户选择的 Markdown 目录

        # ⭐ NEW: 分析目标选择
        self.analysis_target = "all"  # 默认分析 all/

        # ⭐ NEW: API 选择（智谱 or DeepSeek）
        self.api_type = tk.StringVar(value="glm")  # 默认使用智谱 GLM

        # 协调器
        self.coordinator = None

        # 构建界面
        self._build_ui()

        # 初始化时加载文献列表
        self._refresh_paper_list()

    def _build_ui(self):
        """构建界面（带滚动功能）"""
        # 创建 Canvas 和 Scrollbar
        canvas = tk.Canvas(self.frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)

        # 可滚动的内部框架
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # 创建窗口到 Canvas 的链接
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 鼠标滚轮滚动
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # 绑定滚轮事件（Windows 和 Linux）
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # 绑定滚轮事件（MacOS）
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # 按键滚动
        def _on_keydown(event):
            if event.keysym == "Down":
                canvas.yview_scroll(1, "units")
            elif event.keysym == "Up":
                canvas.yview_scroll(-1, "units")

        # 主框架（放在 scrollable_frame 里）
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 打包 Canvas 和 Scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 保存引用以便后续使用
        self.canvas = canvas
        self.scrollable_frame = scrollable_frame

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="🧠 AI 深度分析（双层并发 + GLM-4.7）",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))

        # 进度框架
        progress_frame = ttk.LabelFrame(main_frame, text="分析进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        # 总体进度条
        ttk.Label(progress_frame, text="总体进度:").pack(anchor=tk.W)
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate', length=800)
        self.overall_progress.pack(fill=tk.X, pady=(5, 10))

        # 进度详情标签
        self.progress_detail_label = ttk.Label(progress_frame, text="准备就绪")
        self.progress_detail_label.pack(anchor=tk.W)

        # 当前论文标签
        self.current_paper_label = ttk.Label(progress_frame, text="当前论文: -")
        self.current_paper_label.pack(anchor=tk.W, pady=(5, 0))

        # 分析器状态框架
        status_frame = ttk.LabelFrame(main_frame, text="分析器状态（双层并发）", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建5个分析器的状态标签
        self.analyzer_labels = {}
        analyzers = [
            ("innovation", "创新点分析"),
            ("motivation", "研究动机"),
            ("roadmap", "技术路线"),
            ("mechanism", "机理解析"),
            ("impact", "影响评估")
        ]

        for i, (analyzer, name) in enumerate(analyzers, 1):
            analyzer_frame = ttk.Frame(status_frame)
            analyzer_frame.pack(fill=tk.X, pady=2)

            ttk.Label(analyzer_frame, text=f"{i}. {name}:", width=15).pack(side=tk.LEFT)

            status_label = ttk.Label(analyzer_frame, text="⏸️ 等待中", width=15)
            status_label.pack(side=tk.LEFT)

            progress_bar = ttk.Progressbar(analyzer_frame, mode='determinate', length=400)
            progress_bar.pack(side=tk.LEFT, padx=5)

            self.analyzer_labels[analyzer] = {
                "status": status_label,
                "progress": progress_bar
            }

        # 设置框架
        settings_frame = ttk.LabelFrame(main_frame, text="路径与并发设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # ⭐ NEW: Markdown 目录选择
        ttk.Label(settings_frame, text="Markdown 文献目录:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # 目录选择框架
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        # 显示当前选择的目录
        self.markdown_dir_label = ttk.Label(dir_frame, text="未选择", relief=tk.SUNKEN, anchor=tk.W)
        self.markdown_dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 选择目录按钮
        ttk.Button(dir_frame, text="📁 浏览...", command=self._select_markdown_dir).pack(side=tk.LEFT)

        # 自动检测按钮
        ttk.Button(dir_frame, text="🔍 自动检测", command=self._auto_detect_markdown_dir).pack(side=tk.LEFT, padx=(5, 0))

        # ⭐ NEW: 分析目标选择（all/ 或 categories/）
        ttk.Label(settings_frame, text="分析目标:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(5, 0))

        # 目标选择框架
        target_frame = ttk.Frame(settings_frame)
        target_frame.pack(fill=tk.X, pady=(0, 10))

        # 显示当前选择的目标
        self.target_label = ttk.Label(target_frame, text="all (全部文献)", relief=tk.SUNKEN, anchor=tk.W)
        self.target_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 选择目标按钮
        ttk.Button(target_frame, text="🎯 选择目标", command=self._select_analysis_target).pack(side=tk.LEFT)

        # 目标说明
        target_help = ttk.Label(settings_frame, text="提示：分析分类时会自动从 all/ 复制已有结果，秒级完成！", font=("Arial", 8), foreground="gray")
        target_help.pack(anchor=tk.W, pady=(0, 10))

        # ⭐ NEW: 分析状态显示
        ttk.Label(settings_frame, text="分析状态:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(5, 0))

        # 状态信息框架
        status_info_frame = ttk.Frame(settings_frame)
        status_info_frame.pack(fill=tk.X, pady=(0, 10))

        self.total_papers_label = ttk.Label(status_info_frame, text="总论文数: 0")
        self.total_papers_label.pack(anchor=tk.W)

        self.analyzed_papers_label = ttk.Label(status_info_frame, text="已分析: 0")
        self.analyzed_papers_label.pack(anchor=tk.W)

        self.pending_papers_label = ttk.Label(status_info_frame, text="待分析: 0")
        self.pending_papers_label.pack(anchor=tk.W)

        # 刷新状态按钮
        ttk.Button(settings_frame, text="🔄 刷新状态", command=self._refresh_analysis_status).pack(anchor=tk.W, pady=(5, 0))

        # ⭐ NEW: API 选择（智谱 or DeepSeek）
        api_frame = ttk.LabelFrame(main_frame, text="API 模型选择", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(api_frame, text="选择 AI 模型:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # API 单选按钮框架
        api_radio_frame = ttk.Frame(api_frame)
        api_radio_frame.pack(fill=tk.X)

        # 智谱 GLM 单选按钮
        glm_radio = ttk.Radiobutton(
            api_radio_frame,
            text="🧠 智谱 GLM-4.7（Coding 端点，成本低）",
            variable=self.api_type,
            value="glm",
            command=self._on_api_type_changed
        )
        glm_radio.pack(side=tk.LEFT, padx=(0, 20))

        # DeepSeek 单选按钮
        deepseek_radio = ttk.Radiobutton(
            api_radio_frame,
            text="🔮 DeepSeek-V3（推理能力强）",
            variable=self.api_type,
            value="deepseek",
            command=self._on_api_type_changed
        )
        deepseek_radio.pack(side=tk.LEFT)

        # API 说明
        api_help = ttk.Label(api_frame, text="提示：智谱成本低速度快，DeepSeek推理能力强但成本较高", font=("Arial", 8), foreground="gray")
        api_help.pack(anchor=tk.W, pady=(5, 0))

        # 外层并发（论文数）- 使用滑块
        ttk.Label(settings_frame, text="外层并发（同时处理的论文数）:").pack(anchor=tk.W)
        self.concurrent_papers_var = tk.IntVar(value=10)
        papers_scale = ttk.Scale(settings_frame, from_=1, to=20, variable=self.concurrent_papers_var, orient=tk.HORIZONTAL)
        papers_scale.pack(fill=tk.X, pady=(0, 5))
        self.papers_value_label = ttk.Label(settings_frame, text="当前值: 10")
        self.papers_value_label.pack(anchor=tk.W)
        papers_scale.configure(command=lambda v: self.papers_value_label.config(text=f"当前值: {int(float(v))}"))

        # 内层并发（分析器数）- 使用滑块
        ttk.Label(settings_frame, text="内层并发（每篇论文的分析器数）:").pack(anchor=tk.W, pady=(10, 0))
        self.concurrent_analyzers_var = tk.IntVar(value=5)
        analyzers_scale = ttk.Scale(settings_frame, from_=1, to=5, variable=self.concurrent_analyzers_var, orient=tk.HORIZONTAL)
        analyzers_scale.pack(fill=tk.X, pady=(0, 5))
        self.analyzers_value_label = ttk.Label(settings_frame, text="当前值: 5（固定为 5 个分析器）")
        self.analyzers_value_label.pack(anchor=tk.W)
        analyzers_scale.configure(command=lambda v: self.analyzers_value_label.config(text=f"当前值: {int(float(v))}（固定为 5 个分析器）"))

        # 控制按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        # 主控制按钮
        control_frame = ttk.Frame(btn_frame)
        control_frame.pack(side=tk.LEFT)

        self.start_button = ttk.Button(control_frame, text="▶️ 开始分析", command=self.start_analysis)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(control_frame, text="⏸️ 暂停", command=self.pause_analysis, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="⏹️ 停止", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 系统控制按钮
        sys_frame = ttk.Frame(btn_frame)
        sys_frame.pack(side=tk.RIGHT)

        ttk.Button(sys_frame, text="⬇️ 滚动到日志", command=self.scroll_to_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(sys_frame, text="🧹 清除缓存", command=self.clear_cache).pack(side=tk.LEFT, padx=5)
        ttk.Button(sys_frame, text="🔄 刷新日志", command=self.refresh_log).pack(side=tk.LEFT, padx=5)

        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _refresh_paper_list(self):
        """刷新文献列表（从选择的 Markdown 目录）"""
        # 如果用户已选择目录，使用选择的目录
        if self.selected_markdown_dir and self.selected_markdown_dir.exists():
            markdown_dir = self.selected_markdown_dir
        # 否则尝试使用默认目录
        else:
            markdown_dir = self.project_dir / "markdown" / "all"
            if not markdown_dir.exists():
                self.log(f"⚠️ 请先选择 Markdown 目录")
                self.markdown_dir_label.config(text="请选择目录...")
                return

            # 设置默认目录
            self.selected_markdown_dir = markdown_dir
            self.markdown_dir_label.config(text=f"markdown/all (默认)")

        # 统计论文数量
        paper_count = len([d for d in markdown_dir.iterdir() if d.is_dir()])
        self.log(f"✓ 目录: {markdown_dir.parent.name}/{markdown_dir.name}")
        self.log(f"✓ 发现 {paper_count} 篇论文")

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.frame.update_idletasks()

    def update_progress(self, message: str, progress: float = None):
        """更新进度"""
        if progress is not None:
            self.overall_progress['value'] = progress
            self.progress_detail_label.config(text=f"总体进度: {progress:.1f}%")

        if message:
            self.log(message)

    def update_analyzer_status(self, analyzer: str, status: str, progress: float = None):
        """更新分析器状态"""
        if analyzer in self.analyzer_labels:
            label = self.analyzer_labels[analyzer]["status"]
            bar = self.analyzer_labels[analyzer]["progress"]

            # 更新状态文本和图标
            status_icons = {
                "running": "🔄 运行中",
                "completed": "✅ 已完成",
                "failed": "❌ 失败",
                "waiting": "⏸️ 等待中"
            }
            label.config(text=status_icons.get(status, status))

            # 更新进度条
            if progress is not None:
                bar['value'] = progress

    def _on_api_type_changed(self):
        """API 类型切换回调"""
        api_type = self.api_type.get()
        if api_type == "glm":
            self.log("🔄 切换到智谱 GLM-4.7（Coding 端点，成本低）")
        elif api_type == "deepseek":
            self.log("🔄 切换到 DeepSeek-V3（推理能力强）")

    def start_analysis(self):
        """开始分析"""
        if self.is_running:
            return

        self.is_running = True
        self.is_paused = False
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)

        self.log("=" * 60)
        self.log("开始分析...")

        # 根据选择的API类型显示不同的消息
        api_type = self.api_type.get()
        if api_type == "glm":
            self.log("使用模型: 智谱 GLM-4.7（Coding 端点，成本低）")
        elif api_type == "deepseek":
            self.log("使用模型: DeepSeek-V3（推理能力强）")

        self.log("=" * 60)

        # 在后台线程运行
        thread = threading.Thread(target=self._run_analysis)
        thread.daemon = True
        thread.start()

    def _run_analysis(self):
        """运行分析（后台线程）"""
        try:
            # 检查是否已选择目录
            if not self.selected_markdown_dir or not self.selected_markdown_dir.exists():
                self.log("❌ 请先选择 Markdown 目录")
                self.start_button.config(state=tk.NORMAL)
                self.pause_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.DISABLED)
                self.is_running = False
                return

            # 获取配置
            max_papers = None  # 分析所有论文
            skip_completed = True
            concurrent_papers = int(self.concurrent_papers_var.get())
            concurrent_analyzers = int(self.concurrent_analyzers_var.get())

            # ⭐ 使用用户选择的 Markdown 目录
            markdown_dir = self.selected_markdown_dir

            self.log(f"使用目录: {markdown_dir}")
            self.log(f"分析目标: {self.analysis_target}")

            # ⭐ 修复：确定正确的 output_subdir
            if self.analysis_target == "all":
                output_subdir = "all"
            else:
                output_subdir = f"categories/{self.analysis_target}"

            # ⭐ NEW: 获取用户选择的 API 类型
            api_type = self.api_type.get()

            # 创建协调器（传递 api_type 参数）
            self.coordinator = AgentAnalysisCoordinatorV5(
                markdown_root=markdown_dir,
                output_subdir=output_subdir,
                max_concurrent_papers=concurrent_papers,  # 外层并发
                max_concurrent_analyzers=concurrent_analyzers,  # 内层并发
                api_type=api_type,  # ⭐ NEW: 传递 API 类型
            )

            # 设置进度回调
            self.coordinator.set_progress_callback(self.update_progress)

            # 执行分析
            stats = self.coordinator.batch_analyze(
                max_papers=max_papers,
                skip_completed=skip_completed,
            )

            # 分析完成
            self.log("=" * 60)
            self.log(f"分析完成！总计: {stats.get('total', 0)}")
            self.log(f"成功: {stats.get('completed', 0)}")
            self.log(f"失败: {stats.get('failed', 0)}")
            self.log("=" * 60)

            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
            self.is_running = False

        except Exception as e:
            self.log(f"❌ 分析失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def pause_analysis(self):
        """暂停/继续分析"""
        if not self.is_running:
            return

        self.is_paused = not self.is_paused

        if self.is_paused:
            self.pause_button.config(text="▶️ 继续")
            self.log("分析已暂停")
        else:
            self.pause_button.config(text="⏸️ 暂停")
            self.log("分析继续...")

    def stop_analysis(self):
        """停止分析"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

        self.log("=" * 60)
        self.log("分析已停止")
        self.log("=" * 60)

    def _select_markdown_dir(self):
        """手动选择 Markdown 目录"""
        # 默认路径：项目的 markdown/all 目录
        default_dir = self.project_dir / "markdown" / "all"
        if not default_dir.exists():
            default_dir = self.project_dir / "markdown"
        if not default_dir.exists():
            default_dir = self.project_dir

        # 打开目录选择对话框
        selected_dir = filedialog.askdirectory(
            title="选择 Markdown 文献目录",
            initialdir=str(default_dir)
        )

        if selected_dir:
            self.selected_markdown_dir = Path(selected_dir)
            self.markdown_dir_label.config(text=str(self.selected_markdown_dir))
            self.log(f"✓ 已选择目录: {self.selected_markdown_dir}")

            # 刷新文献列表
            self._refresh_paper_list()

    def _auto_detect_markdown_dir(self):
        """自动检测可用的 Markdown 目录并显示选择对话框"""
        # 搜索可能的 Markdown 目录位置
        possible_locations = []

        # 1. 项目的 markdown/all 目录
        markdown_all = self.project_dir / "markdown" / "all"
        if markdown_all.exists():
            paper_count = len([d for d in markdown_all.iterdir() if d.is_dir()])
            possible_locations.append({
                "path": markdown_all,
                "name": f"markdown/all (默认输出，{paper_count} 篇)",
                "count": paper_count
            })

        # 2. 项目的 markdown/categories 下的各个分类目录
        categories_dir = self.project_dir / "markdown" / "categories"
        if categories_dir.exists():
            for cat_dir in categories_dir.iterdir():
                if cat_dir.is_dir():
                    paper_count = len([d for d in cat_dir.iterdir() if d.is_dir()])
                    possible_locations.append({
                        "path": cat_dir,
                        "name": f"markdown/categories/{cat_dir.name} ({paper_count} 篇)",
                        "count": paper_count
                    })

        # 3. 项目的 markdown 目录本身
        markdown_root = self.project_dir / "markdown"
        if markdown_root.exists() and markdown_root != markdown_all:
            paper_count = len([d for d in markdown_root.iterdir() if d.is_dir()])
            possible_locations.append({
                "path": markdown_root,
                "name": f"markdown/ (根目录，{paper_count} 篇)",
                "count": paper_count
            })

        # 如果没有找到任何目录
        if not possible_locations:
            self.log("⚠️ 未找到任何 Markdown 目录，请手动选择")
            messagebox.showwarning("未找到目录", "未找到任何 Markdown 目录。\n\n请使用「浏览」按钮手动选择目录。")
            return

        # 创建选择对话框
        dialog = tk.Toplevel(self.frame)
        dialog.title("自动检测到 Markdown 目录")
        dialog.geometry("600x400")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # 说明
        ttk.Label(
            frame,
            text="检测到以下包含 Markdown 论文的目录：",
            font=("", 10, "bold")
        ).pack(pady=10)

        # 目录选择列表
        list_frame = ttk.LabelFrame(frame, text="请选择要分析的目录", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        selected_dir = tk.StringVar(value=str(possible_locations[0]["path"]))

        for i, location in enumerate(possible_locations):
            rb = ttk.Radiobutton(
                list_frame,
                text=f"📁 {location['name']}",
                variable=selected_dir,
                value=str(location["path"])
            )
            rb.pack(anchor=tk.W, pady=5)

        # 统计信息
        total_papers = sum(loc["count"] for loc in possible_locations)
        stats_label = ttk.Label(
            frame,
            text=f"共检测到 {len(possible_locations)} 个目录，总计 {total_papers} 篇论文",
            font=("", 9),
            foreground="gray"
        )
        stats_label.pack(pady=10)

        def confirm_selection():
            """确认选择"""
            self.selected_markdown_dir = Path(selected_dir.get())
            self.markdown_dir_label.config(text=f"{self.selected_markdown_dir.parent.name}/{self.selected_markdown_dir.name}")
            self.log(f"✓ 已选择目录: {self.selected_markdown_dir}")
            dialog.destroy()

            # 刷新文献列表
            self._refresh_paper_list()

        ttk.Button(frame, text="确定", command=confirm_selection).pack(pady=10)

    def _select_analysis_target(self):
        """选择分析目标（all/ 或分类/）"""
        # 获取可用的分类列表
        categories_dir = self.project_dir / "markdown" / "categories"
        available_targets = ["all"]  # 默认选项

        if categories_dir.exists():
            for item in categories_dir.iterdir():
                if item.is_dir():
                    available_targets.append(item.name)

        # 创建选择对话框
        dialog = tk.Toplevel(self.frame)
        dialog.title("选择分析目标")
        dialog.geometry("500x400")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # 说明
        ttk.Label(
            frame,
            text="请选择分析目标：",
            font=("", 10, "bold")
        ).pack(pady=(0, 10))

        ttk.Label(
            frame,
            text="• all (全部文献) - 分析所有文献，结果保存到 agent_results/all/\n• 分类目录 - 分析指定分类，结果保存到 agent_results/categories/{分类}/",
            font=("", 9),
            foreground="gray"
        ).pack(pady=(0, 10))

        # 目标选择列表
        target_var = tk.StringVar(value=self.analysis_target)

        for target in available_targets:
            display_name = "📚 all (全部文献)" if target == "all" else f"📁 {target}"
            rb = ttk.Radiobutton(
                frame,
                text=display_name,
                variable=target_var,
                value=target
            )
            rb.pack(anchor=tk.W, pady=5)

        def confirm():
            """确认选择"""
            selected = target_var.get()
            self.analysis_target = selected

            # 更新显示
            display_name = "📚 all (全部文献)" if selected == "all" else f"📁 {selected}"
            self.target_label.config(text=display_name)

            self.log(f"✓ 已选择分析目标: {selected}")
            dialog.destroy()

            # 刷新状态
            self._refresh_analysis_status()

        ttk.Button(frame, text="确定", command=confirm).pack(pady=10)

    def _refresh_analysis_status(self):
        """刷新分析状态"""
        # 确定索引文件路径
        if self.analysis_target == "all":
            index_file = self.project_dir / "data" / "agent_results" / "all" / "analysis_index.json"
        else:
            # ⭐ 修复路径：categories/{分类名}
            index_file = self.project_dir / "data" / "agent_results" / "categories" / self.analysis_target / "analysis_index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                metadata = index.get("metadata", {})
                total = metadata.get('total_papers', 0)
                analyzed = metadata.get('analyzed_papers', 0)
                partial = metadata.get('partial_papers', 0)
                pending = total - analyzed - partial

                self.total_papers_label.config(text=f"总论文数: {total}")
                self.analyzed_papers_label.config(text=f"已分析: {analyzed} ({analyzed/total*100:.1f}%)" if total > 0 else "已分析: 0")
                self.pending_papers_label.config(text=f"待分析: {pending}")

                # ⭐ 区分"文件不存在"和"无数据"
                if total == 0:
                    self.log(f"📝 等待开始分析（状态文件已创建）")
                else:
                    self.log(f"✓ 状态已刷新: {analyzed}/{total} 已完成")
            except Exception as e:
                self.log(f"⚠️ 读取状态失败: {e}")
        else:
            self.total_papers_label.config(text="总论文数: 0")
            self.analyzed_papers_label.config(text="已分析: 0")
            self.pending_papers_label.config(text="待分析: 0")
            self.log(f"📝 等待开始分析（状态文件将被自动创建）")

    def clear_cache(self):
        """清除 Python 缓存并终止进程"""
        try:
            import subprocess
            import sys

            self.log("🧹 开始清除缓存...")

            # 终止 Python 进程
            self.log("  [1/2] 终止 Python 进程...")
            result = subprocess.run(
                ["tasklist", "|", "findstr", "/i", "python"],
                capture_output=True,
                text=True,
                shell=True
            )

            if "python.exe" in result.stdout.lower():
                # 提取 PID 并终止
                lines = result.stdout.split('\n')
                pids = []
                for line in lines:
                    if 'python.exe' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = parts[1].strip()
                            if pid.isdigit():
                                pids.append(pid)

                for pid in pids[:3]:  # 最多终止 3 个进程
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid],
                                     capture_output=True, shell=True)
                        self.log(f"    - 已终止进程 PID {pid}")
                    except:
                        pass
            else:
                self.log("    - 没有运行中的 Python 进程")

            # 清除缓存文件
            self.log("  [2/2] 删除缓存文件...")
            cache_deleted = 0

            for root, dirs, files in os.walk(self.project_dir):
                # 删除 __pycache__ 目录
                if "__pycache__" in dirs:
                    cache_path = Path(root) / "__pycache__"
                    try:
                        import shutil
                        shutil.rmtree(cache_path)
                        cache_deleted += 1
                        self.log(f"    - 已删除: {cache_path.relative_to(self.project_dir)}")
                    except:
                        pass

                # 删除 .pyc 文件
                for file in files:
                    if file.endswith('.pyc') or file.endswith('.pyo'):
                        pyc_path = Path(root) / file
                        try:
                            pyc_path.unlink()
                            cache_deleted += 1
                        except:
                            pass

            self.log(f"✓ 清除完成！删除了 {cache_deleted} 个缓存项")
            messagebox.showinfo("清除完成", f"已清除缓存并终止进程\n\n删除了 {cache_deleted} 个缓存文件")

        except Exception as e:
            self.log(f"❌ 清除失败: {e}")
            messagebox.showerror("清除失败", f"清除缓存时出错:\n{e}")

    def refresh_log(self):
        """刷新日志显示"""
        self.log_text.config(state='normal')
        self.log("🔄 日志已刷新")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def scroll_to_log(self):
        """滚动到日志区域"""
        try:
            # 更新 canvas 的 scrollregion
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # 滚动到底部
            self.canvas.yview_moveto(1.0)

            # 聚焦到日志文本框
            self.log_text.config(state='normal')
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')

            self.log("⬇️ 已滚动到日志区域")
        except Exception as e:
            self.log(f"⚠️ 滚动失败: {e}")
