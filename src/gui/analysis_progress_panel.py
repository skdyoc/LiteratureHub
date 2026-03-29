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
分析进度面板

显示文献分析的进度和状态。
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime


class AnalysisProgressPanel(ttk.Frame):
    """分析进度面板

    显示文献分析的实时进度和状态。

    使用示例：
    ```python
    panel = AnalysisProgressPanel(parent)
    panel.pack(fill=tk.BOTH, expand=True)

    # 更新进度
    panel.update_progress("analyzing", 50, 100, "正在分析第 50 篇...")

    # 设置完成回调
    panel.set_completion_callback(on_analysis_complete)
    ```
    """

    def __init__(self, parent):
        """初始化分析进度面板

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        self.completion_callback: Optional[Callable] = None
        self.analysis_stats: Dict[str, Any] = {}

        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(title_frame, text="分析进度", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        # 状态标签
        self.status_label = ttk.Label(title_frame, text="就绪", foreground="green")
        self.status_label.pack(side=tk.RIGHT)

        # 总体进度
        progress_frame = ttk.LabelFrame(self, text="总体进度", padding=10)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)

        # 进度标签
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill=tk.X)

        self.progress_percent_label = ttk.Label(progress_info_frame, text="0%")
        self.progress_percent_label.pack(side=tk.LEFT)

        self.progress_detail_label = ttk.Label(progress_info_frame, text="0 / 0")
        self.progress_detail_label.pack(side=tk.RIGHT)

        # 消息标签
        self.message_label = ttk.Label(progress_frame, text="等待开始...")
        self.message_label.pack(fill=tk.X, pady=5)

        # 分阶段进度
        stage_frame = ttk.LabelFrame(self, text="分阶段进度", padding=10)
        stage_frame.pack(fill=tk.X, padx=5, pady=5)

        # 创建阶段进度条
        self.stage_progress = {}
        stages = [
            ("search", "文献搜索"),
            ("download", "PDF 下载"),
            ("parse", "文档解析"),
            ("analyze", "AI 分析"),
            ("generate", "PPT 生成")
        ]

        for stage_id, stage_name in stages:
            stage_row = ttk.Frame(stage_frame)
            stage_row.pack(fill=tk.X, pady=2)

            ttk.Label(stage_row, text=f"{stage_name}:", width=12).pack(side=tk.LEFT)

            progress = ttk.Progressbar(stage_row, mode='determinate', length=200)
            progress.pack(side=tk.LEFT, padx=5)
            progress['value'] = 0

            label = ttk.Label(stage_row, text="0%", width=6)
            label.pack(side=tk.LEFT)

            self.stage_progress[stage_id] = {
                "progress": progress,
                "label": label
            }

        # 统计信息
        stats_frame = ttk.LabelFrame(self, text="统计信息", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        # 创建统计标签
        self.stats_labels = {}
        stats = [
            ("total", "总文献数"),
            ("analyzed", "已分析"),
            ("pending", "待分析"),
            ("failed", "失败")
        ]

        for i, (stat_id, stat_name) in enumerate(stats):
            row = i // 2
            col = i % 2

            frame = ttk.Frame(stats_frame)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")

            ttk.Label(frame, text=f"{stat_name}:").pack(side=tk.LEFT)
            label = ttk.Label(frame, text="0", font=("Arial", 12, "bold"))
            label.pack(side=tk.LEFT, padx=5)

            self.stats_labels[stat_id] = label

        # 控制按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="开始分析", command=self._start_analysis).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="暂停", command=self._pause_analysis).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="继续", command=self._resume_analysis).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="取消", command=self._cancel_analysis).pack(side=tk.LEFT, padx=2)

        # 日志区域
        log_frame = ttk.LabelFrame(self, text="实时日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 日志文本框
        self.log_text = tk.Text(log_frame, height=6, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_progress(
        self,
        stage: str,
        current: int,
        total: int,
        message: str = None
    ):
        """更新进度

        Args:
            stage: 阶段 ID
            current: 当前进度
            total: 总数
            message: 消息（可选）
        """
        # 更新总体进度
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar['value'] = percentage
        self.progress_percent_label.config(text=f"{percentage}%")
        self.progress_detail_label.config(text=f"{current} / {total}")

        if message:
            self.message_label.config(text=message)

        # 更新阶段进度
        if stage in self.stage_progress:
            self.stage_progress[stage]["progress"]['value'] = percentage
            self.stage_progress[stage]["label"].config(text=f"{percentage}%")

        # 添加日志
        if message:
            self.add_log(f"[{stage}] {message}")

    def update_stats(self, stats: Dict[str, int]):
        """更新统计信息

        Args:
            stats: 统计信息字典
        """
        for stat_id, value in stats.items():
            if stat_id in self.stats_labels:
                self.stats_labels[stat_id].config(text=str(value))

        self.analysis_stats.update(stats)

    def set_status(self, status: str, color: str = "black"):
        """设置状态

        Args:
            status: 状态文本
            color: 颜色
        """
        self.status_label.config(text=status, foreground=color)

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志消息

        Args:
            message: 日志消息
            level: 日志级别
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # 根据级别设置颜色
        if level == "ERROR":
            self.log_text.tag_add("error", f"{tk.END}-1l linestart", f"{tk.END}-1l lineend")
            self.log_text.tag_config("error", foreground="red")
        elif level == "WARNING":
            self.log_text.tag_add("warning", f"{tk.END}-1l linestart", f"{tk.END}-1l lineend")
            self.log_text.tag_config("warning", foreground="orange")

    def set_completion_callback(self, callback: Callable):
        """设置完成回调

        Args:
            callback: 回调函数
        """
        self.completion_callback = callback

    def _start_analysis(self):
        """开始分析"""
        self.set_status("运行中", "blue")
        self.add_log("分析已开始", "INFO")

        # 调用分析管理器
        try:
            from src.analysis.manager import AnalysisManager
            if hasattr(self, 'analysis_manager'):
                self.analysis_manager.start_analysis()
        except ImportError:
            self.add_log("分析管理器未加载", "WARNING")

        self.update_progress("analyze", 0, 100, "准备开始分析...")

    def _pause_analysis(self):
        """暂停分析"""
        self.set_status("已暂停", "orange")
        self.add_log("分析已暂停", "WARNING")

        # 调用分析管理器暂停
        try:
            if hasattr(self, 'analysis_manager'):
                self.analysis_manager.pause_analysis()
        except Exception as e:
            self.add_log(f"暂停失败: {e}", "ERROR")

    def _resume_analysis(self):
        """继续分析"""
        self.set_status("运行中", "blue")
        self.add_log("分析已继续", "INFO")

        # 调用分析管理器继续
        try:
            if hasattr(self, 'analysis_manager'):
                self.analysis_manager.resume_analysis()
        except Exception as e:
            self.add_log(f"继续失败: {e}", "ERROR")

    def _cancel_analysis(self):
        """取消分析"""
        from tkinter import messagebox

        if messagebox.askyesno("确认", "确定要取消分析吗？"):
            self.set_status("已取消", "red")
            self.add_log("分析已取消", "ERROR")

            # 调用分析管理器取消
            try:
                if hasattr(self, 'analysis_manager'):
                    self.analysis_manager.cancel_analysis()
            except Exception as e:
                self.add_log(f"取消失败: {e}", "ERROR")

    def reset(self):
        """重置面板"""
        self.progress_bar['value'] = 0
        self.progress_percent_label.config(text="0%")
        self.progress_detail_label.config(text="0 / 0")
        self.message_label.config(text="等待开始...")
        self.set_status("就绪", "green")

        # 重置阶段进度
        for stage_id in self.stage_progress:
            self.stage_progress[stage_id]["progress"]['value'] = 0
            self.stage_progress[stage_id]["label"].config(text="0%")

        # 重置统计
        for stat_id in self.stats_labels:
            self.stats_labels[stat_id].config(text="0")

        # 清空日志
        self.log_text.delete(1.0, tk.END)

        self.analysis_stats.clear()
