#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LiteratureHub GUI 启动器

一键启动图形界面
用法：
    python launch_gui.py
    或双击：启动GUI.bat
"""

import sys
import os
from pathlib import Path

# 设置控制台编码和 UTF-8 输出
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)


def check_dependencies():
    """检查依赖"""
    missing = []

    try:
        import tkinter
    except ImportError:
        missing.append("tkinter")

    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing:
        print("[X] 缺少依赖库:")
        for lib in missing:
            print(f"   - {lib}")
        print("\n请运行: pip install -r requirements.txt")
        return False

    return True


def check_config():
    """检查配置文件"""
    config_file = project_root / "config" / "api_keys.yaml"

    if not config_file.exists():
        print("[!] 配置文件不存在，正在创建默认配置...")

        config_file.parent.mkdir(parents=True, exist_ok=True)

        default_config = """# LiteratureHub API 密钥配置

# Unpaywall 邮箱（用于开放获取文献下载）
unpaywall:
  email: "skdyoc@gmail.com"

# Elsevier API（用于文献搜索）
elsevier:
  api_key: "12c246d28f9c4eed838447b78644356a"

# GLM API（用于关键词翻译）
glm:
  api_keys:
    - "YOUR_GLM_API_KEY"
"""

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(default_config)

        print(f"[OK] 已创建配置文件: {config_file}")
        print("   请根据需要修改 API 密钥")

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("LiteratureHub GUI 启动器")
    print("=" * 60)
    print()

    # 检查依赖
    if not check_dependencies():
        input("\n按回车键退出...")
        sys.exit(1)

    # 检查配置
    check_config()

    print("[OK] 依赖检查通过")
    print("[OK] 正在启动 GUI...")
    print()

    try:
        # 导入并启动 GUI
        from scripts.page1_gui import Page1GUI

        app = Page1GUI()
        app.run()

    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n[X] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
