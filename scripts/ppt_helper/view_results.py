"""
结果查看脚本

职责：查看和分析生成的结果
"""

import sys
import io
import yaml
import json
from pathlib import Path

# Windows UTF-8 支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_config():
    """加载配置文件"""
    config_file = Path("config/ppt_helper_config.yaml")
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def view_phase1_results(config):
    """查看 Phase 1 结果"""
    print("📊 Phase 1: 概览分析结果")
    print("=" * 60)

    result_file = Path(config['data_paths']['processed_data']) / "phase1_overview.json"

    if not result_file.exists():
        print("❌ Phase 1 结果不存在")
        return

    with open(result_file, 'r', encoding='utf-8') as f:
        result = json.load(f)

    # 显示领域
    print("\n📚 识别的领域:")
    domains = result.get('domains', [])
    for i, domain in enumerate(domains, 1):
        name = domain.get('name', 'Unknown')
        count = domain.get('paper_count', 0)
        description = domain.get('description', '')
        print(f"\n{i}. {name} ({count} 篇)")
        print(f"   {description}")

    # 显示研究热点
    print("\n\n🔥 研究热点:")
    hotspots = result.get('research_hotspots', [])
    for i, hotspot in enumerate(hotspots[:10], 1):
        topic = hotspot.get('topic', 'Unknown')
        frequency = hotspot.get('frequency', 0)
        trend = hotspot.get('trend', 'Unknown')
        print(f"{i}. {topic} (频次: {frequency}, 趋势: {trend})")

    # 显示 Top 文献
    print("\n\n🏆 Top 10 文献:")
    top_papers = result.get('top_papers', [])
    for i, paper in enumerate(top_papers[:10], 1):
        title = paper.get('title', 'Unknown')
        score = paper.get('score', 0.0)
        year = paper.get('year', 0)

        # ⭐ 安全打印标题（处理特殊字符）
        try:
            safe_title = title[:60].encode('gbk', errors='replace').decode('gbk')
        except:
            safe_title = "（标题包含无法显示的字符）"

        print(f"{i}. [{year}] {safe_title}... (评分: {score:.2f})")

    # 显示总结
    print(f"\n\n📝 总结:")
    summary = result.get('summary', '')
    print(summary)


def view_phase2_results(config):
    """查看 Phase 2 结果"""
    print("\n\n🔬 Phase 2: 领域深度分析结果")
    print("=" * 60)

    domain_results_dir = Path(config['data_paths']['domain_results'])

    if not domain_results_dir.exists():
        print("❌ Phase 2 结果目录不存在")
        return

    # 遍历所有领域
    for domain_dir in domain_results_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        domain_name = domain_dir.name
        analysis_file = domain_dir / "domain_analysis.json"

        if not analysis_file.exists():
            continue

        print(f"\n📚 领域: {domain_name}")
        print("-" * 40)

        with open(analysis_file, 'r', encoding='utf-8') as f:
            result = json.load(f)

        # 显示基本信息
        paper_count = result.get('paper_count', 0)
        status = result.get('status', 'unknown')
        print(f"文献数: {paper_count}")
        print(f"状态: {status}")

        # 如果有分析内容，显示概要
        if status == 'completed':
            overview = result.get('domain_overview', '')
            if overview:
                print(f"\n概要: {overview[:200]}...")


def view_phase3_results(config):
    """查看 Phase 3 结果"""
    print("\n\n📊 Phase 3: 综合总结结果")
    print("=" * 60)

    result_file = Path(config['data_paths']['processed_data']) / "final_ppt_content.json"

    if not result_file.exists():
        print("❌ Phase 3 结果不存在")
        return

    with open(result_file, 'r', encoding='utf-8') as f:
        result = json.load(f)

    # 显示元数据
    metadata = result.get('metadata', {})
    print(f"\n📊 元数据:")
    print(f"  总领域数: {metadata.get('total_domains', 0)}")
    print(f"  总文献数: {metadata.get('total_papers', 0)}")

    # 显示各部分状态
    ppt_content = result.get('ppt_content', {})
    print(f"\n📝 PPT 内容:")

    for part_name, part_data in ppt_content.items():
        filename = part_data.get('filename', 'Unknown')
        max_slides = part_data.get('max_slides', 0)
        status = part_data.get('status', 'pending')
        slide_count = len(part_data.get('slides', []))

        print(f"\n  {part_name}:")
        print(f"    文件: {filename}")
        print(f"    状态: {status}")
        print(f"    幻灯片: {slide_count}/{max_slides}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="结果查看脚本")
    parser.add_argument('--phase1', action='store_true', help='查看 Phase 1 结果')
    parser.add_argument('--phase2', action='store_true', help='查看 Phase 2 结果')
    parser.add_argument('--phase3', action='store_true', help='查看 Phase 3 结果')
    parser.add_argument('--all', action='store_true', help='查看所有结果')

    args = parser.parse_args()

    if not any([args.phase1, args.phase2, args.phase3, args.all]):
        args.all = True

    # 加载配置
    config = load_config()

    print("=" * 60)
    print("📊 结果查看".center(60))
    print("=" * 60)

    if args.all or args.phase1:
        view_phase1_results(config)

    if args.all or args.phase2:
        view_phase2_results(config)

    if args.all or args.phase3:
        view_phase3_results(config)

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
