"""
Agent 分析 GUI 监控界面
Agent Analysis GUI Monitor

功能：
1. 实时显示分析进度
2. 显示当前分析论文
3. 显示各分析器状态
4. 实时日志输出
5. 支持暂停/继续
6. ✨ 集成评分排名功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

from scripts.agent_parallel_coordinator_v2_standalone import StandaloneV2Coordinator


class AnalysisGUI:
    """分析 GUI 界面"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent 并行分析系统")
        self.root.geometry("900x700")

        # 状态变量
        self.is_running = False
        self.is_paused = False
        self.current_paper = ""
        self.total_papers = 0
        self.completed_papers = 0

        # 创建界面
        self._create_widgets()

        # 协调器
        self.coordinator = None

    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="🚀 Agent 并行论文分析系统 V2 (双层并发)",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        # 进度框架
        progress_frame = ttk.LabelFrame(main_frame, text="分析进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        # 总体进度条
        ttk.Label(progress_frame, text="总体进度:").pack(anchor=tk.W)
        self.overall_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=800
        )
        self.overall_progress.pack(fill=tk.X, pady=(5, 10))

        # 进度标签（显示详细信息）
        self.progress_detail_label = ttk.Label(progress_frame, text="准备就绪", font=("Arial", 10))
        self.progress_detail_label.pack(anchor=tk.W)

        self.progress_label = ttk.Label(progress_frame, text="准备就绪")
        self.progress_label.pack(anchor=tk.W)

        # 当前论文标签
        self.current_paper_label = ttk.Label(
            progress_frame,
            text="当前论文: -",
            font=("Arial", 10),
            wraplength=800
        )
        self.current_paper_label.pack(anchor=tk.W, pady=(5, 0))

        # 分析器状态框架
        status_frame = ttk.LabelFrame(main_frame, text="分析器状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建5个分析器的状态标签
        self.analyzer_labels = {}
        analyzers = ["innovation", "motivation", "roadmap", "mechanism", "impact"]
        analyzer_names = {
            "innovation": "创新点分析",
            "motivation": "研究动机分析",
            "roadmap": "技术路线分析",
            "mechanism": "机理解析",
            "impact": "影响评估"
        }

        for i, analyzer in enumerate(analyzers):
            frame = ttk.Frame(status_frame)
            frame.pack(fill=tk.X, pady=2)

            ttk.Label(frame, text=f"{analyzer_names[analyzer]}:", width=20).pack(side=tk.LEFT)

            status_label = ttk.Label(frame, text="⏸️ 等待中", width=15)
            status_label.pack(side=tk.LEFT, padx=5)

            progress_bar = ttk.Progressbar(frame, mode='determinate', length=200)
            progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.analyzer_labels[analyzer] = {
                "status": status_label,
                "progress": progress_bar
            }

        # 日志框架
        log_frame = ttk.LabelFrame(main_frame, text="实时日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 控制按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.start_button = ttk.Button(
            button_frame,
            text="▶️ 开始分析",
            command=self.start_analysis
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            button_frame,
            text="⏸️ 暂停",
            command=self.pause_analysis,
            state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="⏹️ 停止",
            command=self.stop_analysis,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 配置框架
        config_frame = ttk.Frame(button_frame)
        config_frame.pack(side=tk.RIGHT)

        ttk.Label(config_frame, text="论文数量:").pack(side=tk.LEFT)
        self.max_papers_var = tk.StringVar(value="1")
        max_papers_entry = ttk.Entry(config_frame, textvariable=self.max_papers_var, width=10)
        max_papers_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(config_frame, text="外层并发:").pack(side=tk.LEFT, padx=(10, 0))
        self.concurrent_papers_var = tk.StringVar(value="20")  # ← 默认20个外层并发
        concurrent_papers_entry = ttk.Entry(config_frame, textvariable=self.concurrent_papers_var, width=10)
        concurrent_papers_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(config_frame, text="内层并发:").pack(side=tk.LEFT, padx=(10, 0))
        self.concurrent_analyzers_var = tk.StringVar(value="5")
        concurrent_analyzers_entry = ttk.Entry(config_frame, textvariable=self.concurrent_analyzers_var, width=10)
        concurrent_analyzers_entry.pack(side=tk.LEFT, padx=5)

        self.skip_completed_var = tk.BooleanVar(value=True)
        skip_check = ttk.Checkbutton(
            config_frame,
            text="跳过已完成",
            variable=self.skip_completed_var
        )
        skip_check.pack(side=tk.LEFT, padx=5)

    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, message: str, progress: float = None):
        """更新进度"""
        if progress is not None:
            self.overall_progress['value'] = progress
            self.progress_label.config(text=f"总体进度: {progress:.1f}%")

        if message:
            # 提取当前论文信息
            if "正在分析:" in message:
                self.current_paper = message.replace("正在分析:", "").strip()
                self.current_paper_label.config(text=f"当前论文: {self.current_paper}")
            elif "分析进度:" in message:
                # ✨ 解析格式: "分析进度: 1/100 [#1 (98.5分)]"
                parts = message.split("/")
                if len(parts) >= 2:
                    # 提取当前数字
                    current_part = parts[0].split(":")[1].strip() if ":" in parts[0] else parts[0].strip()

                    # ✨ 提取排名信息 [排名#xxx (分数)]
                    rank_match = None
                    if "[" in current_part:
                        rank_start = current_part.rfind("[")
                        rank_end = current_part.rfind("]")
                        if rank_start < rank_end:
                            rank_match = current_part[rank_start:rank_end+1]
                            current_part = current_part[:rank_start].strip()

                    # 提取总数（去除可能的排名信息）
                    total_part = parts[1].strip()
                    if "[" in total_part:
                        total_part = total_part[:total_part.rfind("[")].strip()

                    self.completed_papers = int(current_part)
                    self.total_papers = int(total_part) if total_part else self.total_papers

                    # ✨ 显示详细信息（包括排名）
                    if rank_match:
                        detail_text = f"进度: {self.completed_papers}/{self.total_papers} | 排名: {rank_match}"
                        if hasattr(self, 'progress_detail_label'):
                            self.progress_detail_label.config(text=detail_text)
                        self.current_paper_label.config(text=f"当前论文: {rank_match}")
                    else:
                        if hasattr(self, 'progress_detail_label'):
                            self.progress_detail_label.config(text=f"进度: {self.completed_papers}/{self.total_papers}")
                        self.current_paper_label.config(text=f"当前论文: {self.completed_papers}/{self.total_papers}")

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
        self.log("=" * 60)

        # 在后台线程运行
        thread = threading.Thread(target=self._run_analysis)
        thread.daemon = True
        thread.start()

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

    def _run_analysis(self):
        """运行分析（后台线程）"""
        try:
            # 获取配置
            max_papers = int(self.max_papers_var.get()) if self.max_papers_var.get() else None
            skip_completed = self.skip_completed_var.get()
            concurrent_papers = int(self.concurrent_papers_var.get())
            concurrent_analyzers = int(self.concurrent_analyzers_var.get())

            # 创建V2协调器（双层并发）
            self.coordinator = StandaloneV2Coordinator(
                database_path=r"D:\xfs\phd\github项目\Wind-Aero-Literature-Analysis-System\data\database.db",
                output_dir="data/agent_results",
                max_concurrent_papers=concurrent_papers,  # 外层并发：从GUI读取
                max_concurrent_analyzers=concurrent_analyzers,  # 内层并发：从GUI读取
            )

            # 定义进度回调
            def progress_callback(message, progress):
                if not self.is_running:
                    return

                # 更新GUI（必须在主线程）
                self.root.after(0, lambda: self.update_progress(message, progress))

            # ✨ 新增：读取评分排名数据
            ranked_file = Path("data/analysis_results/ranked_papers.json")
            ranked_papers = None

            if ranked_file.exists():
                self.log("✓ 发现评分排名文件，使用排名顺序分析")
                with open(ranked_file, 'r', encoding='utf-8') as f:
                    ranked_papers = json.load(f)
                self.log(f"✓ 加载了 {len(ranked_papers)} 篇文献的排名")

                # 显示Top5预览
                self.log("Top 5 文献预览:")
                for i, item in enumerate(ranked_papers[:5], 1):
                    score = item.get('score', 0)
                    year = item.get('year', 0)
                    journal = item.get('journal', 'Unknown')
                    title_short = item.get('title', '')[:50]
                    self.log(f"  #{i} [{score:.1f}分] {year} | {journal} | {title_short}...")
            else:
                self.log("⚠️  未找到评分排名文件，使用数据库顺序")
                self.log("   提示：运行 python scripts/score_and_rank.py 先进行评分")

            # 执行分析（传入排名数据和进度回调）
            stats = self.coordinator.batch_analyze(
                max_papers=max_papers,
                skip_completed=skip_completed,
                ranked_papers=ranked_papers,  # ✨ 传入排名数据
                progress_callback=progress_callback  # ✨ 传入进度回调
            )

            # 分析完成
            self.root.after(0, self._analysis_complete, stats)

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 错误: {e}"))
            self.root.after(0, self.stop_analysis)

    def _analysis_complete(self, stats):
        """分析完成"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

        self.log("=" * 60)
        self.log("✅ 分析完成！")
        self.log(f"总论文数: {stats['total']}")
        self.log(f"成功完成: {stats['completed']} 篇")
        self.log(f"失败: {stats['failed']} 篇")
        self.log(f"总耗时: {stats['elapsed_time']:.1f}秒")
        self.log(f"平均每篇: {stats['avg_time_per_paper']:.1f}秒")
        self.log("=" * 60)

    def run(self):
        """运行GUI"""
        self.log("系统就绪，等待开始...")
        self.root.mainloop()


def main():
    """主函数"""
    gui = AnalysisGUI()
    gui.run()


if __name__ == "__main__":
    main()
