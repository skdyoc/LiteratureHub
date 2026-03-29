"""
重命名 agent_results 文件夹以匹配 markdown 文件夹名

执行方式：
    python scripts/rename_agent_results_folders.py --dry-run  # 预览（不执行）
    python scripts/rename_agent_results_folders.py --execute   # 执行重命名

注意：
- 只重命名 agent_results/ 中的文件夹
- 基于 markdown/all/ 中的文件夹名作为标准
- 会更新 analysis_index.json 中的 paper_id
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def load_paper_mapping():
    """加载 markdown 文件夹名作为标准"""
    markdown_dir = PROJECT_ROOT / "data" / "projects" / "wind_aero" / "markdown" / "all"

    # 获取所有 markdown 文件夹
    markdown_folders = {
        f.name: f
        for f in markdown_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    }

    print(f"[OK] 加载了 {len(markdown_folders)} 个 markdown 文件夹作为标准")

    return markdown_folders


def find_renamed_folders(agent_results_dir, markdown_folders):
    """找出需要重命名的文件夹"""
    renamed_pairs = []

    for folder in agent_results_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith('.'):
            continue

        # 跳过索引文件
        if folder.name == 'analysis_index.json':
            continue

        current_name = folder.name

        # 尝试匹配
        # 1. 精确匹配（已在 markdown_folders 中）
        if current_name in markdown_folders:
            continue  # 不需要重命名

        # 2. 尝试查找匹配（基于文件名相似度）
        matched_name = find_best_match(current_name, markdown_folders.keys())

        if matched_name:
            renamed_pairs.append((current_name, matched_name))
            print(f"  找到匹配: {current_name}")
            print(f"    -> {matched_name}")

    return renamed_pairs


def find_best_match(current_name, candidate_names):
    """查找最佳匹配的文件夹名"""
    from difflib import SequenceMatcher

    # 规范化函数
    def normalize(name):
        import re
        # 转换为小写
        name = name.lower()
        # 移除特殊字符
        name = re.sub(r'[^\w\s]', '', name)
        # 替换空格和连字符为下划线
        name = re.sub(r'[\s-]+', '_', name)
        return name

    current_normalized = normalize(current_name)

    # 精确匹配
    for candidate in candidate_names:
        if normalize(candidate) == current_normalized:
            return candidate

    # 模糊匹配
    best_match = None
    best_ratio = 0.0

    for candidate in candidate_names:
        candidate_normalized = normalize(candidate)
        ratio = SequenceMatcher(None, current_normalized, candidate_normalized).ratio()

        if ratio > best_ratio and ratio >= 0.85:  # 85% 相似度阈值
            best_ratio = ratio
            best_match = candidate

    return best_match


def preview_renames(renamed_pairs, agent_results_dir):
    """预览重命名操作"""
    print("\n" + "=" * 80)
    print("重命名预览（不会执行）")
    print("=" * 80)

    if not renamed_pairs:
        print("[OK] 所有文件夹名已匹配，无需重命名")
        return

    print(f"\n需要重命名 {len(renamed_pairs)} 个文件夹：\n")

    for i, (old_name, new_name) in enumerate(renamed_pairs, 1):
        old_path = agent_results_dir / old_name
        new_path = agent_results_dir / new_name

        # 检查新文件夹是否已存在
        if new_path.exists():
            print(f"{i}. [!] 跳过 (目标已存在):")
            print(f"   {old_name} → {new_name}")
            print(f"   原因: {new_name} 文件夹已存在")
        else:
            print(f"{i}. {old_name} → {new_name}")
            # 显示文件夹内容
            files = list(old_path.iterdir()) if old_path.exists() else []
            print(f"   文件数: {len(files)}")


def execute_renames(renamed_pairs, agent_results_dir, update_index=True):
    """执行重命名操作"""
    print("\n" + "=" * 80)
    print("开始执行重命名操作")
    print("=" * 80)

    if not renamed_pairs:
        print("[OK] 所有文件夹名已匹配，无需重命名")
        return

    # 读取索引文件
    index_file = agent_results_dir / "analysis_index.json"
    if update_index and index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            analysis_index = json.load(f)
    else:
        analysis_index = None

    success_count = 0
    failed_count = 0

    for old_name, new_name in renamed_pairs:
        old_path = agent_results_dir / old_name
        new_path = agent_results_dir / new_name

        # 检查目标是否已存在
        if new_path.exists():
            print(f"[!] 跳过: {old_name} -> {new_name} (目标已存在)")
            failed_count += 1
            continue

        # 执行重命名
        try:
            shutil.move(str(old_path), str(new_path))
            print(f"[OK] 重命名: {old_name} -> {new_name}")
            success_count += 1

            # 更新索引文件
            if analysis_index and old_name in analysis_index.get("papers", {}):
                # 重命名索引中的条目
                analysis_index["papers"][new_name] = analysis_index["papers"].pop(old_name)
                # 更新 paper_id 字段
                analysis_index["papers"][new_name]["paper_id"] = new_name

        except Exception as e:
            print(f"[X] 失败: {old_name} -> {new_name}")
            print(f"   错误: {e}")
            failed_count += 1

    # 保存更新后的索引文件
    if update_index and analysis_index and success_count > 0:
        # 更新元数据
        analysis_index["metadata"]["last_updated"] = datetime.now().isoformat()
        analysis_index["metadata"]["source"] = "LiteratureHub (Renamed from Wind-Aero)"

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_index, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] 已更新索引文件: {index_file}")

    print("\n" + "=" * 80)
    print("重命名操作完成")
    print("=" * 80)
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"总计: {len(renamed_pairs)}")


def main():
    parser = argparse.ArgumentParser(description="重命名 agent_results 文件夹以匹配 markdown 文件夹名")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行重命名")
    parser.add_argument("--execute", action="store_true", help="执行模式，执行重命名操作")
    parser.add_argument("--no-update-index", action="store_true", help="不更新索引文件")

    args = parser.parse_args()

    # 默认为预览模式
    if not args.execute:
        args.dry_run = True

    print("=" * 80)
    print("Agent Results 文件夹重命名工具")
    print("=" * 80)
    print(f"模式: {'预览（不会执行）' if args.dry_run else '执行（会重命名文件夹）'}")
    print()

    # 加载标准文件夹名
    markdown_folders = load_paper_mapping()

    # 分析 agent_results 文件夹
    agent_results_dir = PROJECT_ROOT / "data" / "agent_results" / "all"

    if not agent_results_dir.exists():
        print(f"[X] 目录不存在: {agent_results_dir}")
        return

    print(f"\n分析 agent_results 文件夹...")
    print(f"目录: {agent_results_dir}")

    renamed_pairs = find_renamed_folders(agent_results_dir, markdown_folders)

    print(f"\n找到 {len(renamed_pairs)} 个需要重命名的文件夹")

    # 预览或执行
    if args.dry_run:
        preview_renames(renamed_pairs, agent_results_dir)
    else:
        # 确认操作
        print("\n[!] 警告：即将重命名文件夹！")
        response = input("确认继续？(yes/no): ")

        if response.lower() == 'yes':
            execute_renames(
                renamed_pairs,
                agent_results_dir,
                update_index=not args.no_update_index
            )
        else:
            print("操作已取消")


if __name__ == "__main__":
    main()
