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
# 添加项目根目录到路径（LiteratureHub/）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_config():
    """加载配置文件"""
    config_file = Path("config/ppt_helper/config.yaml")
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

    # ⭐ 使用 01_overview.py 中的 prepare_agent_summaries 函数
    # 它已经集成了评分机制
    import importlib.util
    import sys

    # 动态加载 01_overview.py
    overview_script = Path(__file__).parent / "01_overview.py"
    spec = importlib.util.spec_from_file_location("overview", str(overview_script))
    overview_module = importlib.util.module_from_spec(spec)
    sys.modules["overview"] = overview_module
    spec.loader.exec_module(overview_module)

    # 准备数据（使用评分机制）
    agent_summaries = overview_module.prepare_agent_summaries(config, mode="all")

    # 执行分析
    print("\n🤖 调用 GLM-4.7 API 进行概览分析...")
    from src.ppt_helper.agents.overview_agent import OverviewAgent

    agent = OverviewAgent(
        keys_file=config['api']['keys_file'],
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

    # 获取领域列表
    domains = phase1_result.get('domains', [])

    if not domains:
        print("⚠️  没有找到领域，跳过 Phase 2")
        return {}

    print(f"  找到 {len(domains)} 个领域")
    for i, domain in enumerate(domains, 1):
        print(f"    {i}. {domain.get('name')}")

    print("\n⚠️  Phase 2 需要读取原始 full.md 文件，请确保数据准备完成")

    # TODO: 实现领域深度分析
    # 这里需要：
    # 1. 读取每个领域的 full.md 文件
    # 2. 调用 DomainAnalyzerAgent
    # 3. 保存结果

    print("\n⚠️  Phase 2 尚未完全实现（需要大量 API 调用）")
    print("建议：先使用小数据集测试，或手动指定领域")

    print()

    return {}


def phase_3_summary(config, phase2_result):
    """Phase 3: 综合总结"""
    print("📊 Phase 3: 综合总结（总）")
    print("-" * 70)

    # TODO: 实现综合总结
    # 这里需要：
    # 1. 读取 Phase 2 的所有领域分析结果
    # 2. 调用 SummaryAgent
    # 3. 生成 4 部分 PPT 内容

    print("⚠️  Phase 3 尚未实现（依赖 Phase 2 结果）")

    print()

    return {}


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

        # Phase 3: 综合总结
        phase3_result = phase_3_summary(config, phase2_result)

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
        print(f"   - Phase 3: {config['data_paths']['final_output']}")
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
