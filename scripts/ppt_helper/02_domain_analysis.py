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
# 添加项目根目录到路径（LiteratureHub/）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_config():
    """加载配置文件"""
    config_file = Path("config/ppt_helper/config.yaml")
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

    # ⭐ 使用 categories 模式的路径（因为从分类文献分析来的）
    base_dir = Path(config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub'))
    markdowns_path = base_dir / "data/projects/wind_aero/markdown/categories/大型风力机气动"

    for i, paper_id in enumerate(paper_ids, 1):
        # 定位 full.md 文件
        markdown_path = markdowns_path / paper_id / "full.md"

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

    # ⭐ 使用 categories 模式的路径（因为从分类文献分析来的）
    base_dir = Path(config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub'))
    agent_results_path = base_dir / "data/agent_results/categories/大型风力机气动"

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

    # 获取 base_dir 和模式
    base_dir = config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub')

    # 检查是否是 categories 模式
    # 这里我们假设使用 categories 模式，因为是从分类文献分析来的
    extractor = ContentExtractor(
        base_dir=base_dir,
        mode="categories",
        category="大型风力机气动"
    )

    summaries = extractor.extract_all_agent_results(paper_ids)

    print(f"✅ 加载了 {len(summaries)} 篇的 agent_results")

    return summaries


def run_domain_analysis(config, domain_name: str, paper_ids: List[str],
                       full_md_contents: Dict[str, str], agent_results: Dict[str, Any],
                       agent_results_json: Dict[str, Dict[str, Any]]):
    """
    执行领域分析（使用 Claude Code Agent，绕过 API）

    Args:
        config: 配置对象
        domain_name: 领域名称
        paper_ids: 论文 ID 列表
        full_md_contents: full.md 内容映射
        agent_results: agent_results 摘要（保留向后兼容）
        agent_results_json: 完整的 agent_results JSON（5 个子智能体输出）
    """
    import subprocess

    print(f"\n🤖 Phase 2: 领域深度分析 - {domain_name}")
    print("-" * 60)

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
    print(f"  - full.md 内容: {len(full_md_contents)} 篇")

    # ⭐ 准备工作目录
    base_dir = Path(config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub'))
    workspace_dir = base_dir / "agent_workspace" / "phase2_domain_analysis" / domain_name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # ⭐ 保存 full.md 内容摘要（因为 full.md 太大，只保存关键部分）
    full_md_summary_file = workspace_dir / "full_md_summary.txt"
    with open(full_md_summary_file, 'w', encoding='utf-8') as f:
        f.write(f"# 领域: {domain_name}\n")
        f.write(f"# 文献数: {len(full_md_contents)}\n\n")
        for paper_id, content in full_md_contents.items():
            # 只保存前 2000 字符（通常包含摘要和引言）
            summary = content[:2000] if len(content) > 2000 else content
            f.write(f"## [{paper_id}]\n")
            f.write(f"{summary}\n")
            f.write(f"\n{'='*60}\n\n")
    print(f"  ✓ full.md 摘要已保存: {full_md_summary_file}")

    # ⭐ 保存 agent_results JSON
    agent_results_file = workspace_dir / "agent_results.json"
    with open(agent_results_file, 'w', encoding='utf-8') as f:
        json.dump(agent_results_json, f, ensure_ascii=False, indent=2)
    print(f"  ✓ agent_results 已保存: {agent_results_file}")

    # ⭐ 保存 Phase 1 上下文
    phase1_context_file = workspace_dir / "phase1_context.json"
    with open(phase1_context_file, 'w', encoding='utf-8') as f:
        json.dump({
            "domain_name": domain_name,
            "domain_description": domain_description,
            "related_hotspots": related_hotspots,
            "top_papers": top_papers,
        }, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Phase 1 上下文已保存: {phase1_context_file}")

    # ⭐ 构造 Claude Code Agent Prompt（更直接的指令）
    agent_prompt = f"""EXECUTE ANALYSIS TASK - PHASE 2 DOMAIN DEEP ANALYSIS

DOMAIN: {domain_name}
DESCRIPTION: {domain_description}

INPUT FILES (READ THESE FILES):
1. {full_md_summary_file.name} - {len(full_md_contents)} papers' full.md summaries
2. {agent_results_file.name} - Complete agent_results JSON (5 sub-agents' outputs)
3. {phase1_context_file.name} - Phase 1 context data

CONTEXT:
- Related hotspots: {len(related_hotspots)}
- High-impact papers: {len(top_papers)}

TASK: Execute domain deep analysis and output ONLY JSON

ANALYSIS SECTIONS:
1. Domain Overview - core research questions, key challenges, positioning
2. Technical Roadmap - timeline of major developments and milestones
3. Key Innovations - major innovations and their impact
4. Methods & Tools - primary research methods and tools
5. Representative Work - foundational and breakthrough papers
6. Gaps & Future - current limitations and future directions

OUTPUT REQUIREMENTS:
- OUTPUT ONLY PURE JSON (no markdown, no conversational text)
- Save to: {workspace_dir / "domain_analysis.json"}
- JSON format:
{{
  "domain_overview": {{"core_research_questions": ["question1", "question2"], "key_challenges": ["challenge1"], "positioning": "description"}},
  "technical_roadmap": [{{"year": 2018, "milestone": "milestone", "description": "description"}}],
  "key_innovations": [{{"innovation": "innovation", "impact": "impact", "related_papers": ["paper_id"]}}],
  "methods_and_tools": {{"primary_methods": ["method1", "method2"], "tools": ["tool1"], "comparison": "comparison"}},
  "representative_work": [{{"paper_id": "id", "title": "title", "reason": "reason", "contribution": "contribution"}}],
  "gaps_and_future": {{"limitations": ["limitation1"], "future_directions": ["direction1"], "interdisciplinary_opportunities": ["opportunity1"]}},
  "analysis_summary": {{"total_papers_analyzed": {len(full_md_contents)}, "key_findings": ["finding1"], "recommendations": ["recommendation1"]}}
}}

CRITICAL: OUTPUT ONLY JSON - NO MARKDOWN, NO CONVERSATIONAL TEXT
"""

    # ⭐ 调用 Claude Code CLI
    print("\n" + "=" * 60)
    print("🤖 正在调用 Claude Code Agent...")
    print("=" * 60)

    try:
        # 构造命令（Windows 上需要 shell=True 来执行 .cmd 文件）
        cmd = [
            "claude",
            "--model", "sonnet",
            "--add-dir", str(workspace_dir),
            "--allowedTools", "Read,Write,Edit",
            "-p", agent_prompt
        ]

        print(f"命令: {' '.join(cmd)}")
        print()

        # 执行命令（Windows 需要 shell=True）
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=3600,  # 1小时超时
            shell=True  # ⭐ Windows 上需要 shell=True 来执行 .cmd 文件
        )

        # 打印输出
        if result.stdout:
            print("📤 Agent 输出:")
            print("-" * 60)
            print(result.stdout[:1000])  # 只打印前1000字符
            if len(result.stdout) > 1000:
                print(f"\n... (省略 {len(result.stdout) - 1000} 字符)")
            print("-" * 60)

        if result.stderr:
            print("⚠️  Agent 错误输出:")
            print("-" * 60)
            print(result.stderr)
            print("-" * 60)

        # 检查返回码
        if result.returncode != 0:
            print(f"❌ Claude Code Agent 执行失败（返回码: {result.returncode}）")
            return None

        print("✅ Claude Code Agent 执行完成")

    except subprocess.CalledProcessError as e:
        print(f"❌ 调用 Claude Code CLI 失败: {e}")
        return None
    except subprocess.TimeoutExpired:
        print("❌ Claude Code Agent 执行超时（1小时）")
        return None
    except FileNotFoundError:
        print("❌ 找不到 claude 命令！请确保已安装 Claude Code CLI")
        print("   安装方法: npm install -g @anthropic-ai/claude-code")
        return None
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return None

    # ⭐ 加载 Agent 输出
    output_file = workspace_dir / "domain_analysis.json"
    if not output_file.exists():
        print(f"\n❌ Agent 输出文件不存在: {output_file}")
        print(f"   请检查 Agent 是否正确生成了输出文件")
        return None

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        print(f"\n✅ 成功加载 Agent 输出: {output_file}")
    except json.JSONDecodeError as e:
        print(f"❌ Agent 输出文件 JSON 解析失败: {e}")
        print(f"   请检查输出文件格式是否正确")
        return None

    # ⭐ 保存到最终位置
    output_dir = Path(config['data_paths']['domain_results']) / domain_name
    output_dir.mkdir(parents=True, exist_ok=True)

    final_output_file = output_dir / "domain_analysis.json"
    with open(final_output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 结果已保存到: {final_output_file}")

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
