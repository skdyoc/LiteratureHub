#!/usr/bin/env python3
"""
Agent 2: Deep Analyzer for Research Gaps
深度分析研究空白 - 从 Agent Results 层提取细化信息
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

class DeepAnalyzer:
    """深度分析器 - 从 Agent Results 提取研究空白"""

    def __init__(self, agent_results_dir: str, agent1_output: str):
        self.agent_results_dir = Path(agent_results_dir)
        self.agent1_data = self._load_agent1_output(agent1_output)

        # 关键词库 (5个维度的搜索关键词)
        self.keywords = {
            'innovation': [
                '但是', '然而', '仍有待', '虽然.*但是', '不过',
                '局限性', '限制', '未解决', '待解决', '不足',
                '缺乏', '缺失', '空白', '挑战', '问题',
                'however', 'but', 'limitation', 'gap', 'challenge',
                'unsolved', 'open issue', 'remaining'
            ],
            'motivation': [
                '需求', '挑战', '限制', '不足', '缺乏',
                '问题', '瓶颈', '困难', '障碍',
                'need', 'demand', 'require', 'lack', 'shortcoming',
                'challenge', 'bottleneck', 'difficult', 'barrier'
            ],
            'mechanism': [
                '不清楚', '未完全阐明', '尚不明确', '依赖经验',
                '未完全理解', '机制不明', '机理.*未',
                'unclear', 'not fully understood', 'poorly understood',
                'mechanism.*unknown', 'remain.*unclear'
            ],
            'roadmap': [
                '未来工作', '进一步研究', '下一步', '待解决',
                'future work', 'further research', 'next step',
                'future study', 'remain to be', 'will be',
                'proposed', '建议', '建议研究'
            ],
            'impact': [
                '有待', '需要验证', '应用前景', '局限性',
                '潜在.*挑战', '实际应用', '工程应用',
                'to be verified', 'needs validation', 'practical application',
                'engineering challenge', 'implementation.*difficulty'
            ]
        }

        # 研究空白分类体系
        self.gap_categories = {
            '理论模型': ['model', 'theory', 'formulation', 'equation', '建模', '模型', '理论'],
            '计算方法': ['computational', 'simulation', 'CFD', 'numerical', '计算', '仿真', '数值'],
            '实验验证': ['experimental', 'validation', 'measurement', 'test', '实验', '验证', '测试'],
            '工程应用': ['application', 'implementation', 'engineering', '工程', '应用', '实施'],
            'AI应用': ['AI', 'machine learning', 'neural network', 'deep learning', '人工智能', '机器学习'],
            '设计优化': ['optimization', 'design', '优化', '设计'],
            '多学科耦合': ['coupling', 'multi-physics', 'multidisciplinary', '耦合', '多物理场'],
            '极端环境': ['extreme', 'icing', 'offshore', 'floating', '极端', '结冰', '海上', '浮式']
        }

    def _load_agent1_output(self, filepath: str) -> dict:
        """加载 Agent 1 的输出"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def analyze(self) -> dict:
        """执行深度分析"""
        print("[Agent 2] Deep Analysis Starting...")

        # Step 1: 扫描 Agent Results
        print("\n[Step 1] Scanning Agent Results...")
        all_findings = self._scan_all_agent_results()

        # Step 2: 与 Agent 1 结果交叉验证
        print("\n[Step 2] Cross-validating with Agent 1...")
        validated_gaps = self._cross_validate_with_agent1(all_findings)

        # Step 3: 跨领域关联分析
        print("\n[Step 3] Cross-domain analysis...")
        cross_domain_analysis = self._perform_cross_domain_analysis(validated_gaps)

        # Step 4: 生成最终输出
        print("\n[Step 4] Generating final output...")
        output = self._generate_output(validated_gaps, cross_domain_analysis)

        return output

    def _scan_all_agent_results(self) -> List[dict]:
        """扫描所有 Agent Results"""
        all_findings = []

        # 获取所有文献目录
        paper_dirs = [d for d in self.agent_results_dir.glob('*/')
                     if d.is_dir() and not d.name.startswith('.')]

        total_papers = len(paper_dirs)
        print(f"   Found {total_papers} papers with Agent Results")

        # 优先处理 Agent 1 识别的候选文献
        candidate_papers = set()
        for paper in self.agent1_data.get('candidate_papers', []):
            # 尝试匹配目录名
            paper_id = paper['paper_id']
            matching_dirs = [d for d in paper_dirs if paper_id in d.name]
            if matching_dirs:
                candidate_papers.add(matching_dirs[0])

        print(f"   {len(candidate_papers)} candidate papers from Agent 1")

        # 抽样策略: 优先分析候选文献 + 每个领域抽样
        processed_count = 0
        for paper_dir in paper_dirs:
            paper_id = paper_dir.name

            # 优先处理候选文献
            if paper_dir in candidate_papers:
                findings = self._analyze_paper(paper_dir, priority='high')
                all_findings.extend(findings)
                processed_count += 1

            # 抽样处理其他文献 (每个领域最多 5 篇)
            elif processed_count < 100:  # 限制总处理数量
                findings = self._analyze_paper(paper_dir, priority='medium')
                if findings:  # 如果发现了研究空白
                    all_findings.extend(findings)
                    processed_count += 1

            if processed_count % 10 == 0:
                print(f"   Processed {processed_count} papers...")

        print(f"   [OK] Analyzed {processed_count} papers")
        print(f"   [INFO] Found {len(all_findings)} research线索")

        return all_findings

    def _analyze_paper(self, paper_dir: Path, priority: str = 'medium') -> List[dict]:
        """分析单篇文献的 Agent Results"""
        findings = []

        # 5个维度的 JSON 文件
        dimensions = ['innovation', 'motivation', 'mechanism', 'roadmap', 'impact']

        for dimension in dimensions:
            json_file = paper_dir / f"{dimension}.json"
            if not json_file.exists():
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 搜索关键词
                dimension_findings = self._extract_findings_from_dimension(
                    paper_dir.name, dimension, data, priority
                )
                findings.extend(dimension_findings)

            except Exception as e:
                print(f"   [WARNING] Failed to read {json_file.name}: {e}")
                continue

        return findings

    def _extract_findings_from_dimension(
        self, paper_id: str, dimension: str, data: dict, priority: str
    ) -> List[dict]:
        """从单个维度提取研究发现"""
        findings = []
        keywords = self.keywords.get(dimension, [])

        # 将 data 转换为文本
        text = json.dumps(data, ensure_ascii=False)

        # 搜索关键词
        for keyword in keywords:
            # 使用正则表达式搜索
            pattern = re.compile(keyword, re.IGNORECASE)
            matches = pattern.finditer(text)

            for match in matches:
                # 提取上下文 (前后 50 个字符)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                # 过滤掉无意义的上下文
                if len(context) < 20:
                    continue

                # 分类研究空白
                category = self._classify_gap(context)

                finding = {
                    'paper_id': paper_id,
                    'dimension': dimension,
                    'keyword': keyword,
                    'context': context,
                    'category': category,
                    'priority': priority,
                    'confidence': self._calculate_confidence(context, dimension)
                }

                findings.append(finding)

        return findings

    def _classify_gap(self, text: str) -> str:
        """分类研究空白"""
        scores = {}
        for category, keywords in self.gap_categories.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    score += 1
            scores[category] = score

        # 返回得分最高的分类
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return '其他'

    def _calculate_confidence(self, context: str, dimension: str) -> str:
        """计算置信度"""
        # 高置信度: 多个关键词同时出现
        keyword_count = sum(1 for kw in self.keywords[dimension]
                          if kw.lower() in context.lower())

        if keyword_count >= 2:
            return 'high'
        elif keyword_count == 1:
            return 'medium'
        else:
            return 'low'

    def _cross_validate_with_agent1(self, all_findings: List[dict]) -> List[dict]:
        """与 Agent 1 的结果交叉验证"""
        validated_gaps = []

        # Agent 1 的初步空白
        preliminary_gaps = self.agent1_data.get('preliminary_gaps', [])

        # 将 Agent 1 的空白转换为可搜索的模式
        for gap in preliminary_gaps:
            gap_title = gap['title']
            gap_desc = gap['description']
            gap_category = gap['category']

            # 在 Agent Results 中寻找证据
            supporting_findings = []
            for finding in all_findings:
                # 改进的匹配策略:
                # 1. 检查分类是否匹配
                category_match = (gap_category == finding['category'])

                # 2. 检查关键词相关性
                # 提取 gap_desc 的关键术语
                gap_keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', gap_desc)
                gap_keywords = [kw for kw in gap_keywords if len(kw) >= 2]

                context_lower = finding['context'].lower()
                keyword_matches = sum(1 for kw in gap_keywords if kw.lower() in context_lower)

                # 3. 综合判断
                if category_match or keyword_matches >= 2:
                    supporting_findings.append(finding)

            if supporting_findings:
                # 整合证据
                validated_gap = {
                    'id': f"gap_{len(validated_gaps)+1:03d}",
                    'title': gap_title,
                    'category': gap_category,
                    'detailed_description': self._generate_detailed_description(
                        gap_desc, supporting_findings
                    ),
                    'agent_dimensions': self._extract_dimension_evidence(supporting_findings),
                    'sources': {
                        'phase_level': gap.get('sources', []),
                        'agent_results': [f['paper_id'] for f in supporting_findings[:5]]
                    },
                    'relevance': gap.get('relevance', '中'),
                    'supporting_papers': list(set([f['paper_id'] for f in supporting_findings])),
                    'evidence_count': len(supporting_findings),
                    'confidence': 'high' if len(supporting_findings) >= 3 else 'medium'
                }
                validated_gaps.append(validated_gap)

        print(f"   [OK] Cross-validation: {len(preliminary_gaps)} preliminary -> {len(validated_gaps)} validated")

        return validated_gaps

    def _generate_detailed_description(self, base_desc: str, findings: List[dict]) -> str:
        """生成详细描述"""
        # 基础描述
        description = base_desc

        # 添加来自不同维度的证据
        dimension_counts = Counter([f['dimension'] for f in findings])
        if dimension_counts:
            description += f"\n\n**多维度证据**: "
            description += ', '.join([f"{dim}: {count}项"
                                    for dim, count in dimension_counts.most_common()])

        return description

    def _extract_dimension_evidence(self, findings: List[dict]) -> dict:
        """提取各维度证据"""
        dimensions = {}

        for finding in findings:
            dim = finding['dimension']
            if dim not in dimensions:
                dimensions[dim] = []

            # 只保留前3个最相关的证据
            if len(dimensions[dim]) < 3:
                dimensions[dim].append(finding['context'][:100])

        return dimensions

    def _perform_cross_domain_analysis(self, validated_gaps: List[dict]) -> dict:
        """跨领域关联分析"""
        analysis = {
            'common_challenges': [],
            'key_papers': []
        }

        # 统计高频出现的问题关键词
        all_contexts = []
        for gap in validated_gaps:
            for dim, evidences in gap.get('agent_dimensions', {}).items():
                all_contexts.extend(evidences)

        # 提取高频关键词
        word_counter = Counter()
        for context in all_contexts:
            words = re.findall(r'\w+', context.lower())
            word_counter.update(words)

        # 识别共同挑战 (高频关键词)
        common_keywords = [word for word, count in word_counter.most_common(20)
                          if len(word) > 3 and count > 2]

        for keyword in common_keywords[:10]:
            # 找到包含该关键词的研究空白
            related_gaps = [gap for gap in validated_gaps
                           if keyword in str(gap).lower()]

            if len(related_gaps) >= 2:
                analysis['common_challenges'].append({
                    'challenge': f"高频关键词: {keyword}",
                    'related_gaps': len(related_gaps),
                    'categories': list(set([gap['category'] for gap in related_gaps]))
                })

        # 识别关键文献 (在多个研究空白中被提到)
        paper_mentions = defaultdict(int)
        for gap in validated_gaps:
            for paper_id in gap.get('supporting_papers', []):
                paper_mentions[paper_id] += 1

        # Top 10 关键文献
        for paper_id, count in sorted(paper_mentions.items(),
                                     key=lambda x: x[1], reverse=True)[:10]:
            if count >= 2:  # 至少在2个研究空白中被提到
                analysis['key_papers'].append({
                    'paper_id': paper_id,
                    'mentioned_in_gaps': count
                })

        return analysis

    def _generate_output(self, validated_gaps, cross_domain_analysis) -> dict:
        """生成最终输出"""
        output = {
            'detailed_gaps': validated_gaps,
            'cross_domain_analysis': cross_domain_analysis,
            'summary': {
                'total_detailed_gaps': len(validated_gaps),
                'cross_domain_gaps': len(cross_domain_analysis['common_challenges']),
                'high_confidence_gaps': len([g for g in validated_gaps if g.get('confidence') == 'high']),
                'key_insights': self._generate_key_insights(validated_gaps, cross_domain_analysis)
            },
            'metadata': {
                'generated_by': 'Agent2_Deep_Analyzer',
                'generation_time': '2026-03-30',
                'agent1_cross_validation': True,
                'total_papers_analyzed': len(set([
                    paper for gap in validated_gaps
                    for paper in gap.get('supporting_papers', [])
                ]))
            }
        }

        return output

    def _generate_key_insights(self, gaps, analysis) -> List[str]:
        """生成关键发现"""
        insights = []

        if not gaps:
            insights.append("警告: 未发现验证的研究空白,需要调整匹配策略")
            return insights

        # 按分类统计
        category_counts = Counter([gap['category'] for gap in gaps])
        if category_counts:
            top_category = category_counts.most_common(1)[0]
            insights.append(
                f"最大研究空白类别: {top_category[0]} ({top_category[1]}个空白)"
            )

        # 高置信度空白
        high_conf_gaps = [gap for gap in gaps if gap.get('confidence') == 'high']
        if high_conf_gaps:
            insights.append(
                f"多层证据支撑的空白: {len(high_conf_gaps)}个"
            )

        # 跨领域挑战
        if analysis['common_challenges']:
            insights.append(
                f"跨领域共性挑战: {len(analysis['common_challenges'])}个"
            )

        # 关键文献
        if analysis['key_papers']:
            top_paper = analysis['key_papers'][0]
            insights.append(
                f"最关键文献: {top_paper['paper_id']} "
                f"(在{top_paper['mentioned_in_gaps']}个空白中被提到)"
            )

        return insights


def main():
    """主函数"""
    # 路径配置
    base_dir = Path("D:/xfs/phd/github项目/LiteratureHub")
    agent_results_dir = base_dir / "data/agent_results/all"
    agent1_output = base_dir / "data/ppt_helper/processed/agent1_phase_overview.json"
    output_file = base_dir / "data/ppt_helper/processed/agent2_deep_analysis.json"

    # 执行分析
    analyzer = DeepAnalyzer(str(agent_results_dir), str(agent1_output))
    result = analyzer.analyze()

    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Analysis complete! Output saved to: {output_file}")
    print(f"\n[Summary Statistics]")
    print(f"   - Detailed research gaps: {result['summary']['total_detailed_gaps']}")
    print(f"   - Cross-domain challenges: {result['summary']['cross_domain_gaps']}")
    print(f"   - High confidence gaps: {result['summary']['high_confidence_gaps']}")


if __name__ == '__main__':
    main()
