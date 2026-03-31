"""
Phase 1: 概览分析脚本（LiteratureHub 集成版）

职责：基于 agent_results 生成领域整体概览
支持 all 和 categories 两种模式
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
# 添加项目根目录到路径（LiteratureHub/）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_config():
    """加载配置文件"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / "config" / "ppt_helper" / "config.yaml"

    if not config_file.exists():
        # 尝试相对于脚本位置的配置
        script_dir = Path(__file__).parent
        config_file = script_dir / "config" / "ppt_helper" / "config.yaml"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def prepare_agent_summaries(config, mode="all", category=None):
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

    Args:
        config: 配置字典
        mode: 工作模式，"all" 或 "categories"
        category: 分类名称（仅在 categories 模式下使用）
    """
    from src.ppt_helper.workers.content_extractor import ContentExtractor
    from src.ppt_helper.scoring.paper_scorer import PaperScorer

    print("📊 提取文献摘要...")

    # 获取基础目录
    base_dir = config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub')

    # 初始化提取器
    extractor = ContentExtractor(base_dir=base_dir, mode=mode, category=category)

    # 初始化评分器
    scorer = PaperScorer()

    # 获取所有论文 ID
    paper_ids = extractor.get_available_paper_ids()
    print(f"  ✓ 找到 {len(paper_ids)} 篇文献（{mode} 模式" + (f", 分类: {category}" if category else "") + "）")

    # 处理所有可用文献
    MAX_PAPERS = len(paper_ids)
    print(f"  ⏳ 开始提取摘要（全部 {MAX_PAPERS} 篇）...")

    # 提取所有 agent_results
    all_agent_results = extractor.extract_all_agent_results(paper_ids[:MAX_PAPERS])
    print(f"  ✓ 提取了 {len(all_agent_results)} 篇的 agent_results")

    # 转换为 OverviewAgent 需要的格式
    summaries_list = []
    for paper_id, agent_results in all_agent_results.items():
        # 提取元数据
        metadata = extractor.extract_metadata(paper_id)

        if not metadata:
            print(f"  ⚠️  跳过 {paper_id}: 元数据提取失败")
            continue

        # ⭐ 计算评分（影响因子70% + 时间权重30%）
        score = scorer.calculate_final_score(
            journal=metadata.journal if hasattr(metadata, 'journal') else '',
            year=metadata.year if hasattr(metadata, 'year') else 2020,
            impact_factor=metadata.impact_factor if hasattr(metadata, 'impact_factor') else None
        )

        # 更新元数据的评分
        metadata.score = score

        # 提取 innovation（完整的，不只是计数）
        innovation = agent_results.get("innovation", {})

        # 构造摘要项
        summary_item = {
            "metadata": metadata,
            "innovation_summary": innovation,
            "paper_id": paper_id
        }

        summaries_list.append(summary_item)

    # ⭐ 按评分排序（使用 PaperScorer 计算的评分）
    summaries_list.sort(key=lambda x: x.get("metadata").score if x.get("metadata") and hasattr(x.get("metadata"), 'score') else 0, reverse=True)

    # 统计年份分布
    year_count = {}
    for s in summaries_list:
        metadata = s.get("metadata")
        if metadata and hasattr(metadata, 'year') and metadata.year:
            year_count[metadata.year] = year_count.get(metadata.year, 0) + 1

    print(f"  ✓ 转换为列表: {len(summaries_list)} 项")
    print(f"  📊 文献年份分布:")
    for year in sorted(year_count.keys()):
        print(f"     - {year}年: {year_count[year]} 篇")

    # 显示评分统计
    if summaries_list:
        scores = [s.get("metadata").score for s in summaries_list if s.get("metadata") and hasattr(s.get("metadata"), 'score')]
        if scores:
            print(f"  📊 评分统计: 最高 {max(scores):.2f} | 最低 {min(scores):.2f} | 平均 {sum(scores)/len(scores):.2f}")

    return summaries_list


def run_overview_analysis(config, agent_summaries, mode='all', category=None):
    """执行概览分析（使用 Claude Code Agent，绕过 API）"""
    import subprocess

    print("\n🔍 Phase 1: 概览分析（总）")
    print("-" * 60)

    # 准备输入数据
    min_domains = config['domain_classification']['min_domains']
    max_domains = config['domain_classification']['max_domains']

    print(f"  - agent_summaries: {len(agent_summaries)} 项")
    print(f"  - min_domains: {min_domains}")
    print(f"  - max_domains: {max_domains}")

    # ⭐ 准备摘要文本（直接实现，无需创建 Agent）
    def safe_str(s: str) -> str:
        """安全转换字符串，避免 GBK 编码错误"""
        try:
            return s.encode('gbk', errors='replace').decode('gbk')
        except:
            return s.encode('ascii', errors='replace').decode('ascii')

    formatted = []
    for i, summary in enumerate(agent_summaries, 1):
        metadata = summary.get("metadata")
        innovation = summary.get("innovation_summary") or {}

        if not metadata:
            continue

        paper_id = metadata.paper_id if metadata.paper_id else "Unknown"
        title = metadata.title if metadata.title else "Unknown"
        year = metadata.year if metadata.year else 0
        authors = metadata.authors if metadata.authors else []
        journal = metadata.journal if metadata.journal else ""
        score = metadata.score if metadata.score else 0.0

        # 安全处理所有可能包含特殊字符的字段
        title = safe_str(title)
        journal = safe_str(journal)
        author_str = safe_str(", ".join(authors[:3]))
        if len(authors) > 3:
            author_str += " et al."

        # 提取完整的 innovation 内容
        new_phenomena = innovation.get("new_phenomena", [])
        new_methods = innovation.get("new_methods", [])
        new_objects = innovation.get("new_objects", [])

        np_count = len(new_phenomena) if isinstance(new_phenomena, list) else 0
        nm_count = len(new_methods) if isinstance(new_methods, list) else 0
        no_count = len(new_objects) if isinstance(new_objects, list) else 0

        text = f"""
-[{i}] Paper ID: {paper_id}
   - 标题: {title}
   - 作者: {author_str}
   - 年份: {year}
   - 期刊: {journal}
   - 评分: {score:.2f}
   - 创新点统计: 现象 {np_count}, 方法 {nm_count}, 对象 {no_count}
"""

        # 添加创新点详细信息（前2个）
        if np_count > 0:
            text += f"   - 新现象（前2个）:\n"
            for j, phen in enumerate(new_phenomena[:2], 1):
                if isinstance(phen, dict):
                    name = phen.get("name", "")
                    detailed = phen.get("detailed_description", "")
                    text += f"     {j}. {name}\n"
                    if detailed:
                        text += f"        {detailed[:100]}...\n"

        if nm_count > 0:
            text += f"   - 新方法（前2个）:\n"
            for j, meth in enumerate(new_methods[:2], 1):
                if isinstance(meth, dict):
                    name = meth.get("name", "")
                    detailed = meth.get("detailed_description", "")
                    text += f"     {j}. {name}\n"
                    if detailed:
                        text += f"        {detailed[:100]}...\n"

        formatted.append(text)

    summaries_text = "\n".join(formatted)

    # ⭐ 保存数据和 Prompt 到工作目录
    base_dir = Path(config['data_paths'].get('base_dir', 'D:/xfs/phd/github项目/LiteratureHub'))

    # 根据模式和分类创建相应的工作目录
    if mode == 'categories' and category:
        workspace_dir = base_dir / "agent_workspace" / "phase1_overview" / category
    else:
        workspace_dir = base_dir / "agent_workspace" / "phase1_overview" / "all"

    workspace_dir.mkdir(parents=True, exist_ok=True)

    # 保存摘要文本
    summaries_file = workspace_dir / "agent_summaries.txt"
    with open(summaries_file, 'w', encoding='utf-8') as f:
        f.write(summaries_text)
    print(f"\n  ✓ 摘要已保存: {summaries_file}")

    # 保存参数
    params_file = workspace_dir / "params.json"
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump({
            "min_domains": min_domains,
            "max_domains": max_domains,
            "total_papers": len(agent_summaries),
            "mode": mode,
            "category": category
        }, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 参数已保存: {params_file}")

    # ⭐ 构造 Claude Code Agent Prompt（直接提供完整任务说明）
    agent_prompt = f"""你是一位风能气动领域的文献分析专家。请完成 Phase 1 概览分析任务。

工作目录：{workspace_dir}

任务目标：
分析 350 篇大型风力机气动领域的文献，识别研究领域、提取研究热点、排名高影响力文献。

输入文件：
1. {summaries_file.name} - 文献摘要（包含每篇的元数据、创新点等）
2. {params_file.name} - 分析参数（min_domains=5, max_domains=10）

分析任务：

1. **领域识别**：识别 5-10 个研究领域，基于创新点、研究动机、技术路线
   - 示例领域名称："气动外形优化设计"、"尾流效应建模与控制"、"非定常气动特性研究"

2. **研究热点提取**：提取 Top 10-15 研究热点
   - 统计相似创新点的出现频率
   - 使用简洁的技术术语（2-6个汉字）

3. **Top 文献选择**：选择 Top 20-30 文献
   - 基于评分排序（已计算好）
   - 确保时间覆盖（包含2023-2026年的最新研究）
   - 确保领域覆盖（每个主要领域都有代表）

输出要求：
- 纯 JSON 格式（无 markdown 代码块，无其他文字）
- 保存到：{workspace_dir / "agent_output.json"}
- JSON 结构：
{{
  "domains": [{{"name": "领域名", "description": "描述", "paper_count": 数量, "key_papers": ["id1", "id2"]}}],
  "research_hotspots": [{{"topic": "热点主题", "frequency": 频次, "related_domains": ["领域1"]}}],
  "top_papers": [{{"paper_id": "完整ID", "title": "标题", "score": 评分, "domain": "领域", "innovation_highlights": ["创新点1", "创新点2"], "reason_for_inclusion": "入选理由"}}],
  "analysis_summary": {{"total_papers_analyzed": 350, "dominant_domains": ["领域1", "领域2"], "emerging_trends": ["趋势1"], "research_gaps": ["空白1"]}}
}}

现在请开始分析，读取 {summaries_file.name} 文件并完成分析任务。
"""

    # ⭐ 调用 Claude Code CLI（程序式执行）
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
    output_file = workspace_dir / "agent_output.json"
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

    # 保存到最终位置
    output_dir = Path(config['data_paths']['processed_data'])
    output_dir.mkdir(parents=True, exist_ok=True)

    final_output_file = output_dir / "phase1_overview.json"
    with open(final_output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 结果已保存到: {final_output_file}")

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
        safe_title = title[:60] + '...' if len(title) > 60 else title
        print(f"  - {safe_title} (评分: {paper.get('score', 0):.2f})")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1: 概览分析")
    parser.add_argument('--mode', choices=['all', 'categories'], default='all',
                       help='工作模式：all（全部文献）或 categories（分类文献）')
    parser.add_argument('--category', type=str, default=None,
                       help='分类名称（仅在 categories 模式下使用）')

    args = parser.parse_args()

    print("=" * 60)
    print("🔍 Phase 1: 概览分析".center(60))
    print("=" * 60)
    print(f"模式: {args.mode}" + (f", 分类: {args.category}" if args.category else ""))
    print()

    try:
        # 加载配置
        config = load_config()

        # 准备数据
        agent_summaries = prepare_agent_summaries(config, mode=args.mode, category=args.category)

        # 执行分析
        result = run_overview_analysis(config, agent_summaries, mode=args.mode, category=args.category)

        # 打印摘要
        print_summary(result)

        print()
        print("=" * 60)
        print("✅ Phase 1 完成！")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
