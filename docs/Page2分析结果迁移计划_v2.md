# LiteratureHub Page 2 分析结果迁移计划 v2（分层结构）

**制定日期**: 2026-03-29
**制定者**: 哈雷酱（傲娇大小姐工程师）✨
**核心改进**: 参考 Page 1 的 `all` + `categories` 分层结构

---

## 📁 目标目录结构（完全遵循 Page 1 模式）

```
LiteratureHub/data/agent_results/
├── all/                                    # 【主目录】所有分析结果
│   ├── analysis_index.json                # all/ 的状态索引
│   ├── 2018_Aerodynamic_Analysis_.../     # 论文1
│   │   ├── innovation.json
│   │   ├── motivation.json
│   │   ├── roadmap.json
│   │   ├── mechanism.json
│   │   └── impact.json
│   ├── 2018_Aerodynamic_Optimization_.../  # 论文2
│   └── ...
│
└── categories/                             # 【分类目录】各个分类的分析结果
    ├── 大型风力机气动/                      # 分类1
    │   ├── analysis_index.json            # 分类目录的索引
    │   ├── 2018_Aerodynamic_Analysis_.../
    │   └── ...
    ├── Aerodynamic_Optimization/          # 分类2（如果有）
    │   └── ...
    └── ...
```

**与 Page 1 的对应关系**:

| Page 1 (MinerU 转换) | Page 2 (AI 分析) |
|---------------------|-----------------|
| `markdown/all/` | `agent_results/all/` |
| `markdown/categories/{分类}/` | `agent_results/categories/{分类}/` |
| `conversion_index.json` | `analysis_index.json` |
| `is_converted` | `overall_status` |
| `converted_at` | `completed_at` |

---

## 🎯 核心逻辑（完全复刻 Page 1）

### 场景 A: 分析 `all/` 目录

```
1. 选择 markdown/all/ 作为输入
2. 分析结果保存到 agent_results/all/
3. 生成 agent_results/all/analysis_index.json
```

### 场景 B: 分析分类目录

```
1. 选择 markdown/categories/{分类}/ 作为输入
2. 检查 agent_results/all/ 是否已有结果
   ├─ 已有 → 复制到 agent_results/categories/{分类}/
   └─ 没有 → 进行分析，保存到 agent_results/categories/{分类}/
3. 同时更新 agent_results/all/ 和分类目录的索引
```

**逻辑示例**（参考 Page 1 的 `_convert_category_directory`）:
```python
def _analyze_category_directory(self, category_name: str):
    """分析分类目录（场景B）"""

    # 1. 检查 all/ 是否已有该论文的分析结果
    all_result_dir = self.output_dir / "all" / paper_id
    all_has_result = (all_result_dir / "innovation.json").exists()

    # 2. 检查分类目录是否已有结果
    category_result_dir = self.output_dir / "categories" / category_name / paper_id
    category_has_result = (category_result_dir / "innovation.json").exists()

    # 3. 判断处理方式
    if category_has_result:
        # 分类目录已存在 → 跳过
        logger.info(f"已存在（分类）: {paper_id}")

    elif all_has_result:
        # all/ 已存在，但分类目录没有 → 复制
        logger.info(f"从 all/ 复制: {paper_id}")
        shutil.copytree(all_result_dir, category_result_dir)

    else:
        # 都不存在 → 分析
        logger.info(f"需要分析: {paper_id}")
        # ... 执行分析 ...
```

---

## 📋 详细执行步骤

### Step 1: 创建目录结构（5分钟）

```bash
cd LiteratureHub

# 创建主目录
mkdir -p data/agent_results/all
mkdir -p data/agent_results/categories
```

### Step 2: 迁移已有结果到 `all/`（20分钟）

#### 2.1 创建迁移脚本

**文件**: `scripts/migrate_analysis_results_v2.py`

```python
"""
迁移 Wind-Aero 项目的分析结果到 LiteratureHub
遵循 all/ + categories/ 的分层结构
"""

import shutil
import json
from pathlib import Path
from datetime import datetime

def migrate_to_all_structure():
    """迁移已有分析结果到 agent_results/all/"""

    source_dir = Path("D:/xfs/phd/github项目/Wind-Aero-Literature-Analysis-System/data/agent_results")
    target_all_dir = Path("data/agent_results/all")

    target_all_dir.mkdir(parents=True, exist_ok=True)

    # 初始化索引
    analysis_index = {
        "metadata": {
            "total_papers": 0,
            "analyzed_papers": 0,
            "pending_papers": 0,
            "last_updated": datetime.now().isoformat(),
            "source": "Wind-Aero-Literature-Analysis-System"
        },
        "papers": {}
    }

    # 遍历所有论文
    for paper_dir in source_dir.iterdir():
        if not paper_dir.is_dir():
            continue

        paper_id = paper_dir.name

        # 复制到 all/
        target_paper_dir = target_all_dir / paper_id
        if target_paper_dir.exists():
            shutil.rmtree(target_paper_dir)
        shutil.copytree(paper_dir, target_paper_dir)

        # 记录到索引
        analyzers = {}
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            json_file = target_paper_dir / f"{analyzer}.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    analyzers[analyzer] = {
                        "status": "completed",
                        "file": f"{analyzer}.json",
                        "analyzed_at": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat(),
                        "file_size": json_file.stat().st_size
                    }
                except:
                    pass

        analysis_index["papers"][paper_id] = {
            "paper_id": paper_id,
            "analyzers": analyzers,
            "overall_status": "completed" if len(analyzers) == 5 else "partial"
        }

        print(f"✓ 迁移: {paper_id}")

    # 更新元数据
    analysis_index["metadata"]["total_papers"] = len(analysis_index["papers"])
    analysis_index["metadata"]["analyzed_papers"] = sum(
        1 for p in analysis_index["papers"].values()
        if p["overall_status"] == "completed"
    )

    # 保存索引
    index_file = target_all_dir / "analysis_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_index, f, indent=2, ensure_ascii=False)

    print(f"\n迁移完成:")
    print(f"  总论文数: {analysis_index['metadata']['total_papers']}")
    print(f"  完成数: {analysis_index['metadata']['analyzed_papers']}")
    print(f"  索引文件: {index_file}")

if __name__ == "__main__":
    migrate_to_all_structure()
```

### Step 3: 修改协调器支持分层结构（40分钟）

#### 3.1 修改 `analysis_coordinator_v2.py`

**添加 `output_subdir` 参数**:
```python
class AgentAnalysisCoordinatorV2:
    def __init__(
        self,
        markdown_root: Path,
        output_dir: str = "data/agent_results",
        output_subdir: str = "all",  # ⭐ NEW: "all" 或 "categories/{分类名}"
        ...
    ):
        self.output_root = Path(output_dir)
        self.output_subdir = output_subdir
        self.output_dir = self.output_root / output_subdir  # 完整路径
```

**添加分层支持的方法**:
```python
def _check_all_results(self, paper_id: str) -> dict:
    """检查 all/ 目录是否已有该论文的分析结果"""
    all_dir = self.output_root / "all" / paper_id

    if not all_dir.exists():
        return {"exists": False}

    result = {"exists": True}
    for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
        json_file = all_dir / f"{analyzer}.json"
        if json_file.exists():
            result[analyzer] = {
                "exists": True,
                "file": json_file,
                "analyzed_at": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
            }
        else:
            result[analyzer] = {"exists": False}

    return result

def _copy_from_all(self, paper_id: str, target_dir: Path):
    """从 all/ 复制分析结果到分类目录"""
    all_dir = self.output_root / "all" / paper_id
    target_paper_dir = target_dir / paper_id

    if target_paper_dir.exists():
        shutil.rmtree(target_paper_dir)

    shutil.copytree(all_dir, target_paper_dir)
    logger.info(f"✓ 从 all/ 复制: {paper_id}")
```

### Step 4: 修改 Page 2 GUI 支持分类选择（30分钟）

#### 4.1 添加分类选择功能

**参考 Page 1 的 MinerU 转换对话框**:

```python
def _select_analysis_target(self):
    """选择分析目标（all/ 或分类/）"""

    # 获取可用的分类列表
    categories_dir = self.project_dir / "markdown" / "categories"
    available_categories = ["all"]  # 默认选项

    if categories_dir.exists():
        for item in categories_dir.iterdir():
            if item.is_dir():
                available_categories.append(item.name)

    # 创建选择对话框
    dialog = tk.Toplevel(self.frame)
    dialog.title("选择分析目标")
    dialog.geometry("500x350")

    ttk.Label(dialog, text="请选择要分析的目标：", font=("", 10, "bold")).pack(pady=10)

    # 选择列表
    target_var = tk.StringVar(value="all")

    for category in available_categories:
        rb = ttk.Radiobutton(
            dialog,
            text=f"{'📚 all (全部文献)' if category == 'all' else f'📁 {category}'}",
            variable=target_var,
            value=category
        )
        rb.pack(anchor=tk.W, pady=5)

    def confirm():
        selected = target_var.get()
        self.analysis_target = selected
        dialog.destroy()
        self.log(f"✓ 已选择分析目标: {selected}")

    ttk.Button(dialog, text="确定", command=confirm).pack(pady=10)
```

### Step 5: 执行迁移（10分钟）

```bash
cd LiteratureHub
python scripts/migrate_analysis_results_v2.py
```

**预期输出**:
```
✓ 迁移: 2010_High-mode_Rayleigh-Taylor_growth_in_NIF_ignition_capsules
✓ 迁移: 2018_3D_numerical_simulation_of_aerodynamic_performance_of_iced_contaminated_wind_turbine_rotors
...
✓ 迁移: {paper_id_579}

迁移完成:
  总论文数: 579
  完成数: 579
  索引文件: data/agent_results/all/analysis_index.json
```

### Step 6: 验证与测试（20分钟）

#### 6.1 验证目录结构

```bash
# 检查 all/ 目录
ls data/agent_results/all/ | wc -l  # 应该是 579（不含索引文件）

# 检查索引文件
cat data/agent_results/all/analysis_index.json | jq ".metadata"
```

#### 6.2 测试分类分析

1. 启动 GUI
2. 切换到 Page 2
3. 点击「开始分析」
4. 选择分析目标（all/ 或 分类/）
5. 验证智能跳过逻辑

---

## 📊 最终效果

### GUI 界面

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 AI 深度分析（双层并发 + DeepSeek 无限并发）               │
├─────────────────────────────────────────────────────────────┤
│  路径与并发设置                                               │
│  Markdown 文献目录:                                          │
│  ┌─────────────────────────────────────┐ [🔍 自动检测]       │
│  │ markdown/all (默认，611 篇)         │                      │
│  └─────────────────────────────────────┘                      │
│                                                               │
│  分析目标: [● all (全部)]  ○ 大型风力机气动                   │
│  提示：分析分类时，会自动从 all/ 复制已有结果                   │
├─────────────────────────────────────────────────────────────┤
│  分析状态                                                     │
│  总论文数: 611   已分析: 579 (94.8%)   待分析: 32 (5.2%)   │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

```
┌─────────────────────────────────────────────────────────────┐
│  场景 A: 分析 all/                                           │
├─────────────────────────────────────────────────────────────┤
│  markdown/all/ → [分析] → agent_results/all/               │
│                      → 更新 agent_results/all/analysis_index   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  场景 B: 分析分类（大型风力机气动）                             │
├─────────────────────────────────────────────────────────────┤
│  markdown/categories/大型风力机气动/                          │
│      ↓                                                         │
│  ├─ 检查 agent_results/all/                                  │
│  │   ├─ 已有 → 复制到分类目录                                │
│  │   └─ 没有 → 分析到 all/，再复制到分类目录                 │
│  └─ 更新两个目录的索引文件                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 成功标准

- [ ] `agent_results/all/` 创建成功
- [ ] 579 篇已有结果迁移到 `all/`
- [ ] `all/analysis_index.json` 正确生成
- [ ] 协调器支持 `output_subdir` 参数
- [ ] GUI 支持选择分析目标（all/ 或分类）
- [ ] 分析分类时正确从 `all/` 复制已有结果
- [ ] 索引文件正确记录分析状态

---

## ⏱️ 时间估算

| 步骤 | 任务 | 预计时间 |
|------|------|---------|
| 1 | 创建目录结构 | 5分钟 |
| 2 | 创建迁移脚本 | 20分钟 |
| 3 | 修改协调器 | 40分钟 |
| 4 | 修改 GUI | 30分钟 |
| 5 | 执行迁移 | 10分钟 |
| 6 | 验证测试 | 20分钟 |
| **总计** | | **2小时5分钟** |

---

**这次的设计完全遵循 Page 1 的模式，笨蛋觉得怎么样？(￣▽￣)ノ**
