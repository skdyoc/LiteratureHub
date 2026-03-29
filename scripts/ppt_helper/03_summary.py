"""
Phase 3: 综合总结脚本

职责：将 Phase 1 概览和 Phase 2 领域分析综合成完整的博士论文汇报 PPT
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


def run_summary_analysis(config):
    """执行综合总结分析"""
    from src.ppt_helper.agents.summary_agent import SummaryAgent

    print("\n📊 Phase 3: 综合总结（总）")
    print("-" * 60)

    # 初始化 Agent
    print("DEBUG: 初始化 SummaryAgent...")
    agent = SummaryAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )
    print("DEBUG: SummaryAgent 初始化完成")

    # 准备输入数据
    phase1_path = Path(config['data_paths']['processed_data']) / "phase1_overview.json"
    domain_results_dir = Path(config['data_paths']['domain_results'])
    agent_results_path = Path(config['data_paths']['source_agent_results'])

    # 检查文件是否存在
    if not phase1_path.exists():
        print(f"❌ Phase 1 结果不存在: {phase1_path}")
        print("💡 请先运行 Phase 1: python scripts/ppt_helper/01_overview.py")
        return None

    if not domain_results_dir.exists():
        print(f"❌ Phase 2 结果目录不存在: {domain_results_dir}")
        print("💡 请先运行 Phase 2: python scripts/ppt_helper/02_domain_analysis.py")
        return None

    print(f"DEBUG: Phase 1 路径: {phase1_path}")
    print(f"DEBUG: Phase 2 目录: {domain_results_dir}")
    print(f"DEBUG: agent_results 路径: {agent_results_path}")

    # 准备输入数据
    input_data = {
        "phase1_path": str(phase1_path),
        "domain_results_dir": str(domain_results_dir),
        "agent_results_path": str(agent_results_path),
        "max_key_papers": 20,  # 加载 Top 20 论文的详细分析
    }

    print(f"DEBUG: input_data 准备完成")

    # 执行分析
    print("DEBUG: 开始调用 agent.analyze()...")
    result = agent.analyze(input_data)
    print("DEBUG: agent.analyze() 完成")

    # 保存结果
    output_dir = Path(config['data_paths']['processed_data'])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "final_ppt_content.json"
    agent.save_result(result, str(output_file))

    print(f"\n✅ 结果已保存到: {output_file}")

    return result


def print_summary(result):
    """打印分析结果摘要"""
    if not result:
        return

    print("\n📈 分析结果摘要:")
    print("-" * 60)

    ppt_content = result.get('ppt_content', {})

    print(f"\n生成幻灯片:")
    total_slides = 0
    for part_name, part_data in ppt_content.items():
        title = part_data.get('title', 'Unknown')
        slides = part_data.get('slides', [])
        slide_count = len(slides)
        total_slides += slide_count
        print(f"  {title}: {slide_count} 页")

    print(f"\n总页数: {total_slides}")

    # 显示摘要
    summary = result.get('summary', '')
    if summary:
        print(f"\n整体总结:")
        print(summary[:300] + "..." if len(summary) > 300 else summary)


def main():
    """主函数"""
    import sys  # 确保能立即输出

    print("=" * 60, flush=True)
    print("📊 Phase 3: 综合总结".center(60), flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    # 添加调试信息
    print("DEBUG: 脚本开始执行", flush=True)
    sys.stdout.flush()

    try:
        # 加载配置
        print("DEBUG: 开始加载配置...", flush=True)
        sys.stdout.flush()
        config = load_config()
        print("DEBUG: 配置加载完成", flush=True)
        sys.stdout.flush()

        # 执行分析
        print("DEBUG: 开始执行分析...", flush=True)
        sys.stdout.flush()
        result = run_summary_analysis(config)
        print("DEBUG: 分析完成", flush=True)
        sys.stdout.flush()

        # 打印摘要
        print_summary(result)

        print()
        print("=" * 60, flush=True)
        print("✅ Phase 3 完成！", flush=True)
        print("=" * 60, flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()


if __name__ == "__main__":
    main()
