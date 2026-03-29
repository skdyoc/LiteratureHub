"""
主流程脚本

职责：一键执行完整的总分总分析流程
"""

import sys
import io
import yaml
import json
import time
from pathlib import Path
from datetime import datetime

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


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("  Wind-Aero-Literature-PPT-Helper".center(70))
    print("  风能气动文献 PPT 辅助系统".center(70))
    print("  总分总结构：Phase 1 (总) → Phase 2 (分) → Phase 3 (总)".center(70))
    print("=" * 70)
    print()


def phase_1_overview(config):
    """Phase 1: 概览分析"""
    print("🔍 Phase 1: 概览分析（总）")
    print("-" * 70)

    from src.ppt_helper.workers.content_extractor import ContentExtractor
    from src.ppt_helper.agents.overview_agent import OverviewAgent

    # 准备数据
    print("📊 提取文献摘要...")
    extractor = ContentExtractor(
        agent_results_path=config['data_paths']['source_agent_results']
    )
    paper_ids = extractor.get_available_paper_ids()
    print(f"  找到 {len(paper_ids)} 篇文献")

    summaries = extractor.extract_all_summaries(paper_ids)
    agent_summaries = list(summaries.values())

    # 执行分析
    print("\n🤖 调用 GLM-5 API 进行概览分析...")
    agent = OverviewAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )

    input_data = {
        "agent_results_summaries": agent_summaries,
        "min_domains": config['domain_classification']['min_domains'],
        "max_domains": config['domain_classification']['max_domains']
    }

    result = agent.analyze(input_data)

    # 保存结果
    output_dir = Path(config['data_paths']['processed_data'])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "phase1_overview.json"
    agent.save_result(result, str(output_file))

    print(f"\n✅ Phase 1 完成！")
    print(f"  识别领域: {len(result.get('domains', []))}")
    print(f"  研究热点: {len(result.get('research_hotspots', []))}")
    print(f"  结果保存: {output_file}")
    print()

    return result


def phase_2_domain_analysis(config, phase1_result):
    """Phase 2: 领域深度分析"""
    print("🔬 Phase 2: 领域深度分析（分）")
    print("-" * 70)

    from src.ppt_helper.agents.domain_analyzer_agent import DomainAnalyzerAgent
    from src.ppt_helper.workers.markdown_locator import MarkdownLocator
    from src.ppt_helper.workers.content_extractor import ContentExtractor

    # 获取领域列表
    domains = phase1_result.get('domains', [])

    if not domains:
        print("⚠️  没有找到领域，跳过 Phase 2")
        return {}

    print(f"  找到 {len(domains)} 个领域")
    for i, domain in enumerate(domains, 1):
        print(f"    {i}. {domain.get('name')}")

    # 初始化 Agent
    print("\n🤖 初始化 DomainAnalyzerAgent...")
    agent = DomainAnalyzerAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )

    # 初始化 Workers
    locator = MarkdownLocator(
        markdowns_path=config['data_paths']['source_markdowns']
    )
    extractor = ContentExtractor(
        agent_results_path=config['data_paths']['source_agent_results']
    )

    # 创建输出目录
    output_dir = Path(config['data_paths']['domain_results'])
    output_dir.mkdir(parents=True, exist_ok=True)

    # 分析每个领域
    results = {}
    for i, domain in enumerate(domains, 1):
        domain_name = domain.get('name', 'Unknown')
        domain_description = domain.get('description', '')
        all_papers = domain.get('all_papers', [])
        key_papers = domain.get('key_papers', all_papers[:10])

        print(f"\n[{i}/{len(domains)}] 分析领域: {domain_name}")
        print(f"  描述: {domain_description}")
        print(f"  文献数: {len(all_papers)} (重点: {len(key_papers)})")

        try:
            # 准备输入数据
            input_data = {
                "domain_name": domain_name,
                "domain_description": domain_description,
                "paper_list": key_papers,  # 只分析重点文献
                "full_md_locator": locator,
                "content_extractor": extractor,
                "phase1_context": {
                    "research_hotspots": phase1_result.get('research_hotspots', []),
                    "time_trends": phase1_result.get('time_trends', {}),
                }
            }

            # 执行分析
            result = agent.analyze(input_data)

            # 保存结果
            domain_output_dir = output_dir / domain_name
            domain_output_dir.mkdir(parents=True, exist_ok=True)

            domain_output_file = domain_output_dir / "domain_analysis.json"
            agent.save_result(result, str(domain_output_file))

            print(f"  ✅ 完成: {domain_output_file}")
            results[domain_name] = result

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            continue

    print(f"\n✅ Phase 2 完成！")
    print(f"  成功分析: {len(results)}/{len(domains)} 个领域")
    print(f"  结果目录: {output_dir}")
    print()

    return results


def phase_3_summary(config, phase1_result, phase2_result):
    """Phase 3: 综合总结"""
    print("📊 Phase 3: 综合总结（总）")
    print("-" * 70)

    from src.ppt_helper.agents.summary_agent import SummaryAgent

    # 检查 Phase 2 结果
    if not phase2_result:
        print("⚠️  Phase 2 结果为空，跳过 Phase 3")
        return {}

    print(f"  输入领域数: {len(phase2_result)}")

    # 初始化 Agent
    print("\n🤖 初始化 SummaryAgent...")
    agent = SummaryAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )

    # 准备输入数据
    input_data = {
        "phase1_path": str(Path(config['data_paths']['processed_data']) / "phase1_overview.json"),
        "domain_results_dir": config['data_paths']['domain_results'],
        "agent_results_path": config['data_paths']['source_agent_results'],
        "max_key_papers": 20,
    }

    # 执行分析
    print("\n🤖 调用 GLM-5 API 进行综合总结...")
    result = agent.analyze(input_data)

    # 保存结果
    output_dir = Path(config['data_paths']['processed_data'])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "final_ppt_content.json"
    agent.save_result(result, str(output_file))

    print(f"\n✅ Phase 3 完成！")
    print(f"  结果保存: {output_file}")

    # 显示幻灯片数量
    ppt_content = result.get('ppt_content', {})
    total_slides = 0
    for part_name, part_data in ppt_content.items():
        slides = part_data.get('slides', [])
        slide_count = len(slides)
        total_slides += slide_count
        print(f"  {part_name}: {slide_count} 页")

    print(f"  总幻灯片: {total_slides} 页")
    print()

    return result


def main():
    """主函数"""
    print_banner()

    print("🚀 开始执行完整流程...")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start_time = time.time()

    try:
        # 加载配置
        config = load_config()

        # Phase 1: 概览分析
        phase1_result = phase_1_overview(config)

        # Phase 2: 领域深度分析
        phase2_result = phase_2_domain_analysis(config, phase1_result)

        # Phase 3: 综合总结（传递 phase1_result 和 phase2_result）
        phase3_result = phase_3_summary(config, phase1_result, phase2_result)

        # 完成
        elapsed_time = time.time() - start_time

        print("=" * 70)
        print("✅ 流程执行完成！")
        print(f"总耗时: {elapsed_time:.1f} 秒")
        print("=" * 70)
        print()
        print("📁 输出位置：")
        print(f"   - Phase 1: {config['data_paths']['processed_data']}/phase1_overview.json")
        print(f"   - Phase 2: {config['data_paths']['domain_results']}/")
        print(f"   - Phase 3: {config['data_paths']['processed_data']}/final_ppt_content.json")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
