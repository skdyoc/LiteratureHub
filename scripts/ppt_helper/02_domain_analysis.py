"""
Phase 2: 领域深度分析脚本

职责：针对每个领域深度分析，必须读取原始 full.md

⚠️ 关键：所有分析结论必须引用原文，禁止编造！
"""

import sys
import io
import yaml
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

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


def load_phase1_result(config):
    """加载 Phase 1 结果"""
    result_file = Path(config['data_paths']['processed_data']) / "phase1_overview.json"

    if not result_file.exists():
        print(f"❌ Phase 1 结果不存在: {result_file}")
        print("请先运行: python scripts/01_overview.py")
        sys.exit(1)

    with open(result_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_domain_paper_ids(domain_name: str, phase1_result: Dict[str, Any]) -> List[str]:
    """获取指定领域的论文 ID 列表"""
    # 从 Phase 1 结果中查找领域
    domains = phase1_result.get('domains', [])

    target_domain = None
    for domain in domains:
        if domain.get('name') == domain_name:
            target_domain = domain
            break

    if not target_domain:
        print(f"❌ 未找到领域: {domain_name}")
        print("可用的领域:")
        for domain in domains:
            print(f"  - {domain.get('name')}")
        return []

    # 返回该领域的论文 ID
    return target_domain.get('key_papers', [])


def read_full_md_contents(config, paper_ids: List[str]) -> Dict[str, str]:
    """读取所有 full.md 内容"""
    from src.ppt_helper.readers.full_md_reader import FullMdReader

    print(f"\n📖 读取 {len(paper_ids)} 篇文献的 full.md...")

    reader = FullMdReader()
    contents = {}
    success_count = 0

    for i, paper_id in enumerate(paper_ids, 1):
        # 定位 full.md 文件
        markdown_path = Path(config['data_paths']['source_markdowns']) / paper_id / "full.md"

        if not markdown_path.exists():
            print(f"  ⚠️ [{i}/{len(paper_ids)}] {paper_id}: 文件不存在")
            continue

        # 读取内容
        content = reader.read_full_md(str(markdown_path))

        if content:
            contents[paper_id] = content
            success_count += 1
            print(f"  ✅ [{i}/{len(paper_ids)}] {paper_id}: {len(content)} 字符")
        else:
            print(f"  ❌ [{i}/{len(paper_ids)}] {paper_id}: 读取失败")

    print(f"\n📊 成功读取: {success_count}/{len(paper_ids)} 篇")

    return contents


def read_agent_results_json(config, paper_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    读取所有论文的 agent_results JSON（5 个子智能体的输出）

    Args:
        config: 配置对象
        paper_ids: 论文 ID 列表

    Returns:
        字典 {paper_id: {"motivation": {...}, "innovation": {...}, ...}}
    """
    print(f"\n📦 读取 {len(paper_ids)} 篇文献的 agent_results JSON...")

    agent_results_path = Path(config['data_paths']['agent_results'])
    all_results = {}
    success_count = 0

    # 5 个 JSON 文件名
    json_files = [
        "motivation.json",
        "innovation.json",
        "mechanism.json",
        "impact.json",
        "roadmap.json"
    ]

    for i, paper_id in enumerate(paper_ids, 1):
        paper_dir = agent_results_path / paper_id

        if not paper_dir.exists():
            print(f"  ⚠️ [{i}/{len(paper_ids)}] {paper_id}: 目录不存在")
            continue

        paper_results = {}
        json_count = 0

        # 读取 5 个 JSON
        for json_name in json_files:
            json_file = paper_dir / json_name

            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 提取 result 字段（如果存在）
                    if isinstance(data, dict) and "result" in data:
                        result = data["result"]
                        # 如果 result 是字符串（JSON 格式），需要解析
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except:
                                result = {}
                        paper_results[json_name.replace(".json", "")] = result
                    else:
                        paper_results[json_name.replace(".json", "")] = data

                    json_count += 1
                except Exception as e:
                    print(f"  ⚠️ [{i}/{len(paper_ids)}] {paper_id}: {json_name} 读取失败 - {e}")

        if paper_results:
            all_results[paper_id] = paper_results
            success_count += 1
            print(f"  ✅ [{i}/{len(paper_ids)}] {paper_id}: {json_count}/5 个 JSON")
        else:
            print(f"  ❌ [{i}/{len(paper_ids)}] {paper_id}: 未读取到任何 JSON")

    print(f"\n📊 成功读取: {success_count}/{len(paper_ids)} 篇")

    return all_results


def load_agent_results(config, paper_ids: List[str]) -> Dict[str, Any]:
    """加载 agent_results"""
    from src.ppt_helper.workers.content_extractor import ContentExtractor

    print(f"\n📦 加载 agent_results...")

    extractor = ContentExtractor(
        agent_results_path=config['data_paths']['agent_results']
    )

    summaries = extractor.extract_all_summaries(paper_ids)

    print(f"✅ 加载了 {len(summaries)} 篇的 agent_results")

    return summaries


def run_domain_analysis(config, domain_name: str, paper_ids: List[str],
                       full_md_contents: Dict[str, str], agent_results: Dict[str, Any],
                       agent_results_json: Dict[str, Dict[str, Any]]):
    """
    执行领域分析

    Args:
        config: 配置对象
        domain_name: 领域名称
        paper_ids: 论文 ID 列表
        full_md_contents: full.md 内容映射
        agent_results: agent_results 摘要（保留向后兼容）
        agent_results_json: 完整的 agent_results JSON（5 个子智能体输出）
    """
    from src.ppt_helper.agents.domain_analyzer_agent import DomainAnalyzerAgent

    print(f"\n🤖 Phase 2: 领域深度分析 - {domain_name}")
    print("-" * 60)

    # 初始化 Agent
    agent = DomainAnalyzerAgent(
        keys_file="config/api_keys.txt",
        model=config['api']['model']
    )

    # ⭐ 加载完整的 Phase 1 结果
    phase1_file = Path(config['data_paths']['processed_data']) / "phase1_overview.json"
    phase1_data = None

    if phase1_file.exists():
        with open(phase1_file, 'r', encoding='utf-8') as f:
            phase1_data = json.load(f)
        print(f"✅ 已加载 Phase 1 结果")
    else:
        print(f"⚠️  未找到 Phase 1 结果，将使用基础分析")

    # ⭐ 提取该领域相关的 Phase 1 数据
    domain_description = ""
    related_hotspots = []
    time_trends = {}
    top_papers = []

    if phase1_data:
        # 获取领域描述
        for domain in phase1_data.get('domains', []):
            if domain.get('name') == domain_name:
                domain_description = domain.get('description', '')
                break

        # ⭐ 提取相关的研究热点（包含该领域关键词的热点）
        all_hotspots = phase1_data.get('research_hotspots', [])
        for hotspot in all_hotspots:
            hotspot_papers = hotspot.get('papers', [])
            # 检查热点的文献是否在当前领域的文献列表中
            if any(pid in paper_ids for pid in hotspot_papers):
                related_hotspots.append(hotspot)

        # ⭐ 获取时间趋势
        time_trends = phase1_data.get('time_trends', {})

        # ⭐ 获取 Top 论文
        top_papers = phase1_data.get('top_papers', [])
        # 只保留该领域的论文
        top_papers = [p for p in top_papers if p.get('paper_id') in paper_ids]

    print(f"  - 相关研究热点: {len(related_hotspots)} 个")
    print(f"  - 高影响力文献: {len(top_papers)} 篇")
    print(f"  - agent_results JSON: {len(agent_results_json)} 篇")

    # 准备输入数据
    input_data = {
        "domain_name": domain_name,
        "domain_description": domain_description,
        "paper_ids": paper_ids,
        "full_md_contents": full_md_contents,
        # ⭐ 传递完整的 agent_results JSON（5 个子智能体输出）
        "agent_results_json": agent_results_json,
        # ⭐ 传递 Phase 1 的上下文数据
        "phase1_context": {
            "related_hotspots": related_hotspots,
            "time_trends": time_trends,
            "top_papers": top_papers,
        } if phase1_data else None,
    }

    # ⭐ 调用 AI 分析
    print(f"\n🤖 调用 {config['api']['model']} API 进行深度分析...")
    result = agent.analyze(input_data)

    return result


def save_domain_result(config, domain_name: str, result: Dict[str, Any]):
    """保存领域分析结果"""
    output_dir = Path(config['data_paths']['domain_results']) / domain_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "domain_analysis.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已保存到: {output_file}")


def list_domains(phase1_result: Dict[str, Any]):
    """列出所有可用领域"""
    print("📚 可用领域:")
    print("-" * 60)

    domains = phase1_result.get('domains', [])

    for i, domain in enumerate(domains, 1):
        name = domain.get('name', 'Unknown')
        count = domain.get('paper_count', 0)
        description = domain.get('description', '')

        print(f"{i}. {name}")
        print(f"   文献数: {count}")
        print(f"   描述: {description}")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Phase 2: 领域深度分析")
    parser.add_argument('--domain', type=str, help='领域名称')
    parser.add_argument('--list', action='store_true', help='列出所有可用领域')
    parser.add_argument('--all', action='store_true', help='分析所有领域')
    parser.add_argument('--max-papers', type=int, default=10,
                       help='⭐ full.md 最多读取的文献数（默认: 10，因为 full.md 很大）')
    parser.add_argument('--max-agent-results', type=int, default=50,
                       help='⭐ agent_results JSON 最多读取的文献数（默认: 50，因为 JSON 较小）')

    args = parser.parse_args()

    print("=" * 60)
    print("🔬 Phase 2: 领域深度分析".center(60))
    print("=" * 60)
    print()

    # 加载配置
    config = load_config()

    # 加载 Phase 1 结果
    phase1_result = load_phase1_result(config)

    # 列出领域
    if args.list:
        list_domains(phase1_result)
        return

    # 检查是否分析所有领域
    if args.all:
        analyze_all_domains(config, phase1_result, args.max_papers, args.max_agent_results)
        return

    # 检查是否指定了领域
    if not args.domain:
        print("请使用 --domain 指定要分析的领域")
        print("或使用 --list 查看所有可用领域")
        print("或使用 --all 分析所有领域")
        print()
        print("示例:")
        print("  python scripts/02_domain_analysis.py --list")
        print("  python scripts/02_domain_analysis.py --domain '叶片气动优化'")
        print("  python scripts/02_domain_analysis.py --all")
        return

    domain_name = args.domain

    # 获取领域的论文 ID（所有可用文献）
    all_paper_ids = get_domain_paper_ids(domain_name, phase1_result)

    if not all_paper_ids:
        return

    print(f"📚 领域: {domain_name}")
    print(f"📄 总文献数: {len(all_paper_ids)}")

    # ⭐ 分别限制 full.md 和 agent_results 的文献数量
    # full.md 文件很大，严格限制
    max_full_md = args.max_papers

    # agent_results JSON 较小，可以宽松限制
    max_agent_results = args.max_agent_results
    agent_results_paper_ids = all_paper_ids[:max_agent_results]

    # ⭐ 特殊处理：如果 max_papers = 0，跳过 full.md
    if max_full_md == 0:
        print(f"  ⚠️  full.md 跳过（max_papers = 0）")
        print(f"  - agent_results JSON 读取: {len(agent_results_paper_ids)} 篇（限制: {max_agent_results}）")
        print(f"  ℹ️  将只使用 agent_results JSON 进行分析")

        # 不读取 full.md
        full_md_paper_ids = []
        full_md_contents = {}

        # 加载 agent_results（使用 agent_results 的 paper_ids）
        agent_results = load_agent_results(config, agent_results_paper_ids)

        # ⭐ 读取完整的 agent_results JSON（宽松限制）
        agent_results_json = read_agent_results_json(config, agent_results_paper_ids)

        # 执行分析（使用 agent_results 的 paper_ids，full.md 为空）
        result = run_domain_analysis(
            config, domain_name, agent_results_paper_ids,  # ⭐ 使用 agent_results 的 paper_ids
            full_md_contents, agent_results, agent_results_json
        )
    else:
        # 正常流程：读取 full.md
        full_md_paper_ids = all_paper_ids[:max_full_md]

        print(f"  - full.md 读取: {len(full_md_paper_ids)} 篇（限制: {max_full_md}）")
        print(f"  - agent_results JSON 读取: {len(agent_results_paper_ids)} 篇（限制: {max_agent_results}）")

        # 读取 full.md（严格限制）
        full_md_contents = read_full_md_contents(config, full_md_paper_ids)

        if not full_md_contents:
            print("❌ 没有成功读取任何 full.md，无法继续")
            return

        # 加载 agent_results（简化摘要，使用 full_md 的 paper_ids）
        agent_results = load_agent_results(config, full_md_paper_ids)

        # ⭐ 读取完整的 agent_results JSON（宽松限制）
        agent_results_json = read_agent_results_json(config, agent_results_paper_ids)

        # 执行分析（使用 full.md 的 paper_ids）
        result = run_domain_analysis(
            config, domain_name, full_md_paper_ids,  # ⭐ 使用 full_md 的 paper_ids
            full_md_contents, agent_results, agent_results_json
        )

    # 保存结果
    save_domain_result(config, domain_name, result)

    print()
    print("=" * 60)
    print("✅ Phase 2 完成！")
    print("=" * 60)


def analyze_all_domains(config, phase1_result: Dict[str, Any], max_papers: int, max_agent_results: int):
    """分析所有领域

    Args:
        config: 配置对象
        phase1_result: Phase 1 结果
        max_papers: full.md 最多读取的文献数
        max_agent_results: agent_results JSON 最多读取的文献数
    """
    domains = phase1_result.get('domains', [])

    if not domains:
        print("❌ 没有找到任何领域")
        return

    print(f"📚 共找到 {len(domains)} 个领域")
    print(f"⚙️  full.md 限制: {max_papers} 篇")
    print(f"⚙️  agent_results JSON 限制: {max_agent_results} 篇")
    print()

    results_summary = []

    for i, domain in enumerate(domains, 1):
        domain_name = domain.get('name', 'Unknown')

        print("=" * 60)
        print(f"[{i}/{len(domains)}] 分析领域: {domain_name}")
        print("=" * 60)

        # 获取领域的论文 ID（所有可用文献）
        all_paper_ids = domain.get('all_papers', domain.get('key_papers', []))

        if not all_paper_ids:
            print(f"⚠️  跳过 {domain_name}（没有文献）")
            results_summary.append({
                "domain": domain_name,
                "status": "skipped",
                "reason": "没有文献"
            })
            print()
            continue

        # ⭐ 分别限制 full.md 和 agent_results 的文献数量
        # agent_results JSON 较小，可以宽松限制
        agent_results_paper_ids = all_paper_ids[:max_agent_results]

        # ⭐ 特殊处理：如果 max_papers = 0，跳过 full.md
        if max_papers == 0:
            print(f"📚 领域: {domain_name}")
            print(f"📄 总文献数: {len(all_paper_ids)}")
            print(f"  ⚠️  full.md 跳过（max_papers = 0）")
            print(f"  - agent_results JSON 读取: {len(agent_results_paper_ids)} 篇（限制: {max_agent_results}）")
            print(f"  ℹ️  将只使用 agent_results JSON 进行分析")
            print()

            try:
                # 不读取 full.md
                full_md_paper_ids = []
                full_md_contents = {}

                # 加载 agent_results（使用 agent_results 的 paper_ids）
                agent_results = load_agent_results(config, agent_results_paper_ids)

                # ⭐ 读取完整的 agent_results JSON（宽松限制）
                agent_results_json = read_agent_results_json(config, agent_results_paper_ids)

                # 执行分析（使用 agent_results 的 paper_ids，full.md 为空）
                result = run_domain_analysis(
                    config, domain_name, agent_results_paper_ids,  # ⭐ 使用 agent_results 的 paper_ids
                    full_md_contents, agent_results, agent_results_json
                )

                # 保存结果
                save_domain_result(config, domain_name, result)

                print(f"✅ {domain_name} 分析完成")
                results_summary.append({
                    "domain": domain_name,
                    "status": "success",
                    "paper_count": len(agent_results_paper_ids)  # 记录 agent_results 的数量
                })

            except Exception as e:
                print(f"❌ {domain_name} 分析失败: {e}")
                results_summary.append({
                    "domain": domain_name,
                    "status": "error",
                    "error": str(e)
                })

            print()
            continue

        # 正常流程：读取 full.md
        # full.md 文件很大，严格限制
        full_md_paper_ids = all_paper_ids[:max_papers]

        print(f"  - full.md 读取: {len(full_md_paper_ids)} 篇（限制: {max_papers}）")
        print(f"  - agent_results JSON 读取: {len(agent_results_paper_ids)} 篇（限制: {max_agent_results}）")
        print(f"📚 领域: {domain_name}")
        print(f"📄 总文献数: {len(all_paper_ids)}")
        print()

        try:
            # 读取 full.md（严格限制）
            full_md_contents = read_full_md_contents(config, full_md_paper_ids)

            if not full_md_contents:
                print(f"❌ {domain_name}: 没有成功读取任何文献")
                results_summary.append({
                    "domain": domain_name,
                    "status": "failed",
                    "reason": "无法读取文献"
                })
                print()
                continue

            # 加载 agent_results（简化摘要，使用 full_md 的 paper_ids）
            agent_results = load_agent_results(config, full_md_paper_ids)

            # ⭐ 读取完整的 agent_results JSON（宽松限制）
            agent_results_json = read_agent_results_json(config, agent_results_paper_ids)

            # 执行分析（使用 full_md 的 paper_ids）
            result = run_domain_analysis(
                config, domain_name, full_md_paper_ids,
                full_md_contents, agent_results, agent_results_json
            )

            # 保存结果
            save_domain_result(config, domain_name, result)

            print(f"✅ {domain_name} 分析完成")
            results_summary.append({
                "domain": domain_name,
                "status": "success",
                "paper_count": len(full_md_paper_ids)
            })

        except Exception as e:
            print(f"❌ {domain_name} 分析失败: {e}")
            results_summary.append({
                "domain": domain_name,
                "status": "error",
                "error": str(e)
            })

        print()

    # 打印总结
    print("=" * 60)
    print("📊 分析总结".center(60))
    print("=" * 60)
    print()

    success_count = sum(1 for r in results_summary if r.get('status') == 'success')
    failed_count = sum(1 for r in results_summary if r.get('status') in ['failed', 'error'])

    print(f"总计领域: {len(domains)}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failed_count}")

    print()
    print("详细结果:")
    for r in results_summary:
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'error': '❌',
            'skipped': '⏭️ '
        }.get(r.get('status'), '❓')

        print(f"  {status_emoji} {r['domain']}: {r.get('status', 'unknown')}")

    print()
    print("=" * 60)
    print("✅ Phase 2（所有领域）完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
