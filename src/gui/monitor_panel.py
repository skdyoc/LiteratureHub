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
监控面板

提供实时进度监控和状态显示。
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Dict, List, Any
import time


class MonitorPanel(ttk.Frame):
    """监控面板

    显示实时进度、任务状态、日志信息。

    使用示例：
    ```python
    panel = MonitorPanel(parent)
    panel.pack(fill=tk.BOTH, expand=True)

    # 更新进度
    panel.update_progress("文献搜索", 50, 100)

    # 添加日志
    panel.add_log("开始搜索文献...")
    ```
    """

    def __init__(self, parent):
        """初始化监控面板

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        self.task_progress: Dict[str, int] = {}
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 顶部：总体进度
        overview_frame = ttk.LabelFrame(self, text="总体进度", padding=10)
        overview_frame.pack(fill=tk.X, padx=5, pady=5)

        # 进度条
        progress_frame = ttk.Frame(overview_frame)
        progress_frame.pack(fill=tk.X, pady=5)

        ttk.Label(progress_frame, text="总体完成度:").pack(side=tk.LEFT)
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        self.overall_progress.pack(side=tk.LEFT, padx=10)
        self.overall_label = ttk.Label(progress_frame, text="0%")
        self.overall_label.pack(side=tk.LEFT)

        # 统计信息
        stats_frame = ttk.Frame(overview_frame)
        stats_frame.pack(fill=tk.X, pady=5)

        self.stats_labels = {}
        for stat_name in ["总任务数", "已完成", "进行中", "失败"]:
            frame = ttk.Frame(stats_frame)
            frame.pack(side=tk.LEFT, padx=10)
            ttk.Label(frame, text=f"{stat_name}:").pack(side=tk.LEFT)
            label = ttk.Label(frame, text="0")
            label.pack(side=tk.LEFT)
            self.stats_labels[stat_name] = label

        # 中部：任务列表
        tasks_frame = ttk.LabelFrame(self, text="任务状态", padding=10)
        tasks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 任务表格
        columns = ("task_name", "status", "progress", "start_time", "end_time", "duration")
        self.task_tree = ttk.Treeview(tasks_frame, columns=columns, show="headings", height=10)

        self.task_tree.heading("task_name", text="任务名称")
        self.task_tree.heading("status", text="状态")
        self.task_tree.heading("progress", text="进度")
        self.task_tree.heading("start_time", text="开始时间")
        self.task_tree.heading("end_time", text="结束时间")
        self.task_tree.heading("duration", text="耗时")

        self.task_tree.column("task_name", width=150)
        self.task_tree.column("status", width=80)
        self.task_tree.column("progress", width=80)
        self.task_tree.column("start_time", width=120)
        self.task_tree.column("end_time", width=120)
        self.task_tree.column("duration", width=80)

        # 滚动条
        scrollbar = ttk.Scrollbar(tasks_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)

        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部：日志区域
        log_frame = ttk.LabelFrame(self, text="实时日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 日志文本框
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 日志控制按钮
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(log_toolbar, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_toolbar, text="导出日志", command=self._export_log).pack(side=tk.LEFT, padx=2)

        # 自动滚动选项
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_toolbar, text="自动滚动", variable=self.auto_scroll_var).pack(side=tk.LEFT, padx=10)

    def update_progress(self, task_name: str, current: int, total: int):
        """更新任务进度

        Args:
            task_name: 任务名称
            current: 当前进度
            total: 总数
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        self.task_progress[task_name] = percentage

        # 更新任务树
        self._update_task_in_tree(task_name, percentage)

        # 更新总体进度
        self._update_overall_progress()

    def _update_task_in_tree(self, task_name: str, progress: int):
        """更新任务树中的进度"""
        # 查找任务
        for item in self.task_tree.get_children():
            values = self.task_tree.item(item)['values']
            if values[0] == task_name:
                # 更新进度
                self.task_tree.item(item, values=(
                    values[0],
                    values[1],
                    f"{progress}%",
                    values[3],
                    values[4],
                    values[5]
                ))
                return

        # 如果任务不存在，添加新任务
        now = datetime.now().strftime("%H:%M:%S")
        self.task_tree.insert("", tk.END, values=(
            task_name,
            "进行中",
            f"{progress}%",
            now,
            "-",
            "-"
        ))

    def _update_overall_progress(self):
        """更新总体进度"""
        if not self.task_progress:
            return

        overall = sum(self.task_progress.values()) / len(self.task_progress)
        self.overall_progress['value'] = overall
        self.overall_label.config(text=f"{int(overall)}%")

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志消息

        Args:
            message: 日志消息
            level: 日志级别（INFO, WARNING, ERROR）
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, log_entry)

        # 自动滚动到底部
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)

        # 根据级别设置颜色
        if level == "ERROR":
            self.log_text.tag_add("error", f"{tk.END}-1l linestart", f"{tk.END}-1l lineend")
            self.log_text.tag_config("error", foreground="red")
        elif level == "WARNING":
            self.log_text.tag_add("warning", f"{tk.END}-1l linestart", f"{tk.END}-1l lineend")
            self.log_text.tag_config("warning", foreground="orange")

    def update_stats(self, total: int, completed: int, running: int, failed: int):
        """更新统计信息

        Args:
            total: 总任务数
            completed: 已完成数
            running: 进行中数
            failed: 失败数
        """
        self.stats_labels["总任务数"].config(text=str(total))
        self.stats_labels["已完成"].config(text=str(completed))
        self.stats_labels["进行中"].config(text=str(running))
        self.stats_labels["失败"].config(text=str(failed))

    def mark_task_completed(self, task_name: str, success: bool = True):
        """标记任务完成

        Args:
            task_name: 任务名称
            success: 是否成功
        """
        now = datetime.now().strftime("%H:%M:%S")

        # 更新任务树
        for item in self.task_tree.get_children():
            values = self.task_tree.item(item)['values']
            if values[0] == task_name:
                status = "完成" if success else "失败"
                start_time = values[3]

                # 计算耗时
                try:
                    start = datetime.strptime(start_time, "%H:%M:%S")
                    end = datetime.strptime(now, "%H:%M:%S")
                    duration = str(end - start)
                except:
                    duration = "-"

                self.task_tree.item(item, values=(
                    values[0],
                    status,
                    "100%",
                    start_time,
                    now,
                    duration
                ))

                # 设置颜色
                if success:
                    self.task_tree.item(item, tags=('success',))
                else:
                    self.task_tree.item(item, tags=('failed',))

                self.task_tree.tag_configure('success', foreground='green')
                self.task_tree.tag_configure('failed', foreground='red')

                break

        # 添加日志
        if success:
            self.add_log(f"任务完成: {task_name}", "INFO")
        else:
            self.add_log(f"任务失败: {task_name}", "ERROR")

    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def _export_log(self):
        """导出日志"""
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))

            self.add_log(f"日志已导出到: {file_path}", "INFO")

    def reset(self):
        """重置监控面板"""
        # 清空任务树
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        # 清空进度
        self.task_progress.clear()
        self.overall_progress['value'] = 0
        self.overall_label.config(text="0%")

        # 重置统计
        self.update_stats(0, 0, 0, 0)

        # 清空日志
        self._clear_log()

        self.add_log("监控面板已重置", "INFO")
