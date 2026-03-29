"""
重命名 agent_results 文件夹以匹配 markdown 文件夹名（最终版本）

执行方式：
    python scripts/rename_agent_results_folders.py --execute

处理逻辑：
1. 包含 DOI 的文件夹：去掉 _10. 后的 DOI
2. 拼写错误：自动修正（Efect→Effect, Infuence→Influence）
3. 年份不同：使用 markdown 的年份
4. 截断匹配：markdown 文件夹名被截断的，使用 markdown 名称
5. 规范化匹配：大小写、连字符转换
"""

import shutil
import json
import re
from pathlib import Path
from datetime import datetime
import sys

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def remove_doi(name):
    """去掉文件夹名中的 DOI 后缀"""
    if '_10.' in name:
        return name.split('_10.')[0]
    return name


def fix_spelling(name):
    """修正拼写错误"""
    corrections = {
        'Efect_of': 'Effect_of',
        'Infuence_of': 'Influence_of',
        'efects_of': 'effects_of',
        'infuence_of': 'influence_of',
    }

    for wrong, correct in corrections.items():
        if wrong in name:
            return name.replace(wrong, correct, 1)
    return name


def normalize_for_matching(name):
    """规范化名称用于匹配（小写、替换连字符为下划线）"""
    normalized = name.lower()
    # 先把连字符和空格替换为下划线
    normalized = re.sub(r'[-\s]+', '_', normalized)
    # 再删除其他特殊字符（保留字母、数字、下划线）
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    return normalized


def find_best_match(agent_name, markdown_folders):
    """查找最佳匹配的 markdown 文件夹"""
    # 规范化 agent 名称
    agent_normalized = normalize_for_matching(agent_name)

    # 尝试多种匹配策略

    # 策略1: 精确匹配（规范化后）
    for md_name in markdown_folders:
        if normalize_for_matching(md_name) == agent_normalized:
            return md_name, 'exact'

    # 策略2: 去掉 DOI 后精确匹配
    agent_no_doi = remove_doi(agent_name)
    agent_no_doi_normalized = normalize_for_matching(agent_no_doi)
    for md_name in markdown_folders:
        if normalize_for_matching(md_name) == agent_no_doi_normalized:
            return md_name, 'doi_removed'

    # 策略3: 修正拼写后匹配
    agent_fixed = fix_spelling(agent_no_doi)
    agent_fixed_normalized = normalize_for_matching(agent_fixed)
    for md_name in markdown_folders:
        if normalize_for_matching(md_name) == agent_fixed_normalized:
            return md_name, 'spelling_fixed'

    # 策略4: 包含匹配（agent 是 markdown 的子集，markdown 被截断）
    agent_key = agent_normalized[5:]  # 去掉年份
    best_match = None
    best_ratio = 0.0

    for md_name in markdown_folders:
        md_normalized = normalize_for_matching(md_name)
        md_key = md_normalized[5:]  # 去掉年份

        # 检查 md_key 是否以 agent_key 开头
        if md_key.startswith(agent_key) and len(agent_key) > 15:
            return md_name, 'markdown_truncated'

        # 检查 agent_key 是否包含在 md_key 中
        if agent_key[:30] in md_key and len(agent_key[:30]) > 20:
            return md_name, 'contains'

    # 策略5: 年份不同（如 agent 是 2019，markdown 是 2020）
    year = agent_name[:4]
    for md_name in markdown_folders:
        if md_name.startswith(year + '_') or md_name.startswith(str(int(year) + 1) + '_'):
            md_normalized = normalize_for_matching(md_name)
            if agent_key in md_normalized or md_normalized.startswith(agent_key[:20]):
                return md_name, 'year_mismatch'

    return None, None


def execute_renames():
    """执行重命名操作"""

    agent_results_dir = PROJECT_ROOT / "data" / "agent_results" / "all"
    markdown_dir = PROJECT_ROOT / "data" / "projects" / "wind_aero" / "markdown" / "all"

    print("=" * 80)
    print("开始批量重命名 Agent Results 文件夹")
    print("=" * 80)

    # 获取所有 markdown 文件夹
    markdown_folders = [f.name for f in markdown_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]

    # 获取所有 agent_results 文件夹（排除索引文件）
    agent_folders = []
    for f in agent_results_dir.iterdir():
        if f.is_dir() and not f.name.startswith('.') and f.name != 'analysis_index.json':
            agent_folders.append(f)

    print(f"Markdown 文件夹: {len(markdown_folders)}")
    print(f"Agent Results 文件夹: {len(agent_folders)}")
    print()

    # 读取索引文件
    index_file = agent_results_dir / "analysis_index.json"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            analysis_index = json.load(f)
    else:
        analysis_index = {"papers": {}, "metadata": {}}

    # 统计
    renamed_count = 0
    skipped_count = 0
    failed_count = 0
    renamed_list = []

    for agent_folder in agent_folders:
        old_name = agent_folder.name
        old_path = agent_folder

        # 检查是否已经匹配
        if old_name in markdown_folders:
            skipped_count += 1
            continue

        # 查找匹配
        new_name, match_type = find_best_match(old_name, markdown_folders)

        if new_name:
            new_path = agent_results_dir / new_name

            # 检查目标是否已存在
            if new_path.exists():
                print(f"[!] 跳过（目标已存在）: {old_name[:50]}...")
                failed_count += 1
                continue

            try:
                # 执行重命名
                shutil.move(str(old_path), str(new_path))
                print(f"[OK] 重命名: {old_name[:50]}")
                print(f"     -> {new_name[:50]}")
                print(f"     类型: {match_type}")
                print()

                # 更新索引文件
                if old_name in analysis_index.get("papers", {}):
                    # 重命名索引中的条目
                    analysis_index["papers"][new_name] = analysis_index["papers"].pop(old_name)
                    # 更新 paper_id 字段
                    analysis_index["papers"][new_name]["paper_id"] = new_name

                renamed_count += 1
                renamed_list.append((old_name, new_name, match_type))

            except Exception as e:
                print(f"[X] 失败: {old_name[:50]}")
                print(f"     错误: {e}")
                print()
                failed_count += 1
        else:
            print(f"[?] 未找到匹配: {old_name}")
            failed_count += 1

    # 保存更新后的索引文件
    if renamed_count > 0:
        analysis_index["metadata"]["last_updated"] = datetime.now().isoformat()
        analysis_index["metadata"]["source"] = "LiterHub (Renamed from Wind-Aero)"

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_index, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] 已更新索引文件: {len(analysis_index['papers'])} 个论文")

    # 打印统计
    print("=" * 80)
    print("重命名操作完成")
    print("=" * 80)
    print(f"跳过（已匹配）: {skipped_count}")
    print(f"重命名成功: {renamed_count}")
    print(f"失败/未找到匹配: {failed_count}")
    print(f"总计: {len(agent_folders)}")


if __name__ == "__main__":
    execute_renames()
