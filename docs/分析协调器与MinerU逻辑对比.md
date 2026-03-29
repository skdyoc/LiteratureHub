# 分析协调器与 MinerU 逻辑对比说明

**创建日期**: 2026-03-29
**状态**: ✅ 已对齐

---

## 核心设计原则

**all/ 是主存储目录，categories/ 是副本**

- `all/` 存储所有论文的完整分析结果
- `categories/{category}/` 存储分类下的论文副本（从 all/ 复制或新分析后同步）
- 两个目录都各自维护 `analysis_index.json` 索引文件

---

## MinerU 的处理逻辑（参考标准）

位置：`src/workflow/page1_workflow.py` 第 1337-1428 行

### 处理流程

```python
# 步骤3: 遍历 PDF，判断处理方式
for pdf_file in pdf_files:
    # 检查 all/ 是否已有
    all_md_exists = (all_md_folder / "full.md").exists()
    is_converted_in_all = all_index.get(pdf_name, {}).get('is_converted', False)

    # 检查分类目录是否已有
    category_md_exists = (category_md_folder / "full.md").exists()
    is_converted_in_category = category_index.get(pdf_name, {}).get('is_converted', False)

    # 判断处理方式
    if category_md_exists and is_converted_in_category:
        # 1. 分类目录已存在 -> 跳过
        skipped += 1

    elif all_md_exists and is_converted_in_all:
        # 2. all/ 已存在，但分类目录没有 -> 复制
        shutil.copytree(all_md_folder, category_md_folder)
        # 更新分类索引
        copied_from_all += 1

    else:
        # 3. 都不存在 -> 转换
        success = self._convert_pdf_with_mineru(pdf_file, output_dir, md_folder_name)
        if success:
            # 同步到 all/（如果 all/ 里没有）
            if not all_md_exists:
                shutil.copytree(category_md_folder, all_md_folder)
                # 更新 all/ 索引
```

### 关键点

1. **优先检查分类目录**：已存在则跳过
2. **其次检查 all/ 目录**：存在则复制到分类目录
3. **最后进行新转换**：转换完成后同步到 all/

---

## 分析协调器的处理逻辑

位置：`src/workflow/analysis_coordinator_v2.py` 第 575-698 行

### 处理流程

```python
# 步骤1: 检查 all/ 是否已有结果（分类目录模式下）
if self.output_subdir != "all" and skip_completed:
    all_results = self._check_all_results(paper_id)

    if all_results.get("exists") and all_results.get("innovation", {}).get("exists"):
        # 1. all/ 已有完整结果 -> 复制到分类目录，跳过分析
        self._copy_from_all(paper_id, self.output_dir)
        # 加载复制后的结果
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            if all_results.get(analyzer, {}).get("exists"):
                results[analyzer] = self._load_cached_result(paper_id, analyzer)
        # 更新分类目录索引
        for analyzer in results:
            self._update_analysis_status(paper_id, analyzer, "completed")
        return results

    elif all_results.get("exists"):
        # 2. all/ 有部分结果 -> 复制已有的，分析缺失的
        # 复制已有的文件
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            if all_results.get(analyzer, {}).get("exists"):
                shutil.copy2(all_file, target_file)
                results[analyzer] = self._load_cached_result(paper_id, analyzer)
                self._update_analysis_status(paper_id, analyzer, "completed")
        # 继续分析缺失的部分...

# 步骤2: 确定需要运行的分析器（检查当前目录是否已完成）
analyzers_to_run = []
for analyzer in self.analyzers:
    if skip_completed and self._is_analyzer_completed(paper_id, analyzer):
        # 跳过已完成的
        if analyzer not in results:
            results[analyzer] = self._load_cached_result(paper_id, analyzer)
    else:
        analyzers_to_run.append(analyzer)

# 步骤3: 并行调用 DeepSeek API 分析缺失的部分
api_results = self.api_client.analyze_paper(...)

# 步骤4: 保存结果（自动同步到 all/）
for analyzer, api_result in api_results.items():
    if api_result.get("success"):
        self._save_result(paper_id, analyzer, results[analyzer])
        # _save_result 内部会：
        # 1. 保存到当前目录
        # 2. 同步到 all/（如果是分类目录）
        # 3. 更新两个索引
```

### 关键点

1. **优先检查 all/ 目录**：有完整结果则复制，有部分结果则复制并分析缺失的
2. **检查当前目录**：跳过已完成的，只分析缺失的
3. **保存结果时自动同步**：每次保存结果都会同步到 all/

---

## 关键差异与对齐

### 差异点

| 方面 | MinerU | 分析协调器 |
|------|--------|-----------|
| 检查顺序 | 分类 → all/ | all/ → 分类 |
| 同步时机 | 转换完成后同步 | 每个分析器完成后同步 |
| 同步单位 | 整个文件夹 | 单个分析器文件 |

### 对齐说明

1. **检查顺序差异**：合理差异
   - MinerU 先检查分类目录，因为分类目录是用户直接操作的
   - 分析协调器先检查 all/，因为 all/ 是主存储目录

2. **同步时机差异**：优化改进
   - MinerU 在整个转换完成后同步（一次性）
   - 分析协调器在每个分析器完成后同步（实时性更好）
   - 优势：如果分析中断，all/ 仍有已完成的分析器结果

3. **同步单位差异**：实现方式不同
   - MinerU 同步整个文件夹（因为所有文件同时生成）
   - 分析协调器同步单个文件（因为 5 个分析器独立完成）
   - 结果一致：最终 all/ 和 categories/ 都有完整的 5 个文件

---

## 新增方法

### `_update_analysis_status_in_dir`

```python
def _update_analysis_status_in_dir(self, paper_id: str, analyzer: str, status: str, result_file: Path, subdir: str):
    """
    更新指定目录的分析状态（线程安全）

    用于更新 all/ 或分类目录的索引文件
    """
    # 加载目标目录的索引
    # 更新论文分析器状态
    # 保存索引
```

### 功能

- 更新 `all/` 目录的 `analysis_index.json`
- 更新分类目录的 `analysis_index.json`
- 线程安全（使用 WRITE_LOCK）

---

## 修改的方法

### `_save_result`

**修改前**：
```python
def _save_result(self, paper_id: str, analyzer: str, result: Dict[str, Any]):
    # 只保存到当前目录
    result_file = paper_dir / f"{analyzer}.json"
    with open(result_file, "w") as f:
        json.dump(result, f)
    # 更新当前目录索引
    self._update_analysis_status(paper_id, analyzer, "completed", result_file)
```

**修改后**：
```python
def _save_result(self, paper_id: str, analyzer: str, result: Dict[str, Any]):
    # 1. 保存到当前目录
    result_file = paper_dir / f"{analyzer}.json"
    with open(result_file, "w") as f:
        json.dump(result, f)

    # 2. 如果是分类目录，同步到 all/
    if self.output_subdir != "all":
        all_result_file = all_dir / f"{analyzer}.json"
        shutil.copy2(result_file, all_result_file)
        # 更新 all/ 索引
        self._update_analysis_status_in_dir(paper_id, analyzer, status, all_result_file, "all")

    # 3. 更新当前目录索引
    self._update_analysis_status(paper_id, analyzer, status, result_file)
```

---

## 数据流图

```
┌──────────────────────────────────────────────────────────────────┐
│                      分析协调器处理流程                            │
└──────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │  步骤1: 检查 all/ 是否已有结果                                 │
   └─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ↓               ↓               ↓
      完整结果          部分结果          无结果
            │               │               │
            ↓               ↓               ↓
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │复制全部   │    │复制已有   │    │继续分析   │
    │跳过分析   │    │分析缺失   │    │所有缺失   │
    └──────────┘    └──────────┘    └──────────┘
                            │
                            ↓
            ┌───────────────────────────────┐
            │  步骤2: 并行调用 DeepSeek API  │
            └───────────────────────────────┘
                            │
                            ↓
            ┌───────────────────────────────┐
            │  步骤3: 保存结果              │
            │  - 保存到当前目录              │
            │  - 同步到 all/                │
            │  - 更新两个索引                │
            └───────────────────────────────┘
                            │
                            ↓
            ┌───────────────────────────────┐
            │  最终状态                      │
            │  - categories/ 有完整结果      │
            │  - all/ 有完整结果             │
            │  - 两个索引已更新              │
            └───────────────────────────────┘
```

---

## 验证清单

- [x] 分类目录分析完成后，结果同步到 all/
- [x] 失败的分析结果也同步到 all/
- [x] all/ 的索引文件正确更新
- [x] 分类目录的索引文件正确更新
- [x] 从 all/ 复制的结果正确加载
- [x] 线程安全（使用 WRITE_LOCK）
- [x] Python 语法检查通过

---

## 使用示例

### 场景 1: 分析分类目录中的论文

```bash
# 在分类目录 "Aerodynamic_Optimization" 中分析 10 篇论文
python scripts/page2_gui.py
# 选择: Aerodynamic_Optimization
# 分析数量: 10
# 跳过已完成: ✅

# 结果：
# 1. data/agent_results/categories/Aerodynamic_Optimization/{paper_id}/
#    - innovation.json, motivation.json, roadmap.json, mechanism.json, impact.json
# 2. data/agent_results/all/{paper_id}/
#    - innovation.json, motivation.json, roadmap.json, mechanism.json, impact.json (同步)
# 3. 两个目录的 analysis_index.json 都已更新
```

### 场景 2: 分析 all/ 中的论文

```bash
# 在 all/ 目录中分析 10 篇论文
python scripts/page2_gui.py
# 选择: all
# 分析数量: 10
# 跳过已完成: ✅

# 结果：
# 1. data/agent_results/all/{paper_id}/
#    - innovation.json, motivation.json, roadmap.json, mechanism.json, impact.json
# 2. all/ 的 analysis_index.json 已更新
# 3. 不同步到其他目录（因为当前就是 all/）
```

### 场景 3: 从 all/ 复制到分类目录

```bash
# 在分类目录 "Aerodynamic_Optimization" 中分析
# 但 all/ 中已有该论文的完整分析结果

# 结果：
# 1. 自动从 all/ 复制到 categories/Aerodynamic_Optimization/
# 2. 跳过 API 调用（节省成本）
# 3. 分类目录的索引已更新
```

---

*本文档由 AI 自动生成，最后更新时间: 2026-03-29*
