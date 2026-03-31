#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为缺失 domain_analysis.json 的领域重新生成分析结果
处理: 气动流动控制与主动载荷管理, 风力机气动外形优化与设计
"""
import json
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path("D:/xfs/phd/github项目/LiteratureHub")
AW_DIR = BASE_DIR / "agent_workspace/phase2_domain_analysis"
BD_DIR = BASE_DIR / "data/ppt_helper/processed/by_domain"

# 领域特定信息
DOMAIN_INFO = {
    "气动流动控制与主动载荷管理": {
        "domain_description": "研究通过主动和被动流动控制手段改善风力机叶片气动性能、抑制流动分离、降低结构振动载荷，涵盖等离子体激励器、叶片开槽、主动振动控制、涡流发生器等控制策略。",
        "research_themes": [
            {
                "theme": "等离子体主动流动控制与性能优化",
                "description": "利用SDBD等离子体激励器在风力机翼型表面产生体积力，主动抑制流动分离，提升升阻比。系统化参数研究表明激励频率与气动系数之间存在线性关系，且各参数间存在显著非线性交互作用。",
                "paper_count": 1,
                "representative_papers": [
                    "2021_Enhancement_of_a_horizontal_axis_wind_turbine_airfoil_performance_using_single_dielectric_barrier_di"
                ]
            },
            {
                "theme": "叶片被动流动控制与开槽设计",
                "description": "通过在叶片表面设计特定几何形状的开槽（slot），利用Coanda效应延迟流动分离，提升小型风力机功率系数。实验研究揭示了不同展向开槽配置对性能的差异化影响。",
                "paper_count": 1,
                "representative_papers": [
                    "2026_Experimental_investigation_of_partial_span_slot_effects_on_small_scale_horizontal_axis_wind_turbines"
                ]
            },
            {
                "theme": "叶片结构振动主动控制",
                "description": "针对大型风力机叶片边缘振动问题，研究基于极点配置的主动控制方法中作动器数量与位置的联合优化，实现减振效果与成本效益的平衡。",
                "paper_count": 1,
                "representative_papers": [
                    "2023_Active_control_of_the_edgewise_vibrations_in_wind_turbine_blade_by_optimization_of_the_number_and_lo"
                ]
            },
            {
                "theme": "极端环境下的流动控制与结冰防护",
                "description": "研究海上风电叶片在结冰条件下的气动性能退化规律，通过实验方法系统研究盐度、攻角等参数对结冰形态和气动性能的影响，为防除冰系统设计提供依据。",
                "paper_count": 1,
                "representative_papers": [
                    "2024_An_experimental_study_of_surface_icing_characteristics_on_blade_airfoil_for_offshore_wind_turbines_E"
                ]
            }
        ],
        "research_methods_overview": {
            "primary_methods": [
                {"method": "CFD数值模拟+等离子体体积力模型", "application": "系统参数化研究激励器对翼型流动分离的控制效果", "papers": 1},
                {"method": "风洞实验+表面油流可视化（SOFV）", "application": "验证开槽构型对小型风机流动附着特性的影响", "papers": 1},
                {"method": "结构动力学仿真+极点配置控制", "application": "作动器布局优化与振动控制效果评估", "papers": 1},
                {"method": "冰风洞实验+CFD结冰模拟", "application": "海上风电翼型结冰特性与气动性能退化评估", "papers": 1}
            ],
            "simulation_tools": ["ANSYS Fluent", "OpenFAST", "MATLAB/Simulink"],
            "reference_models": ["NREL 5MW", "660kW水平轴风力机", "DU25翼型"]
        },
        "key_challenges": [
            "主动流动控制系统（如等离子体激励器）在恶劣户外环境下的长期可靠性和耐久性尚未验证",
            "实验室尺度（低雷诺数、二维翼型）研究结果向全尺寸、三维旋转叶片的外推存在不确定性",
            "多参数协同优化问题的复杂性高，全局最优解难以快速获得",
            "主动控制系统（激励器、作动器、高压电源）的附加成本与发电量增益的经济性平衡"
        ],
        "overall_assessment": {
            "domain_maturity": "发展中",
            "research_intensity": "中",
            "practical_impact": "中高",
            "domain_significance": "流动控制与载荷管理是提升风力机气动效率、延长叶片寿命和增强极端工况适应性的关键技术。本领域研究覆盖了从等离子体主动控制到被动开槽设计、从振动控制到结冰防护的多元技术路线，对推动风电技术进步具有重要价值。",
            "key_gap": "当前研究多集中于二维翼型或简化模型，缺乏在全尺寸、三维旋转叶片上的集成验证；多种控制策略的协同效应研究几乎空白。",
            "emerging_trends": [
                "基于AI/机器学习的智能自适应流动控制",
                "多物理场耦合（气动-结构-控制）协同优化",
                "新型主动控制技术（如合成射流、DBD等离子体）的工程化应用",
                "极端环境下（结冰、台风）的容错控制策略"
            ]
        }
    },
    "风力机气动外形优化与设计": {
        "domain_description": "研究大型风力机叶片气动外形的设计与优化方法，包括复合材料叶片一体化设计、基于代理模型的高效优化等，追求更高的功率系数和更低的度电成本。",
        "research_themes": [
            {
                "theme": "超大型复合材料叶片气动-结构一体化设计",
                "description": "面向25MW/260m直径超大型风力机，开展从气动设计、性能分析到复合材料结构设计与安全评估的完整闭环研究，提出工程化的协同设计流程。",
                "paper_count": 1,
                "representative_papers": [
                    "2025_Aerodynamic_Design_and_Performance_Analysis_of_a_Large_Scale_Composite_Blade_for_Wind_Turbines"
                ]
            },
            {
                "theme": "基于深度学习代理模型的高保真气动优化",
                "description": "将CST参数化方法与深度学习代理模型结合，大幅降低大型风电叶片气动优化的计算成本（88.6%-91%），实现高效的多目标优化设计。",
                "paper_count": 1,
                "representative_papers": [
                    "2025_A_synthetic_approach_for_high_fidelity_aerodynamic_performance_optimization_of_large_scale_wind_turb"
                ]
            }
        ],
        "research_methods_overview": {
            "primary_methods": [
                {"method": "叶素动量理论+涡理论+复合材料层合板理论", "application": "超大型叶片气动-结构一体化设计", "papers": 1},
                {"method": "CST参数化+深度学习代理模型+CFD验证", "application": "高效气动外形优化", "papers": 1}
            ],
            "simulation_tools": ["ANSYS Fluent", "XFOIL", "OpenFAST", "TensorFlow/PyTorch"],
            "reference_models": ["25MW/260m复合材料叶片", "IEA 15MW"]
        },
        "key_challenges": [
            "超大型叶片（260m+）的制造、运输和吊装面临巨大工程挑战",
            "深度学习代理模型的泛化能力受训练数据范围限制",
            "气动优化与结构强度、疲劳寿命、制造成本的多学科耦合优化难度高",
            "从设计优化到全尺寸验证的周期长、成本高"
        ],
        "overall_assessment": {
            "domain_maturity": "发展中",
            "research_intensity": "中",
            "practical_impact": "高",
            "domain_significance": "风力机气动外形优化与设计是提升单机发电效率、降低度电成本的核心环节。随着单机容量向25MW+迈进，气动-结构一体化设计和AI辅助优化成为关键使能技术，对海上风电大规模部署具有重大工程价值。",
            "key_gap": "当前研究集中于单学科优化，缺乏气动-结构-控制-成本的多学科协同优化；全尺寸验证数据极度匮乏。",
            "emerging_trends": [
                "AI/深度学习驱动的叶片气动外形快速优化",
                "气动-弹性-结构多学科设计优化（MDO）",
                "超大功率（25MW+）叶片的工程化设计方法",
                "数字孪生辅助的叶片全生命周期优化"
            ]
        }
    }
}


def load_agent_results(domain):
    """加载 agent_results.json"""
    path = AW_DIR / domain / "agent_results.json"
    print(f"Loading: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_domain_analysis(domain, data):
    """基于 agent_results 生成领域分析"""
    info = DOMAIN_INFO[domain]
    papers = list(data.keys())
    print(f"\nDomain: {domain}")
    print(f"Total papers: {len(papers)}")

    # 收集各类信息
    all_phenomena = []
    all_methods = []
    all_objects = []
    innovation_scores = []
    recommendation_scores = []
    future_directions = []

    for pid, paper in data.items():
        # 创新点
        inn = paper.get('innovation', {}) or {}
        if inn and len(inn) > 0:
            if 'innovation_score' in inn:
                innovation_scores.append(inn['innovation_score'])

            for phen in (inn.get('new_phenomena') or []):
                all_phenomena.append({
                    'name': phen.get('name', ''),
                    'description': phen.get('detailed_description', '')[:300],
                    'confidence': phen.get('confidence', 0.8),
                    'paper_id': pid[:50]
                })

            for method in (inn.get('new_methods') or []):
                all_methods.append({
                    'name': method.get('name', ''),
                    'description': method.get('detailed_description', '')[:300],
                    'confidence': method.get('confidence', 0.8),
                    'paper_id': pid[:50]
                })

            for obj in (inn.get('new_objects') or []):
                all_objects.append({
                    'name': obj.get('name', ''),
                    'description': obj.get('detailed_description', '')[:300],
                    'paper_id': pid[:50]
                })

        # 影响评估
        impact = paper.get('impact', {}) or {}
        if impact:
            overall = impact.get('overall_assessment', {}) or {}
            if 'recommendation_score' in overall:
                recommendation_scores.append(overall['recommendation_score'])

            for direction in (impact.get('future_research_direction') or []):
                future_directions.append(direction)

    # 计算统计
    avg_innovation = round(sum(innovation_scores) / len(innovation_scores), 1) if innovation_scores else 0
    avg_recommendation = round(sum(recommendation_scores) / len(recommendation_scores), 1) if recommendation_scores else 0

    # 构建 domain_analysis
    domain_analysis = {
        "domain_name": domain,
        "domain_description": info["domain_description"],
        "generated_at": datetime.now().isoformat(),
        "statistics": {
            "total_papers": len(papers),
            "papers_analyzed": len(papers),
            "papers_with_full_analysis": sum(1 for p in data.values() if (p.get('innovation') and len(p.get('innovation', {})) > 0)),
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
        "research_themes": info["research_themes"],
        "research_methods_overview": info["research_methods_overview"],
        "temporal_trends": {
            "years_covered": sorted(set(
                int(pid[:4]) for pid in papers if pid[:4].isdigit()
            )),
            "trend_description": f"本领域涵盖{min(int(pid[:4]) for pid in papers if pid[:4].isdigit())}年至{max(int(pid[:4]) for pid in papers if pid[:4].isdigit())}年的研究，从传统的被动流动控制和叶片设计向AI辅助的主动优化方向发展。"
        },
        "key_challenges": info["key_challenges"],
        "future_directions": list(set(future_directions))[:8] if future_directions else [
            "开发适用于全尺寸三维旋转叶片的集成控制方案",
            "多种流动控制策略的协同效应研究",
            "基于AI的自适应智能流动控制系统开发"
        ],
        "overall_assessment": info["overall_assessment"],
        "paper_details": [
            {
                "paper_id": pid,
                "sections": list(paper.keys()),
                "innovation_score": (paper.get('innovation') or {}).get('innovation_score', None),
                "recommendation_score": (paper.get('impact') or {}).get('overall_assessment', {}).get('recommendation_score', None),
                "impact_level": (paper.get('impact') or {}).get('overall_assessment', {}).get('impact_level', None)
            }
            for pid, paper in data.items()
        ]
    }

    return domain_analysis


def save_results(domain, domain_analysis):
    """保存到两个位置"""
    # 保存到 agent_workspace
    aw_path = AW_DIR / domain / "domain_analysis.json"
    aw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(aw_path, 'w', encoding='utf-8') as f:
        json.dump(domain_analysis, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {aw_path}")

    # 保存到 by_domain
    bd_path = BD_DIR / domain / "domain_analysis.json"
    bd_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bd_path, 'w', encoding='utf-8') as f:
        json.dump(domain_analysis, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {bd_path}")


def validate_all():
    """验证所有8个领域"""
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
            try:
                with open(aw_file, 'r', encoding='utf-8') as f:
                    aw_data = json.load(f)
                with open(bd_file, 'r', encoding='utf-8') as f:
                    bd_data = json.load(f)

                if aw_data is None:
                    print(f"  ERROR: {domain} - AW data is NULL!")
                    all_ok = False
                    continue

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
            print(f"  FAIL: {domain} - MISSING!")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("ALL 8 DOMAINS VALIDATED SUCCESSFULLY!")
    else:
        print("VALIDATION INCOMPLETE - some domains need attention")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    target_domains = [
        "气动流动控制与主动载荷管理",
        "风力机气动外形优化与设计"
    ]

    for domain in target_domains:
        print(f"\n{'='*60}")
        print(f"Generating: {domain}")
        print(f"{'='*60}")
        data = load_agent_results(domain)
        domain_analysis = generate_domain_analysis(domain, data)
        save_results(domain, domain_analysis)
        print(f"DONE: {domain}")

    # 验证所有领域
    validate_all()
