# 纯气动深度分析任务指令

## 核心目标

从大型风力机气动领域的文献中，识别**可支撑5年博士研究的纯气动问题**。

## 严格约束

### ✅ 必须聚焦（PURE AERODYNAMICS）
- **Dynamic Stall**（动态失速）：非定常气动现象、涡脱落、迟滞效应
- **Rotational Effects**（旋转效应）：3D旋转增升、离心/科氏力影响
- **3D Corrections**（三维修正）：展向流、径向流、旋转修正
- **Large Angle of Attack**（大攻角）：分离流、深失速、再附着
- **Separated Flow Phenomena**（分离流现象）：边界层分离、剪切层、涡结构

### ❌ 严禁涉及（NOT PURE AERODYNAMICS）
- 浮式风机结构/控制
- 疲劳评估（结构力学）
- 多物理场耦合（气动-水动-结构耦合）
- 海洋湍流模型
- 载荷控制算法
- 风电场布局优化
- 垂直轴风机
- 结冰/沙尘环境

## 分析方法

### 第一步：系统性识别纯气动论文

从以下来源识别纯气动论文：
1. **phase1_overview.json** - 查看各领域概览，筛选"动态失速与非定常气动特性"领域
2. **by_domain/动态失速与非定常气动特性/domain_analysis.json** - 该领域的深度分析
3. **agent_results** - 扫描各论文的5维分析结果，筛选关键词：
   - dynamic stall, rotational augmentation, unsteady aerodynamics
   - 3D corrections, separated flow, yaw effects
   - surge motion on aerodynamics（仅气动效应，不涉及结构响应）

### 第二步：深度阅读full.md（"读厚"阶段）

对筛选出的核心论文，读取**full.md**文件，提取：

#### 1. 技术细节（必须具体）

**建模方程和公式**：
- 例如：Beddoes-Leishman模型的分离点公式
- 例如：法向/切向力系数计算公式
- 例如：时间滞后方程

**数值方法**：
- CFD方法（URANS, LES, DES）
- 湍流模型（SST k-ω, γ-Reθ转捩模型）
- 网格参数、时间步长

**实验验证**：
- 风洞/水洞实验数据
- NREL Phase VI转子数据
- S809翼型数据

**关键发现（带数据）**：
- 例如："迟滞环减少60%"
- 例如："效率提升10-50倍，精度损失<10%"

#### 2. 研究空白识别

从论文中提取的**局限性**和**未来工作**，识别：
- 哪些气动现象尚未充分理解？
- 哪些建模方法精度不足？
- 哪些工况/条件缺乏研究？
- 哪些耦合机制不清楚？

#### 3. 可研究性问题

识别**可以支撑5年博士研究**的纯气动问题：
- 问题必须有足够的理论深度
- 问题必须有实际工程价值
- 问题必须尚未解决
- 问题必须在现有文献基础上可推进

### 第三步：综合分析（"读薄"阶段）

将多篇论文的技术细节综合，形成：
1. **核心气动问题**：具体、可研究
2. **现有方法总结**：建模方法、验证数据、局限性
3. **研究空白**：明确、具体、有数据支撑
4. **候选研究方向**：纯气动、可深入、有创新空间

## 输出格式

创建以下JSON结构：

```json
{
  "pure_aerodynamics_papers": [
    {
      "paper_id": "论文标识",
      "title": "论文标题",
      "year": 年份,
      "core_aerodynamic_topic": "核心气动主题（dynamic_stall/rotational_effects/3d_corrections等）",
      "technical_details": {
        "modeling_equations": ["具体方程1", "具体方程2"],
        "numerical_methods": "CFD方法描述",
        "experimental_validation": "实验数据来源",
        "key_findings_with_data": ["发现1+数据", "发现2+数据"]
      },
      "limitations": ["局限性1", "局限性2"],
      "future_work": ["未来工作建议1", "未来工作建议2"]
    }
  ],
  "identified_research_gaps": [
    {
      "gap_id": "研究空白编号",
      "title": "研究空白标题",
      "category": "dynamic_stall/rotational_effects/3d_corrections等",
      "description": "详细描述",
      "evidence_papers": ["支撑论文ID列表"],
      "specific_problems": [
        "具体技术问题1",
        "具体技术问题2"
      ],
      "feasibility": {
        "data_available": true/false,
        "tools_mature": true/false,
        "timescale_5years": true/false,
        "innovation_space": "大/中/小"
      }
    }
  ],
  "candidate_research_directions": [
    {
      "direction_id": "方向编号",
      "title": "研究方向标题",
      "pure_aerodynamics_focus": "具体纯气动焦点",
      "research_problem": "具体可研究问题",
      "theoretical_contribution": "理论贡献",
      "engineering_value": "工程价值",
      "feasibility_analysis": "可行性分析",
      "supporting_papers": ["支撑论文ID列表"]
    }
  ]
}
```

## 执行步骤

1. **读取phase1_overview.json**，了解8大领域分布
2. **读取by_domain/动态失速与非定常气动特性/domain_analysis.json**，获取该领域论文列表
3. **扫描agent_results**，根据关键词筛选纯气动论文
4. **读取筛选出的论文的full.md文件**，深度提取技术细节
5. **综合分析**，识别研究空白和候选方向
6. **生成输出JSON文件**

## 关键词列表

### ✅ 包含（纯气动）
- dynamic stall, unsteady aerodynamics
- rotational augmentation, 3D rotational effects
- 3D corrections, spanwise flow, radial flow
- separated flow, boundary layer separation
- large angle of attack, deep stall
- vortex shedding, leading-edge vortex
- hysteresis effects, unsteady boundary layer
- yawed inflow, yaw effects
- surge motion effects on aerodynamics（仅气动）

### ❌ 排除（非纯气动）
- floating wind turbine（结构/控制）
- fatigue load（结构）
- fatigue damage assessment
- multi-physics coupling
- ocean turbulence, wave loads
- control strategies, pitch control
- wake effect, farm layout
- vertical axis wind turbine (VAWT)
- ice accretion, sand erosion
- aeroelasticity, CSD coupling
- structural dynamics, blade vibration

## 质量标准

1. **技术深度**：每个研究空白必须有具体技术细节支撑
2. **数据支撑**：关键发现必须有实验/仿真数据
3. **纯气动聚焦**：严格区分纯气动与多物理场问题
4. **可研究性**：每个空白必须可支撑深入研究的可能性
5. **文献证据**：所有结论必须有具体论文支撑

---

**记住**：先"读厚"（深入分析full.md提取技术细节），再"读薄"（综合凝练研究空白）！
