@echo off
chcp 65001 > nul 2>&1
title LiteratureHub GUI

echo ============================================================
echo LiteratureHub - 文献管理系统
echo ============================================================
echo.

REM 检查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.9+
    echo.
    pause
    exit /b 1
)

echo ✅ 正在启动 GUI...
echo.

REM 启动 GUI
python launch_gui.py

if errorlevel 1 (
    echo.
    echo ❌ 启动失败
    pause
)
