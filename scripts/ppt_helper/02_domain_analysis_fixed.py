"""
Phase 2: 领域深度分析（修复版）

职责：直接使用实际的分类文件夹数据进行领域深度分析
"""

import sys
import io
import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Windows UTF-8 支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def get_categories_with_papers(config) -> Dict[str, List[str]]:
    """
    获取所有分类及其论文列表

    Returns:
        {分类名称: [论文ID列表]}
    """
    categories_dir = Path(config['data_paths']['source_markdowns']) / "categories"

    if not categories_dir.exists():
        print(f"❌ 分类目录不存在: {categories_dir}")
        return {}

    categories = {}

    for category_dir in categories_dir.iterdir():
        if not category_dir.is_dir():
            continue

        # 获取该分类下的所有论文
        paper_ids = []
        for paper_dir in category_dir.iterdir():
            if paper_dir.is_dir():
                # 检查是否有 full.md
                full_md = paper_dir / "full.md"
                if full_md.exists():
                    paper_ids.append(paper_dir.name)

        if paper_ids:
            categories[category_dir.name] = paper_ids

    return categories


def analyze_single_domain(
    config,
    domain_name: str,
    paper_ids: List[str],
    max_papers: int = 10
) -> Dict[str, Any]:
    """
    分析单个领域

    Args:
        config: 配置对象
        domain_name: 领域名称
        paper_ids: 论文 ID 列表
        max_papers: 最大论文数量

    Returns:
        分析结果
    """
    from src.ppt_helper.agents.domain_analyzer_agent import DomainAnalyzerAgent
    from src.ppt_helper.readers.full_md_reader import FullMdReader
    from src.ppt_helper.workers.content_extractor import ContentExtractor

    print(f"\n{'=' * 60}")
    print(f"分析领域: {domain_name}")
    print(f"总文献数: {len(paper_ids)}")
    print(f"分析限制: {max_papers} 篇")
    print('=' * 60)

    # 限制论文数量
    selected_papers = paper_ids[:max_papers]
    print(f"选择文献: {len(selected_papers)} 篇")

    # 读取 full.md
    print(f"\n读取 {len(selected_papers)} 篇文献的 full.md...")
    reader = FullMdReader()
    # ⭐ 实际的 full.md 文件在 all/ 目录下，不是在分类目录下
    markdown_path = Path(config['data_paths']['source_markdowns']) / "all"

    full_md_contents = {}
    for i, paper_id in enumerate(selected_papers, 1):
        full_md_file = markdown_path / paper_id / "full.md"

        if not full_md_file.exists():
            print(f"  ⚠️ [{i}/{len(selected_papers)}] {paper_id}: 文件不存在")
            continue

        content = reader.read_full_md(str(full_md_file))
        if content:
            full_md_contents[paper_id] = content
            print(f"  ✅ [{i}/{len(selected_papers)}] {paper_id}: {len(content)} 字符")
        else:
            print(f"  ❌ [{i}/{len(selected_papers)}] {paper_id}: 读取失败")

    print(f"\n成功读取: {len(full_md_contents)}/{len(selected_papers)} 篇")

    if not full_md_contents:
        print(f"❌ {domain_name}: 没有成功读取任何文献")
        return {"status": "failed", "error": "no_papers"}

    # 读取 agent_results JSON
    print(f"\n读取 agent_results JSON...")
    agent_results_path = Path(config['data_paths']['source_agent_results'])
    agent_results_json = {}

    for paper_id in selected_papers:
        paper_dir = agent_results_path / paper_id

        if not paper_dir.exists():
            continue

        paper_results = {}
        for json_name in ["motivation.json", "innovation.json", "mechanism.json", "impact.json", "roadmap.json"]:
            json_file = paper_dir / json_name
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "result" in data:
                        result = data["result"]
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except:
                                result = {}
                        paper_results[json_name.replace(".json", "")] = result
                    else:
                        paper_results[json_name.replace(".json", "")] = data
                except Exception as e:
                    pass

        if paper_results:
            agent_results_json[paper_id] = paper_results

    print(f"成功读取: {len(agent_results_json)} 篇的 agent_results")

    # 调用 Agent 分析
    agent = DomainAnalyzerAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )

    input_data = {
        "domain_name": domain_name,
        "paper_ids": selected_papers,
        "full_md_contents": full_md_contents,
        "agent_results_json": agent_results_json,
    }

    print(f"\n调用 {config['api']['model']} API 进行深度分析...")

    result = agent.analyze(input_data)

    return result


def main():
    """主函数"""
    print("=" * 60)
    print("🔬 Phase 2: 领域深度分析（修复版）".center(60))
    print("=" * 60)

    # 加载配置
    config_file = Path("config/ppt_helper_config.yaml")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 获取所有分类
    print("\n获取分类数据...")
    categories = get_categories_with_papers(config)

    if not categories:
        print("❌ 没有找到任何分类数据")
        return

    print(f"✅ 找到 {len(categories)} 个分类:")
    for cat_name, papers in categories.items():
        print(f"  - {cat_name}: {len(papers)} 篇")

    # 准备输出目录
    output_dir = Path(config['data_paths']['processed_data']) / "by_domain"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 分析每个领域
    results = {}
    success_count = 0

    for domain_name, paper_ids in categories.items():
        result = analyze_single_domain(config, domain_name, paper_ids, max_papers=10)

        # ⭐ 创建子目录并保存为 domain_analysis.json（Phase 3 期望的格式）
        domain_subdir = output_dir / domain_name
        domain_subdir.mkdir(parents=True, exist_ok=True)

        domain_file = domain_subdir / "domain_analysis.json"
        with open(domain_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        results[domain_name] = result

        if result.get("status") != "failed":
            success_count += 1

    # 总结
    print("\n" + "=" * 60)
    print("📊 分析总结".center(60))
    print("=" * 60)
    print(f"总计领域: {len(categories)}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {len(categories) - success_count}")

    for domain_name, result in results.items():
        status = "✅" if result.get("status") != "failed" else "❌"
        print(f"  {status} {domain_name}")

    print("\n✅ Phase 2 完成！")
    print(f"📁 结果保存在: {output_dir}")


if __name__ == "__main__":
    main()
