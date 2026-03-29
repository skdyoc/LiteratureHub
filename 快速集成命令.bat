@echo off
REM LiteratureHub Page 2 GUI 快速集成脚本
REM 创建者: 哈雷酱（傲娇大小姐工程师）✨

echo ============================================================
echo LiteratureHub Page 2 GUI 快速集成脚本
echo 使用 DeepSeek 无限并发模式 ⚡
echo ============================================================
echo.

REM 设置项目路径
set LIT_HUB="d:\xfs\phd\github项目\LiteratureHub"
set WIND_AERO="d:\xfs\phd\github项目\Wind-Aero-Literature-Analysis-System"

echo [1/5] 复制 DeepSeek 客户端...
copy "%WIND_AERO%\src\api\deepseek_client.py" "%LIT_HUB%\src\api\deepseek_client.py"
if %errorlevel% equ 0 (
    echo     ✅ DeepSeek 客户端复制成功
) else (
    echo     ❌ 复制失败
    pause
    exit /b 1
)

echo.
echo [2/5] 复制分析协调器...
copy "%WIND_AERO%\scripts\agent_parallel_coordinator_v2_standalone.py" "%LIT_HUB%\src\workflow\analysis_coordinator.py"
if %errorlevel% equ 0 (
    echo     ✅ 分析协调器复制成功
) else (
    echo     ❌ 复制失败
    pause
    exit /b 1
)

echo.
echo [3/5] 创建 Page 2 GUI 文件...
echo. > "%LIT_HUB%\src\gui\page2_gui.py"
echo     ✅ page2_gui.py 创建成功

echo.
echo [4/5] 复制 Prompts 模板...
xcopy "%WIND_AERO%\prompts" "%LIT_HUB%\src\prompts\analysis" /E /I /Y
echo     ✅ Prompts 模板复制成功

echo.
echo [5/5] 集成完成！
echo.
echo ============================================================
echo 📋 下一步操作：
echo ============================================================
echo.
echo 1. 编辑文件进行必要修改：
echo    - %LIT_HUB%\src\workflow\analysis_coordinator.py
echo      将 markdown_root 改为相对路径
echo.
echo    - %LIT_HUB%\src\gui\page2_gui.py
echo      复制 Page 2 GUI 代码（见文档）
echo.
echo    - %LIT_HUB%\scripts\page1_gui.py
echo      添加 Notebook 页面切换
echo.
echo 2. 更新 API 密钥：
echo    - %LIT_HUB%\config\api_keys.yaml
echo      添加 deepseek.api_key
echo.
echo 3. 启动 GUI：
echo    cd %LIT_HUB%
echo    python launch_gui.py
echo.
echo ============================================================
echo ⚡ 使用 DeepSeek 无限并发模式！
echo ============================================================
echo.
pause
