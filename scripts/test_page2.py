"""
Page 2 GUI 功能测试脚本

用于测试 Page 2 GUI 的基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试模块导入...")
    print("=" * 60)

    try:
        from src.workflow.analysis_coordinator_v2 import AgentAnalysisCoordinatorV2
        print("[OK] AgentAnalysisCoordinatorV2 导入成功")
    except Exception as e:
        print(f"[FAIL] AgentAnalysisCoordinatorV2 导入失败: {e}")
        return False

    try:
        from src.gui.page2_gui import Page2GUI
        print("[OK] Page2GUI 导入成功")
    except Exception as e:
        print(f"[FAIL] Page2GUI 导入失败: {e}")
        return False

    try:
        from scripts.page1_gui import Page1GUI
        print("[OK] Page1GUI 导入成功")
    except Exception as e:
        print(f"[FAIL] Page1GUI 导入失败: {e}")
        return False

    print()
    return True


def test_prompts():
    """测试 Prompt 文件是否存在"""
    print("=" * 60)
    print("测试 Prompt 文件...")
    print("=" * 60)

    prompts_dir = project_root / "src" / "prompts" / "analysis"
    required_prompts = [
        "innovation.txt",
        "motivation.txt",
        "roadmap.txt",
        "mechanism.txt",
        "impact.txt"
    ]

    all_ok = True
    for prompt_file in required_prompts:
        prompt_path = prompts_dir / prompt_file
        if prompt_path.exists():
            print(f"[OK] {prompt_file} 存在")
        else:
            print(f"[FAIL] {prompt_file} 不存在")
            all_ok = False

    print()
    return all_ok


def test_markdown_directory():
    """测试 Markdown 目录是否存在"""
    print("=" * 60)
    print("测试 Markdown 目录...")
    print("=" * 60)

    # 检查默认项目目录
    markdown_dir = project_root / "data" / "projects" / "wind_aero" / "markdown" / "all"

    if markdown_dir.exists():
        paper_count = len([d for d in markdown_dir.iterdir() if d.is_dir()])
        print(f"[OK] Markdown 目录存在: {markdown_dir}")
        print(f"[OK] 发现 {paper_count} 篇论文")
    else:
        print(f"[WARN] Markdown 目录不存在: {markdown_dir}")
        print("[WARN] 请先在 Page 1 中转换一些 PDF 文件")

    print()
    return True


def main():
    """主测试函数"""
    print()
    print("=" * 60)
    print("LiteratureHub Page 2 GUI 功能测试")
    print("=" * 60)
    print()

    # 运行所有测试
    results = []
    results.append(("模块导入", test_imports()))
    results.append(("Prompt 文件", test_prompts()))
    results.append(("Markdown 目录", test_markdown_directory()))

    # 打印测试结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    # 检查是否所有测试都通过
    all_passed = all(result for _, result in results)

    print()
    if all_passed:
        print("=" * 60)
        print("[OK] 所有测试通过！可以启动 GUI 进行测试")
        print("=" * 60)
        print()
        print("启动命令：")
        print("  python launch_gui.py")
        print("  或")
        print("  python scripts/page1_gui.py")
        print()
    else:
        print("=" * 60)
        print("[FAIL] 部分测试失败，请检查上述错误信息")
        print("=" * 60)


if __name__ == "__main__":
    main()
