"""
PPT 辅助系统自动监控与执行脚本

职责：
- 每10分钟检查一次进度
- 自动执行四步流程
- 清理Python缓存和进程
- 完成后自动关机

作者：哈雷酱
创建日期：2026-03-30
"""

import sys
import os
import subprocess
import time
import json
import psutil
from pathlib import Path
from datetime import datetime

# Windows UTF-8 支持
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


class PPTPipelineMonitor:
    """PPT 流水线监控器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.scripts_dir = self.project_root / "scripts" / "ppt_helper"
        self.data_dir = self.project_root / "data" / "ppt_helper" / "processed"
        self.log_file = self.project_root / "logs" / "pipeline_monitor.log"
        self.state_file = self.data_dir / "pipeline_state.json"
        self.api_keys_dir = Path(r"D:\xfs\phd\.私人信息")

        # 创建日志目录
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        # 输出到控制台
        print(log_line.strip())

        # 写入日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def kill_python_processes(self):
        """清理所有 Python 进程"""
        self.log("正在清理 Python 进程...", "INFO")

        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 检查是否是 Python 进程
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        # 检查命令行是否包含 LiteratureHub
                        cmdline = proc.info['cmdline']
                        if cmdline and any('LiteratureHub' in str(cmd) for cmd in cmdline):
                            self.log(f"  - 终止进程 {proc.info['pid']}", "DEBUG")
                            proc.terminate()
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            self.log(f"清理了 {killed_count} 个 Python 进程", "INFO")

        except Exception as e:
            self.log(f"清理进程失败: {e}", "ERROR")

    def clear_python_cache(self):
        """清理 Python 缓存"""
        self.log("正在清理 Python 缓存...", "INFO")

        try:
            # 清理 __pycache__ 目录
            cache_dirs = list(self.project_root.rglob("__pycache__"))
            for cache_dir in cache_dirs:
                try:
                    import shutil
                    shutil.rmtree(cache_dir)
                    self.log(f"  - 删除 {cache_dir.relative_to(self.project_root)}", "DEBUG")
                except Exception as e:
                    self.log(f"  - 删除失败 {cache_dir}: {e}", "DEBUG")

            # 清理 .pyc 文件
            pyc_files = list(self.project_root.rglob("*.pyc"))
            for pyc_file in pyc_files:
                try:
                    pyc_file.unlink()
                    self.log(f"  - 删除 {pyc_file.relative_to(self.project_root)}", "DEBUG")
                except Exception as e:
                    self.log(f"  - 删除失败 {pyc_file}: {e}", "DEBUG")

            self.log("Python 缓存清理完成", "INFO")

        except Exception as e:
            self.log(f"清理缓存失败: {e}", "ERROR")

    def load_state(self) -> dict:
        """加载当前状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"加载状态失败: {e}", "ERROR")

        # 默认状态
        return {
            "current_step": 0,
            "steps": [
                {"name": "Phase 1: 概览分析", "script": "01_overview.py", "status": "pending", "output": "phase1_overview.json"},
                {"name": "Phase 2: 领域深度分析", "script": "02_domain_analysis.py", "status": "pending", "output": "by_domain"},
                {"name": "Phase 3: 综合总结", "script": "03_summary.py", "status": "pending", "output": "final_ppt_content.json"},
                {"name": "HTML 生成", "script": "04_generate_html.py", "status": "pending", "output": "html_output"}
            ],
            "last_check": None,
            "total_runs": 0
        }

    def save_state(self, state: dict):
        """保存当前状态"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"保存状态失败: {e}", "ERROR")

    def check_output_exists(self, output_path: str) -> bool:
        """检查输出文件是否存在"""
        output_full = self.data_dir / output_path

        if output_path.endswith('.json'):
            # 检查 JSON 文件
            if output_full.exists():
                try:
                    with open(output_full, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return bool(data)  # 确保文件不为空
                except Exception:
                    return False
        else:
            # 检查目录
            if output_full.exists() and output_full.is_dir():
                # 检查目录是否有 HTML 文件
                html_files = list(output_full.rglob("*.html"))
                return len(html_files) > 0

        return False

    def execute_script(self, script_name: str) -> bool:
        """执行指定的脚本"""
        script_path = self.scripts_dir / script_name

        if not script_path.exists():
            self.log(f"脚本不存在: {script_path}", "ERROR")
            return False

        self.log(f"开始执行: {script_name}", "INFO")
        self.log(f"脚本路径: {script_path}", "DEBUG")

        try:
            # 设置环境变量
            env = os.environ.copy()

            # 添加项目根目录到 PYTHONPATH
            pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{str(self.project_root)};{pythonpath}"

            # 执行脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=7200  # 2小时超时
            )

            # 记录输出
            self.log(f"--- 标准输出 ---", "DEBUG")
            for line in result.stdout.splitlines():
                self.log(f"  {line}", "DEBUG")

            if result.stderr:
                self.log(f"--- 标准错误 ---", "DEBUG")
                for line in result.stderr.splitlines():
                    self.log(f"  {line}", "DEBUG")

            if result.returncode == 0:
                self.log(f"✓ {script_name} 执行成功", "INFO")
                return True
            else:
                self.log(f"✗ {script_name} 执行失败 (返回码: {result.returncode})", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"✗ {script_name} 执行超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ {script_name} 执行异常: {e}", "ERROR")
            return False

    def shutdown_system(self):
        """关机"""
        self.log("=" * 60, "INFO")
        self.log("所有任务已完成！准备关机...", "INFO")
        self.log("=" * 60, "INFO")

        time.sleep(10)  # 10秒后关机

        if sys.platform == "win32":
            # Windows 关机
            os.system("shutdown /s /t 0 /c \"PPT 流水线已完成，系统即将关机\"")

    def run(self):
        """运行监控主流程"""
        self.log("=" * 60, "INFO")
        self.log("PPT 流水线监控器启动", "INFO")
        self.log("=" * 60, "INFO")

        # 加载状态
        state = self.load_state()
        state["total_runs"] += 1
        state["last_check"] = datetime.now().isoformat()

        self.log(f"第 {state['total_runs']} 次检查", "INFO")
        self.log(f"当前步骤: {state['current_step']}", "INFO")

        # 检查是否已完成
        if state["current_step"] >= len(state["steps"]):
            self.log("所有步骤已完成！", "INFO")

            # 检查 HTML 输出
            html_output = self.data_dir / "html_output"
            if html_output.exists():
                html_files = list(html_output.rglob("*.html"))
                self.log(f"HTML 文件数量: {len(html_files)}", "INFO")

                if len(html_files) > 0:
                    self.log("✓ HTML 生成完整，准备关机", "INFO")
                    self.save_state(state)
                    self.shutdown_system()
                    return
            else:
                self.log("⚠ HTML 输出不存在，重新生成", "WARNING")
                state["current_step"] = 3  # 回到 HTML 生成步骤

        # 执行当前步骤
        current_step_idx = state["current_step"]
        if current_step_idx < len(state["steps"]):
            step = state["steps"][current_step_idx]

            self.log(f"当前任务: {step['name']}", "INFO")

            # 检查输出是否已存在
            if self.check_output_exists(step["output"]):
                self.log(f"✓ 输出已存在: {step['output']}", "INFO")
                step["status"] = "completed"
                state["current_step"] += 1
                self.save_state(state)
            else:
                # 执行脚本
                self.log(f"执行脚本: {step['script']}", "INFO")

                # 清理
                self.kill_python_processes()
                self.clear_python_cache()

                # 执行
                success = self.execute_script(step["script"])

                # 再次清理
                self.kill_python_processes()
                self.clear_python_cache()

                if success:
                    step["status"] = "completed"
                    state["current_step"] += 1
                    self.save_state(state)
                else:
                    step["status"] = "failed"
                    self.save_state(state)

        # 显示状态摘要
        self.log("-" * 60, "INFO")
        self.log("状态摘要:", "INFO")
        for i, step in enumerate(state["steps"]):
            status_symbol = {
                "pending": "⏳",
                "running": "▶",
                "completed": "✓",
                "failed": "✗"
            }.get(step["status"], "?")

            current_marker = " <<< 当前" if i == state["current_step"] else ""
            self.log(f"  {status_symbol} {step['name']}{current_marker}", "INFO")

        self.log("=" * 60, "INFO")


def main():
    """主函数"""
    monitor = PPTPipelineMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
