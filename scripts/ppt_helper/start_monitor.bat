@echo off
REM PPT 流水线监控脚本启动器
REM 在后台运行监控器，不影响对话框

cd /d "D:\xfs\phd\github项目\LiteratureHub"

REM 使用 start 命令在后台启动 Python 进程
start /MIN pythonw scripts\ppt_helper\auto_pipeline_monitor.py

echo 监控器已在后台启动
echo 日志文件: logs\pipeline_monitor.log
echo 状态文件: data\ppt_helper\processed\pipeline_state.json
