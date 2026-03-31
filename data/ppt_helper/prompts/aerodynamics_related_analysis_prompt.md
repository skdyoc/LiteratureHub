# 大型风力机气动相关问题深度分析任务

## 任务定位
为博一研究生制作导师汇报PPT，识别可支撑5年博士研究的**与气动相关**的研究方向。

## 核心领域：大型风力机气动

### ✅ 包含（与气动直接相关）
1. **核心气动**：
   - 动态失速（Dynamic Stall）
   - 旋转效应（Rotational Effects）
   - 三维修正（3D Corrections）
   - 非定常气动（Unsteady Aerodynamics）
   - 大攻角分离流（Large Angle of Attack, Separated Flow）

2. **气动耦合**（气主导的耦合问题）：
   - 气动弹性（Aeroelasticity）- 气动主导的
   - 气动-结构耦合（Aero-structure coupling）
   - 浮式风机气动效应（FOWT aerodynamic effects）- 运动对气动的影响
   - 非定常来流下的气动响应

3. **气动优化**：
   - 气动外形优化
   - 翼型优化
   - 叶片气动设计

4. **气动方法**：
   - 高保真CFD方法
   - 降阶模型（ROM）
   - BEM理论改进
   - 湍流建模

### ❌ 排除（与气动关系不大）
- **纯结构力学**：不考虑气动的疲劳、损伤、振动分析
- **纯控制**：不考虑气动的控制算法、变桨策略
- **纯水动力学**：不考虑气动的波浪载荷、水动响应
- **风电场宏观布局**：尾流效应、场级优化
- **垂直轴风机**：可能不是研究重点
- **特殊环境**：结冰、沙尘等环境因素（除非研究气动影响）
- **噪声分析**：气动噪声可以包含

## 分析方法

### 第一步：识别相关论文
从phase1_overview.json和各领域domain_analysis.json中，筛选与气动相关的论文：

**关键词筛选**：
- aerodynamic*, dynamic stall, rotational, unsteady
- aeroelastic, aero-structure, FOWT, floating
- CFD, CSD, ROM, BEM
- optimization, design, airfoil, blade

**排除关键词**：
- pure structural, pure control
- wake effect, farm layout
- VAWT（垂直轴）
- ice, sand（除非研究气动影响）

### 第二步：深度阅读full.md
对筛选出的论文（约15-20篇），读取full.md文件，提取：

**技术细节**：
1. 建模方程和方法
2. CFD数值方法
3. 实验验证数据
4. 关键发现（带数据）
5. 局限性
6. 未来工作方向

### 第三步：识别研究空白
基于深度分析，识别：
- 哪些气动相关问题尚未解决？
- 哪些建模方法需要改进？
- 哪些工况缺乏研究？
- 哪些耦合机制不清楚？
- 哪些方向可以支撑5年研究？

### 第四步：评估可行性
对每个研究空白，评估：
- 数据可获得性
- 工具成熟度
- 5年研究周期可行性
- 创新空间大小

### 第五步：形成候选方向
综合分析，提出2-4个候选研究方向：
- 明确研究问题
- 阐述理论贡献
- 说明工程价值
- 评估可行性

## 输出要求

创建JSON文件：`aerodynamics_related_analysis.json`

包含：
1. **已分析论文列表**（15-20篇）
   - 基本信息
   - 核心气动主题
   - 技术细节
   - 局限性

2. **识别的研究空白**（5-8个）
   - 技术描述
   - 文献证据
   - 具体问题
   - 可行性评估

3. **候选研究方向**（2-4个）
   - 研究问题
   - 理论贡献
   - 工程价值
   - 可行性分析

## 执行步骤
1. 读取phase1_overview.json，了解领域分布
2. 读取各domain_analysis.json，筛选气动相关论文
3. 对筛选出的论文，读取full.md深度分析
4. 综合分析，识别研究空白
5. 提出候选研究方向
6. 生成输出JSON文件
