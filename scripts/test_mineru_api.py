#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU API 测试脚本

测试 MinerU 精准解析 API 是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.mineru_client import MinerUClient, ModelVersion


def test_token():
    """测试 Token 加载"""
    print("=" * 60)
    print("测试 1: Token 加载")
    print("=" * 60)

    try:
        client = MinerUClient()
        print(f"[OK] Token 加载成功")
        print(f"API Base: {client.config.api_base}")
        print(f"Token (前20字符): {client.config.token[:20]}...")
        return True
    except Exception as e:
        print(f"[FAIL] Token 加载失败: {e}")
        return False


def test_parse_by_url():
    """测试 URL 解析（使用 MinerU 示例文件）"""
    print("\n" + "=" * 60)
    print("测试 2: URL 解析")
    print("=" * 60)

    try:
        client = MinerUClient()

        # MinerU 官方示例 PDF
        test_url = "https://cdn-mineru.openxlab.org.cn/demo/example.pdf"

        print(f"测试 URL: {test_url}")
        print("提交任务...")

        result = client.parse_url(
            test_url,
            model_version=ModelVersion.VLM,
            poll=True
        )

        if result.success and result.state.value == "done":
            print(f"[OK] 解析成功!")
            print(f"Task ID: {result.task_id}")
            print(f"ZIP URL: {result.zip_url[:100]}...")
            return True
        else:
            print(f"[FAIL] 解析失败")
            print(f"State: {result.state.value}")
            print(f"Error: {result.error_message}")
            return False

    except Exception as e:
        print(f"[FAIL] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_upload():
    """测试文件上传解析（如果有本地 PDF）"""
    print("\n" + "=" * 60)
    print("测试 3: 文件上传解析")
    print("=" * 60)

    # 查找测试 PDF 文件
    test_pdfs = list(Path("data/projects/wind_aero/pdf").glob("*.pdf"))[:3]

    if not test_pdfs:
        print("[SKIP] 没有找到本地 PDF 文件进行测试")
        print("提示: 将 PDF 文件放在 data/projects/wind_aero/pdf/ 目录下")
        return None

    try:
        client = MinerUClient()
        test_pdf = test_pdfs[0]

        print(f"测试文件: {test_pdf.name}")
        print(f"文件大小: {test_pdf.stat().st_size} bytes")
        print("提交任务...")

        results = client.parse_files_batch(
            [test_pdf],
            model_version=ModelVersion.VLM,
            progress_callback=lambda cur, total, name: print(f"进度: {name}")
        )

        if results:
            result = results.get(test_pdf.name)
            if result and result.success and result.state.value == "done":
                print(f"[OK] 文件上传解析成功!")
                print(f"Task ID: {result.task_id}")
                return True
            else:
                print(f"[FAIL] 文件上传解析失败")
                if result:
                    print(f"State: {result.state.value}")
                    print(f"Error: {result.error_message}")
                return False
        else:
            print("[FAIL] 无返回结果")
            return False

    except Exception as e:
        print(f"[FAIL] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MinerU API 测试" + " " * 34 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # 测试 1: Token 加载
    results.append(("Token 加载", test_token()))

    # 测试 2: URL 解析
    results.append(("URL 解析", test_parse_by_url()))

    # 测试 3: 文件上传
    results.append(("文件上传", test_file_upload()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, success in results:
        status = "[PASS]" if success else "[FAIL]" if success is False else "[SKIP]"
        print(f"{status} {name}")

    passed = sum(1 for _, r in results if r is True)
    total = len(results)

    print()
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print()
        print("所有测试通过! MinerU API 工作正常!")
    else:
        print()
        print("部分测试失败，请检查错误信息。")

    print()
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
