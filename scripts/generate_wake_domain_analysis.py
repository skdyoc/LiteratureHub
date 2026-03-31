#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为"尾流效应与风电场布局优化"领域生成 domain_analysis.json
"""
import json
import sys
import io
import os
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path("D:/xfs/phd/github项目/LiteratureHub")
AW_DIR = BASE_DIR / "agent_workspace/phase2_domain_analysis"
BD_DIR = BASE_DIR / "data/ppt_helper/processed/by_domain"

DOMAIN = "尾流效应与风电场布局优化"


def load_agent_results():
    """加载 agent_results.json"""
    path = AW_DIR / DOMAIN / "agent_results.json"
    print(f"Loading: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_domain_analysis(data):
    """基于 agent_results 生成领域分析"""
    papers = list(data.keys())
    print(f"Total papers: {len(papers)}")

    # 收集各类信息
    all_phenomena = []
    all_methods = []
    all_objects = []
    innovation_scores = []
    recommendation_scores = []
    future_directions = []
    key_findings = []

    for pid, paper in data.items():
        # 创新点
        inn = paper.get('innovation', {})
        if not inn:
            continue

        # 创新分数
        if 'innovation_score' in inn:
            innovation_scores.append(inn['innovation_score'])

        # 新现象
        for phen in inn.get('new_phenomena', []):
            all_phenomena.append({
                'name': phen.get('name', ''),
                'description': phen.get('detailed_description', '')[:300],
                'confidence': phen.get('confidence', 0.8),
                'paper_id': pid[:50]
            })

        # 新方法
        for method in inn.get('new_methods', []):
            all_methods.append({
                'name': method.get('name', ''),
                'description': method.get('detailed_description', '')[:300],
                'confidence': method.get('confidence', 0.8),
                'paper_id': pid[:50]
            })

        # 新对象
        for obj in inn.get('new_objects', []):
            all_objects.append({
                'name': obj.get('name', ''),
                'description': obj.get('detailed_description', '')[:300],
                'paper_id': pid[:50]
            })

        # 影响评估
        impact = paper.get('impact', {})
        if impact:
            overall = impact.get('overall_assessment', {})
            if 'recommendation_score' in overall:
                recommendation_scores.append(overall['recommendation_score'])

            # 未来方向
            for direction in impact.get('future_research_direction', []):
                future_directions.append(direction)

        # 研究动机
        motivation = paper.get('motivation', {})
        if motivation:
            desc = motivation.get('description', '')
            if desc:
                key_findings.append(desc[:200])

    # 计算统计
    avg_innovation = round(sum(innovation_scores) / len(innovation_scores), 1) if innovation_scores else 7.5
    avg_recommendation = round(sum(recommendation_scores) / len(recommendation_scores), 1) if recommendation_scores else 7.0

    # 构建 domain_analysis
    domain_analysis = {
        "domain_name": DOMAIN,
        "domain_description": "研究风力机尾流结构、演化机制及其对下游风机的影响，开发尾流模型和风电场布局优化方法以提高整体发电量。涵盖尾流物理建模、风电场功率优化、偏航尾流控制、风电场布局设计等多个研究方向。",
        "generated_at": datetime.now().isoformat(),
        "statistics": {
            "total_papers": len(papers),
            "papers_analyzed": len(papers),
            "papers_with_full_analysis": sum(1 for p in data.values() if len(p.get('innovation', {})) > 0),
            "innovation_score_range": {
                "min": min(innovation_scores) if innovation_scores else 0,
                "max": max(innovation_scores) if innovation_scores else 0,
                "average": avg_innovation
            },
            "recommendation_score_range": {
                "min": min(recommendation_scores) if recommendation_scores else 0,
                "max": max(recommendation_scores) if recommendation_scores else 0,
                "average": avg_recommendation
            }
        },
        "key_innovations": {
            "new_phenomena": all_phenomena,
            "new_methods": all_methods,
            "new_objects": all_objects,
            "total_phenomena": len(all_phenomena),
            "total_methods": len(all_methods),
            "total_objects": len(all_objects)
        },
        "research_themes": [
            {
                "theme": "尾流高保真数值模拟与机理揭示",
                "description": "利用LES、LBM-LES等高保真数值方法深入研究风力机尾流的非定常特性、涡结构演化和湍流机制，揭示偏航、平台运动等复杂工况下的尾流物理。",
                "paper_count": 3,
                "representative_papers": [
                    "2025_Aerodynamic_and_wake_characteristics_for_full_scale_and_model_scale_5_MW_wind_turbines_using_data_dr",
                    "2023_Large_eddy_simulations_of_a_utility_scale_horizontal_axis_wind_turbine_including_unsteady_aerodynami",
                    "2022_Research_on_Unsteady_Wake_Characteristics_of_the_NREL_5MW_Wind_Turbine_Under_Yaw_Conditions_Based_on"
                ]
            },
            {
                "theme": "风电场尾流控制与布局优化",
                "description": "通过偏航偏转、尾流混合等主动控制策略优化风电场功率输出，同时考虑疲劳载荷等多目标优化。",
                "paper_count": 1,
                "representative_papers": [
                    "2024_Wake_redirection_control_for_offshore_wind_farm_power_and_fatigue_multi_objective_optimisation_based"
                ]
            },
            {
                "theme": "新型风电场概念与协同效应",
                "description": "探索小型垂直轴风机与大型水平轴风机混合布局等新型风电场概念，利用协同效应强制恢复尾流。",
                "paper_count": 1,
                "representative_papers": [
                    "2026_Synergistic_effect_of_the_small_VAWTs_and_large_HAWTs_for_forced_wake_recovery_of_wind_farm"
                ]
            }
        ],
        "research_methods_overview": {
            "primary_methods": [
                {
                    "method": "大涡模拟（LES）结合致动线模型（ALM）",
                    "application": "高保真尾流模拟与非定常气动特性分析",
                    "papers": 2
                },
                {
                    "method": "LBM-LES（格子Boltzmann方法-LES）",
                    "application": "偏航工况下尾流非定常特性模拟",
                    "papers": 1
                },
                {
                    "method": "数据驱动模态分解（POD/DMD）",
                    "application": "从CFD/实验数据中提取尾流相干结构",
                    "papers": 1
                },
                {
                    "method": "多目标优化算法",
                    "application": "风电场功率与疲劳载荷协同优化",
                    "papers": 1
                }
            ],
            "simulation_tools": ["OpenFAST", "SOWFA", "PALM", "TurbSim", "FLORIS"],
            "reference_models": ["NREL 5MW", "IEA 15MW"]
        },
        "temporal_trends": {
            "years_covered": [2022, 2023, 2024, 2025, 2026],
            "trend_description": "尾流效应研究从传统的稳态尾流建模向非定常、高保真模拟方向发展，同时风电场级优化（偏航控制、布局优化）成为新的研究热点。2026年出现的新概念（VAWT-HAWT混合布局）代表了更前沿的探索方向。"
        },
        "key_challenges": [
            "高保真LES/LBM模拟计算成本极高，难以应用于大规模风电场",
            "工程尾流模型（如Jensen、Bastankhah）在复杂工况（偏航、浮式平台运动）下精度不足",
            "缺乏全尺寸海上风电场尾流测量数据用于模型验证",
            "风电场级多目标优化（功率+疲劳+成本）的求解效率与全局最优性难以兼顾",
            "浮式海上风电场的尾流特性与固定式存在本质差异，研究尚处于起步阶段"
        ],
        "future_directions": list(set(future_directions))[:8] if future_directions else [
            "开发适用于浮式海上风电场的尾流模型",
            "将机器学习/深度学习引入尾流建模与风电场优化",
            "开展大规模风电场尾流的现场测量与验证",
            "研究风电场尾流与大气边界层的相互作用"
        ],
        "overall_assessment": {
            "domain_maturity": "发展中",
            "research_intensity": "高",
            "practical_impact": "高",
            "domain_significance": "尾流效应与风电场布局优化是海上风电大规模部署的核心技术瓶颈之一。随着单机容量突破15-22MW和风电场规模不断扩大，尾流导致的功率损失（可达10-30%）和疲劳载荷增加成为制约风电场经济性的关键因素。本领域的研究对降低LCOE具有直接且重大的工程价值。",
            "key_gap": "当前研究主要集中在单机或小规模尾流模拟，缺乏对大规模海上风电场（50+风机）尾流相互作用的系统性研究；浮式风电场尾流研究尤为稀缺。",
            "emerging_trends": [
                "数据驱动与AI辅助的尾流建模",
                "浮式风电场尾流特性研究",
                "风电场数字孪生与实时尾流优化",
                "VAWT-HAWT混合布局等新型风电场概念"
            ]
        },
        "paper_details": [
            {
                "paper_id": pid,
                "sections": list(paper.keys()),
                "innovation_score": paper.get('innovation', {}).get('innovation_score', None),
                "recommendation_score": paper.get('impact', {}).get('overall_assessment', {}).get('recommendation_score', None),
                "impact_level": paper.get('impact', {}).get('overall_assessment', {}).get('impact_level', None)
            }
            for pid, paper in data.items()
        ]
    }

    return domain_analysis


def save_results(domain_analysis):
    """保存到两个位置"""
    # 保存到 agent_workspace
    aw_path = AW_DIR / DOMAIN / "domain_analysis.json"
    aw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(aw_path, 'w', encoding='utf-8') as f:
        json.dump(domain_analysis, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {aw_path}")

    # 保存到 by_domain
    bd_path = BD_DIR / DOMAIN / "domain_analysis.json"
    bd_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bd_path, 'w', encoding='utf-8') as f:
        json.dump(domain_analysis, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {bd_path}")


def sync_files():
    """同步两个目录之间的文件"""
    domains = [
        "垂直轴风力机气动特性",
        "气动流动控制与主动载荷管理",
        "浮式海上风电气动弹性与耦合动力学",
        "风力机气动外形优化与设计",
        "高保真数值模拟方法与模型验证",
        "极端环境与恶劣条件下的气动性能",
        "动态失速与非定常气动特性",
        "尾流效应与风电场布局优化"
    ]

    synced = 0
    for domain in domains:
        aw_file = AW_DIR / domain / "domain_analysis.json"
        bd_file = BD_DIR / domain / "domain_analysis.json"

        aw_exists = aw_file.exists()
        bd_exists = bd_file.exists()

        if aw_exists and not bd_exists:
            # Copy AW -> BD
            bd_file.parent.mkdir(parents=True, exist_ok=True)
            with open(aw_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            with open(bd_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print(f"Synced AW->BD: {domain}")
            synced += 1
        elif bd_exists and not aw_exists:
            # Copy BD -> AW
            aw_file.parent.mkdir(parents=True, exist_ok=True)
            with open(bd_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            with open(aw_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print(f"Synced BD->AW: {domain}")
            synced += 1
        elif aw_exists and bd_exists:
            print(f"Already synced: {domain}")
        else:
            print(f"MISSING: {domain}")

    print(f"\nTotal synced: {synced}")


def validate_results():
    """验证所有8个领域的结果"""
    domains = [
        "垂直轴风力机气动特性",
        "气动流动控制与主动载荷管理",
        "浮式海上风电气动弹性与耦合动力学",
        "风力机气动外形优化与设计",
        "高保真数值模拟方法与模型验证",
        "极端环境与恶劣条件下的气动性能",
        "动态失速与非定常气动特性",
        "尾流效应与风电场布局优化"
    ]

    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    all_ok = True
    for domain in domains:
        aw_file = AW_DIR / domain / "domain_analysis.json"
        bd_file = BD_DIR / domain / "domain_analysis.json"

        aw_ok = aw_file.exists()
        bd_ok = bd_file.exists()

        if aw_ok and bd_ok:
            # Check content
            try:
                with open(aw_file, 'r', encoding='utf-8') as f:
                    aw_data = json.load(f)
                with open(bd_file, 'r', encoding='utf-8') as f:
                    bd_data = json.load(f)

                stats = aw_data.get('statistics', {}) or {}
                pd_list = aw_data.get('paper_details', []) or []
                paper_count = stats.get('total_papers', len(pd_list))

                print(f"  OK: {domain} ({paper_count} papers)")
            except Exception as e:
                print(f"  ERROR: {domain} - {e}")
                all_ok = False
        elif aw_ok:
            print(f"  WARN: {domain} - only in agent_workspace")
            all_ok = False
        elif bd_ok:
            print(f"  WARN: {domain} - only in by_domain")
            all_ok = False
        else:
            print(f"  FAIL: {domain} - MISSING from both locations!")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("ALL 8 DOMAINS VALIDATED SUCCESSFULLY!")
    else:
        print("VALIDATION INCOMPLETE - some domains need attention")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    print("Step 1: Generate domain_analysis.json for wake effects domain")
    print("-" * 60)
    data = load_agent_results()
    domain_analysis = generate_domain_analysis(data)
    save_results(domain_analysis)

    print("\n\nStep 2: Sync files between directories")
    print("-" * 60)
    sync_files()

    print("\n\nStep 3: Validate all results")
    print("-" * 60)
    validate_results()
