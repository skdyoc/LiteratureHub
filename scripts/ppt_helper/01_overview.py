"""
Phase 1: 概览分析脚本

职责：基于 agent_results 生成领域整体概览
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
    import sys
    print("DEBUG: load_config() 开始", flush=True)
    sys.stdout.flush()

    config_file = Path("config/ppt_helper_config.yaml")
    print(f"DEBUG: 配置文件路径: {config_file}", flush=True)
    sys.stdout.flush()

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print("DEBUG: load_config() 完成", flush=True)
    sys.stdout.flush()
    return config


def prepare_agent_summaries(config):
    """
    准备文献摘要（⭐ 读取完整的 agent_results）

    返回格式：
    [
        {
            "metadata": PaperMetadata 对象,
            "innovation_summary": innovation.json 完整内容,
            "paper_id": "完整ID"
        },
        ...
    ]
    """
    import sys
    from src.ppt_helper.workers.content_extractor import ContentExtractor

    print("📊 提取文献摘要...", flush=True)
    sys.stdout.flush()

    print("DEBUG: 初始化 ContentExtractor...", flush=True)
    sys.stdout.flush()

    extractor = ContentExtractor(
        agent_results_path=config['data_paths']['source_agent_results']
    )

    print("DEBUG: ContentExtractor 初始化完成", flush=True)
    sys.stdout.flush()

    # 获取所有论文 ID
    print("DEBUG: 获取论文 ID 列表...", flush=True)
    sys.stdout.flush()
    paper_ids = extractor.get_available_paper_ids()
    print(f"  ✓ 找到 {len(paper_ids)} 篇文献", flush=True)
    sys.stdout.flush()

    # ⭐ 处理所有可用文献
    MAX_PAPERS = len(paper_ids)  # 处理所有文献
    print(f"  ⏳ 开始提取摘要（全部 {MAX_PAPERS} 篇）...", flush=True)
    print(f"  ⚠️  警告：处理大量文献可能导致 Prompt 过长，API 调用可能失败", flush=True)
    sys.stdout.flush()

    # ⭐ 调用新的 extract_all_agent_results() 方法
    all_agent_results = extractor.extract_all_agent_results(paper_ids[:MAX_PAPERS])

    print(f"  ✓ 提取了 {len(all_agent_results)} 篇的 agent_results", flush=True)
    sys.stdout.flush()

    # ⭐ 转换为 OverviewAgent 需要的格式
    summaries_list = []
    for paper_id, agent_results in all_agent_results.items():
        # 提取元数据
        metadata = extractor.extract_metadata(paper_id)

        if not metadata:
            print(f"  ⚠️  跳过 {paper_id}: 元数据提取失败", flush=True)
            continue

        # 提取 innovation（完整的，不只是计数）
        innovation = agent_results.get("innovation", {})

        # 构造摘要项
        summary_item = {
            "metadata": metadata,
            "innovation_summary": innovation,  # ⭐ 完整的 innovation.json
            "paper_id": paper_id
        }

        summaries_list.append(summary_item)

    # ⭐ 按评分和时间权重排序（优先高评分和最新文献）
    def sort_key(summary_item):
        """
        排序函数：基于评分和时间权重

        Args:
            summary_item: 包含 metadata 的字典
        """
        metadata = summary_item.get("metadata")

        if not metadata or not hasattr(metadata, 'score') or not metadata.score:
            return (0, 0)  # 无评分的排最后

        score = metadata.score if metadata.score else 0
        year = metadata.year if metadata.year else 0

        # 时间权重（2026最高，2018最低）
        time_weights = {
            2026: 1.0,
            2025: 0.9,
            2024: 0.8,
            2023: 0.7,
            2022: 0.5,
            2021: 0.3,
            2020: 0.1,
            2019: 0.1,
            2018: 0.1,
            2017: 0.05,
            2016: 0.05,
            2015: 0.05,
            2014: 0.05,
            2013: 0.05,
            2012: 0.05,
            2011: 0.05,
            2010: 0.05,
        }
        time_weight = time_weights.get(year, 0.05)

        # 综合评分 = 原始评分 × 时间权重
        weighted_score = score * time_weight
        return (-weighted_score, -year)  # 负号用于降序排序

    summaries_list.sort(key=sort_key)

    # ⭐ 统计年份分布
    year_count = {}
    for s in summaries_list:
        metadata = s.get("metadata")
        if metadata and hasattr(metadata, 'year') and metadata.year:
            year_count[metadata.year] = year_count.get(metadata.year, 0) + 1

    print(f"  ✓ 转换为列表: {len(summaries_list)} 项", flush=True)
    print(f"  📊 文献年份分布:", flush=True)
    for year in sorted(year_count.keys()):
        print(f"     - {year}年: {year_count[year]} 篇", flush=True)

    # ⭐ 计算预估的 Prompt 长度（包含完整的 innovation.json）
    total_chars = sum(len(str(s.get("innovation_summary", {}))) for s in summaries_list)
    print(f"  📏 预估 innovation 数据大小: {total_chars} 字符", flush=True)
    sys.stdout.flush()

    return summaries_list  # 返回所有已排序的文献


def run_overview_analysis(config, agent_summaries):
    """执行概览分析"""
    from src.ppt_helper.agents.overview_agent import OverviewAgent

    print("\n🔍 Phase 1: 概览分析（总）")
    print("-" * 60)

    print(f"DEBUG: 收到 {len(agent_summaries)} 篇摘要")

    # 初始化 Agent
    print("DEBUG: 初始化 OverviewAgent...")
    agent = OverviewAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )
    print("DEBUG: OverviewAgent 初始化完成")

    # 准备输入数据
    input_data = {
        "agent_results_summaries": agent_summaries,
        "min_domains": config['domain_classification']['min_domains'],
        "max_domains": config['domain_classification']['max_domains']
    }

    print(f"DEBUG: input_data 准备完成")
    print(f"  - agent_summaries: {len(agent_summaries)} 项")
    print(f"  - min_domains: {input_data['min_domains']}")
    print(f"  - max_domains: {input_data['max_domains']}")

    # 执行分析
    print("DEBUG: 开始调用 agent.analyze()...")
    result = agent.analyze(input_data)
    print("DEBUG: agent.analyze() 完成")

    # 保存结果
    output_dir = Path(config['data_paths']['processed_data'])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "phase1_overview.json"
    agent.save_result(result, str(output_file))

    print(f"\n✅ 结果已保存到: {output_file}")

    return result


def print_summary(result):
    """打印分析结果摘要"""
    print("\n📈 分析结果摘要:")
    print("-" * 60)

    print(f"识别的领域: {len(result.get('domains', []))}")
    for domain in result.get('domains', []):
        print(f"  - {domain.get('name')}: {domain.get('paper_count', 0)} 篇")

    print(f"\n研究热点: {len(result.get('research_hotspots', []))}")
    for hotspot in result.get('research_hotspots', [])[:5]:
        print(f"  - {hotspot.get('topic')}: {hotspot.get('frequency')} 次")

    print(f"\nTop 文献: {len(result.get('top_papers', []))}")
    for paper in result.get('top_papers', [])[:3]:
        title = paper.get('title', '')
        # ⭐ 处理特殊字符
        try:
            safe_title = title.encode('gbk', errors='replace').decode('gbk')
        except:
            safe_title = title[:60] + '...'
        print(f"  - {safe_title[:60]}... (评分: {paper.get('score', 0):.2f})")


def main():
    """主函数"""
    import sys  # ⭐ 确保能立即输出

    print("=" * 60, flush=True)  # ⭐ 添加 flush=True
    print("🔍 Phase 1: 概览分析".center(60), flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    # ⭐ 添加调试信息
    print("DEBUG: 脚本开始执行", flush=True)
    sys.stdout.flush()  # ⭐ 强制刷新

    try:
        # 加载配置
        print("DEBUG: 开始加载配置...", flush=True)
        sys.stdout.flush()
        config = load_config()
        print("DEBUG: 配置加载完成", flush=True)
        sys.stdout.flush()

        # 准备数据
        print("DEBUG: 开始准备数据...", flush=True)
        sys.stdout.flush()
        agent_summaries = prepare_agent_summaries(config)
        print("DEBUG: 数据准备完成", flush=True)
        sys.stdout.flush()

        # 执行分析
        print("DEBUG: 开始执行分析...", flush=True)
        sys.stdout.flush()
        result = run_overview_analysis(config, agent_summaries)
        print("DEBUG: 分析完成", flush=True)
        sys.stdout.flush()

        # 打印摘要
        print_summary(result)

        print()
        print("=" * 60, flush=True)
        print("✅ Phase 1 完成！", flush=True)
        print("=" * 60, flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()


if __name__ == "__main__":
    main()
