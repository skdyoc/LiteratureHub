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
工作流面板组件

显示和管理分析工作流。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List, Callable
import logging
from datetime import datetime
from enum import Enum


class WorkflowStep(Enum):
    """工作流步骤枚举"""
    SEARCH = "search"
    DOWNLOAD = "download"
    PARSE = "parse"
    ANALYZE = "analyze"
    GENERATE = "generate"


class WorkflowPanel(ttk.Frame):
    """工作流面板

    显示和管理分析工作流的执行。

    功能：
    - 工作流步骤显示
    - 步骤执行控制
    - 进度跟踪
    - 日志显示
    - 错误处理
    """

    def __init__(
        self,
        parent: tk.Widget,
        workflow_engine: Any,
        on_step_complete: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_workflow_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """初始化工作流面板

        Args:
            parent: 父组件
            workflow_engine: 工作流引擎
            on_step_complete: 步骤完成回调
            on_workflow_complete: 工作流完成回调
        """
        super().__init__(parent)

        self.workflow_engine = workflow_engine
        self.on_step_complete = on_step_complete
        self.on_workflow_complete = on_workflow_complete
        self.logger = logging.getLogger(self.__class__.__name__)

        # 工作流状态
        self.current_step: Optional[str] = None
        self.step_status: Dict[str, str] = {}  # step -> status
        self.is_running = False

        # 创建界面
        self._create_widgets()

        # 初始化步骤状态
        self._initialize_steps()

    def _create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            title_frame,
            text="分析工作流",
            font=("", 12, "bold")
        ).pack(side=tk.LEFT)

        # 工作流状态
        self.status_label = ttk.Label(title_frame, text="就绪")
        self.status_label.pack(side=tk.RIGHT)

        # 步骤列表
        steps_frame = ttk.LabelFrame(self, text="工作流步骤")
        steps_frame.pack(fill=tk.X, padx=10, pady=10)

        # 步骤1: 文献搜索
        self._create_step_ui(
            steps_frame,
            WorkflowStep.SEARCH.value,
            "文献搜索",
            "从多个数据库搜索相关文献"
        )

        # 步骤2: PDF下载
        self._create_step_ui(
            steps_frame,
            WorkflowStep.DOWNLOAD.value,
            "PDF下载",
            "下载文献的PDF文件"
        )

        # 步骤3: 文档解析
        self._create_step_ui(
            steps_frame,
            WorkflowStep.PARSE.value,
            "文档解析",
            "解析PDF文档为结构化数据"
        )

        # 步骤4: AI分析
        self._create_step_ui(
            steps_frame,
            WorkflowStep.ANALYZE.value,
            "AI分析",
            "使用AI深度分析文献内容"
        )

        # 步骤5: PPT生成
        self._create_step_ui(
            steps_frame,
            WorkflowStep.GENERATE.value,
            "PPT生成",
            "生成分析报告PPT"
        )

        # 进度显示
        progress_frame = ttk.LabelFrame(self, text="进度")
        progress_frame.pack(fill=tk.X, padx=10, pady=10)

        # 总体进度
        ttk.Label(progress_frame, text="总体进度:").pack(anchor=tk.W, padx=5, pady=2)
        self.overall_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.overall_progress.pack(fill=tk.X, padx=5, pady=2)
        self.overall_percent_label = ttk.Label(progress_frame, text="0%")
        self.overall_percent_label.pack(anchor=tk.E, padx=5)

        # 当前步骤进度
        ttk.Label(progress_frame, text="当前步骤:").pack(anchor=tk.W, padx=5, pady=2)
        self.current_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.current_progress.pack(fill=tk.X, padx=5, pady=2)
        self.current_percent_label = ttk.Label(progress_frame, text="0%")
        self.current_percent_label.pack(anchor=tk.E, padx=5)

        # 日志显示
        log_frame = ttk.LabelFrame(self, text="执行日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(log_frame, height=8, width=50)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        # 控制按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_btn = ttk.Button(button_frame, text="开始", command=self._start_workflow)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(button_frame, text="暂停", command=self._pause_workflow, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.resume_btn = ttk.Button(button_frame, text="继续", command=self._resume_workflow, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(button_frame, text="取消", command=self._cancel_workflow, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="清空日志", command=self._clear_log).pack(side=tk.RIGHT, padx=5)

    def _create_step_ui(self, parent: tk.Widget, step_id: str, title: str, description: str):
        """创建步骤UI

        Args:
            parent: 父组件
            step_id: 步骤ID
            title: 步骤标题
            description: 步骤描述
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # 状态图标
        status_label = ttk.Label(frame, text="⏸️", width=3)
        status_label.pack(side=tk.LEFT)

        # 步骤标题
        ttk.Label(frame, text=title, font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # 步骤描述
        ttk.Label(frame, text=f"({description})", foreground="gray").pack(side=tk.LEFT, padx=5)

        # 执行按钮
        run_btn = ttk.Button(frame, text="执行", width=6, command=lambda: self._run_single_step(step_id))
        run_btn.pack(side=tk.RIGHT, padx=5)

        # 保存引用
        if not hasattr(self, 'step_widgets'):
            self.step_widgets = {}

        self.step_widgets[step_id] = {
            "frame": frame,
            "status_label": status_label,
            "run_btn": run_btn
        }

    def _initialize_steps(self):
        """初始化步骤状态"""
        for step in WorkflowStep:
            self.step_status[step.value] = "pending"

    def _update_step_status(self, step_id: str, status: str):
        """更新步骤状态

        Args:
            step_id: 步骤ID
            status: 状态 (pending, running, completed, failed)
        """
        self.step_status[step_id] = status

        # 更新UI
        if step_id in self.step_widgets:
            status_icons = {
                "pending": "⏸️",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌"
            }

            icon = status_icons.get(status, "⏸️")
            self.step_widgets[step_id]["status_label"].config(text=icon)

    def _start_workflow(self):
        """开始工作流"""
        if self.is_running:
            messagebox.showwarning("警告", "工作流正在运行中")
            return

        self.is_running = True
        self.current_step = None

        # 更新UI
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_label.config(text="运行中")

        # 重置所有步骤状态
        for step in WorkflowStep:
            self._update_step_status(step.value, "pending")

        # 清空日志
        self._clear_log()

        # 开始执行
        self._execute_next_step()

    def _execute_next_step(self):
        """执行下一个步骤"""
        # 找到下一个待执行的步骤
        steps_order = [
            WorkflowStep.SEARCH.value,
            WorkflowStep.DOWNLOAD.value,
            WorkflowStep.PARSE.value,
            WorkflowStep.ANALYZE.value,
            WorkflowStep.GENERATE.value
        ]

        next_step = None
        for step in steps_order:
            if self.step_status[step] in ["pending", "running"]:
                next_step = step
                break

        if not next_step:
            # 工作流完成
            self._workflow_completed()
            return

        # 执行步骤
        self._run_step(next_step)

    def _run_step(self, step_id: str):
        """运行单个步骤

        Args:
            step_id: 步骤ID
        """
        self.current_step = step_id
        self._update_step_status(step_id, "running")

        step_names = {
            WorkflowStep.SEARCH.value: "文献搜索",
            WorkflowStep.DOWNLOAD.value: "PDF下载",
            WorkflowStep.PARSE.value: "文档解析",
            WorkflowStep.ANALYZE.value: "AI分析",
            WorkflowStep.GENERATE.value: "PPT生成"
        }

        self._add_log(f"开始执行: {step_names.get(step_id, step_id)}")

        try:
            # 调用工作流引擎执行步骤
            if self.workflow_engine:
                # 这里应该调用实际的工作流引擎方法
                # 由于是示例，我们模拟执行
                self._simulate_step_execution(step_id)
            else:
                raise ValueError("工作流引擎未初始化")

        except Exception as e:
            self._handle_step_error(step_id, str(e))

    def _simulate_step_execution(self, step_id: str):
        """模拟步骤执行（实际应调用工作流引擎）

        Args:
            step_id: 步骤ID
        """
        import random

        # 模拟进度更新
        def update_progress(progress: int):
            self._update_current_progress(progress)
            if progress >= 100:
                self._handle_step_complete(step_id, {"status": "success"})

        # 模拟执行（使用after模拟异步）
        self.after(500, lambda: update_progress(30))
        self.after(1000, lambda: update_progress(60))
        self.after(1500, lambda: update_progress(90))
        self.after(2000, lambda: update_progress(100))

    def _handle_step_complete(self, step_id: str, result: Dict[str, Any]):
        """处理步骤完成

        Args:
            step_id: 步骤ID
            result: 执行结果
        """
        if result.get("status") == "success":
            self._update_step_status(step_id, "completed")
            self._add_log(f"步骤完成: {step_id}", "success")

            # 触发回调
            if self.on_step_complete:
                self.on_step_complete(step_id, result)

            # 更新总体进度
            completed_count = sum(1 for status in self.step_status.values() if status == "completed")
            total_count = len(WorkflowStep)
            overall_progress = int((completed_count / total_count) * 100)
            self._update_overall_progress(overall_progress)

            # 执行下一步
            self.after(100, self._execute_next_step)

        else:
            self._handle_step_error(step_id, result.get("error", "Unknown error"))

    def _handle_step_error(self, step_id: str, error: str):
        """处理步骤错误

        Args:
            step_id: 步骤ID
            error: 错误信息
        """
        self._update_step_status(step_id, "failed")
        self._add_log(f"步骤失败: {step_id} - {error}", "error")

        # 询问用户是否继续
        if messagebox.askyesno("错误", f"步骤执行失败: {error}\n\n是否继续执行下一步？"):
            # 跳过此步骤，继续执行
            self.after(100, self._execute_next_step)
        else:
            # 停止工作流
            self._cancel_workflow()

    def _workflow_completed(self):
        """工作流完成"""
        self.is_running = False
        self.current_step = None

        # 更新UI
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="完成")

        self._add_log("工作流执行完成！", "success")

        # 触发回调
        if self.on_workflow_complete:
            self.on_workflow_complete({
                "status": "completed",
                "step_status": self.step_status.copy()
            })

    def _pause_workflow(self):
        """暂停工作流"""
        if not self.is_running:
            return

        self.is_running = False

        # 更新UI
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.NORMAL)
        self.status_label.config(text="已暂停")

        self._add_log("工作流已暂停")

    def _resume_workflow(self):
        """继续工作流"""
        if self.is_running:
            return

        self.is_running = True

        # 更新UI
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.status_label.config(text="运行中")

        self._add_log("工作流继续执行")

        # 继续执行
        self._execute_next_step()

    def _cancel_workflow(self):
        """取消工作流"""
        self.is_running = False
        self.current_step = None

        # 更新UI
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="已取消")

        self._add_log("工作流已取消")

    def _run_single_step(self, step_id: str):
        """运行单个步骤

        Args:
            step_id: 步骤ID
        """
        if self.is_running:
            messagebox.showwarning("警告", "工作流正在运行中，请先暂停或取消")
            return

        self._add_log(f"单独执行步骤: {step_id}")
        self._run_step(step_id)

    def _update_overall_progress(self, progress: int):
        """更新总体进度

        Args:
            progress: 进度值 (0-100)
        """
        self.overall_progress['value'] = progress
        self.overall_percent_label.config(text=f"{progress}%")

    def _update_current_progress(self, progress: int):
        """更新当前步骤进度

        Args:
            progress: 进度值 (0-100)
        """
        self.current_progress['value'] = progress
        self.current_percent_label.config(text=f"{progress}%")

    def _add_log(self, message: str, level: str = "info"):
        """添加日志

        Args:
            message: 日志消息
            level: 日志级别 (info, success, warning, error)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 颜色标记
        colors = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }

        color = colors.get(level, "black")

        # 插入日志
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

        # 应用颜色（使用tag配置）
        # 为不同级别的日志应用不同的颜色
        self.log_text.tag_configure(level, foreground=color)
        # 获取最后一行的行号
        last_line = int(self.log_text.index(tk.END).split('.')[0]) - 1
        self.log_text.tag_add(level, f"{last_line}.0", f"{last_line}.end")

    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
