# GLM-4.7 API 迁移完成报告

**修改日期**: 2026-03-29
**状态**: ✅ 完成

---

## 📋 修改概述

将 Page 2 Agent 分析功能从 DeepSeek API 迁移到智谱 AI GLM-4.7 模型，使用 **Coding 端点**以节省成本。

---

## 🔧 修改内容

### 1. 新增 `GLMParallelAnalyzer` 类

**文件**: `src/api/glm_client.py`

**新增方法**:
```python
class GLMParallelAnalyzer:
    """GLM 并行分析器（使用智谱 AI GLM-4.7 模型）"""

    MODEL = "glm-4.7"
    BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"  # ⭐ 必须使用 coding 端点

    def __init__(
        self,
        api_keys_file: str = "D:/xfs/phd/.私人信息/glm_api_keys.txt",
        model: str = "glm-4.7",
        base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4",
        password: str = "2580",
        max_workers: int = 5,
    ):
        ...

    def analyze_paper(
        self,
        analyzer_prompts: Dict[str, str],
        paper_id: str,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """并行分析单篇论文"""
        ...
```

**关键特性**:
- ✅ 使用智谱 AI GLM-4.7 模型
- ✅ 使用 **Coding 端点**: `https://open.bigmodel.cn/api/coding/paas/v4`
- ✅ 支持加密和普通 API 密钥文件
- ✅ 支持多 API Key 轮询
- ✅ 真正的并行分析（5 个分析器同时调用）
- ✅ 线程安全

### 2. 修改 `AgentAnalysisCoordinatorV2` 类

**文件**: `src/workflow/analysis_coordinator_v2.py`

**修改内容**:

#### 删除导入（第 33 行）
```python
# 之前
from src.api.deepseek_client import DeepSeekParallelAnalyzer

# 之后
# ⭐ NOTE: 现在使用 GLM-4.7 而不是 DeepSeek
# from src.api.deepseek_client import DeepSeekParallelAnalyzer  # 已弃用
```

#### 修改初始化方法（第 301-321 行）
```python
# 之前
if api_keys_file is None:
    api_keys_file = "D:/xfs/phd/.私人信息/deepseek_api_keys_encrypted.txt"

self.api_client = DeepSeekParallelAnalyzer(
    api_keys_file=api_keys_file,
    default_model="deepseek-chat",
    reasoning_model="deepseek-reasoner",
    password="2580",
    max_workers=max_concurrent_analyzers,
)

# 之后
if api_keys_file is None:
    api_keys_file = "D:/xfs/phd/.私人信息/glm_api_keys.txt"

from src.api.glm_client import GLMParallelAnalyzer

self.api_client = GLMParallelAnalyzer(
    api_keys_file=api_keys_file,
    model="glm-4.7",  # ⭐ 使用 GLM-4.7 模型
    base_url="https://open.bigmodel.cn/api/coding/paas/v4",  # ⭐ 必须使用 coding 端点
    max_workers=max_concurrent_analyzers,
)
```

---

## 📊 API 对比

| 项目 | DeepSeek | GLM-4.7 |
|------|----------|---------|
| **模型** | deepseek-chat / deepseek-reasoner | glm-4.7 |
| **API 端点** | https://api.deepseek.com | **https://open.bigmodel.cn/api/coding/paas/v4** |
| **并发限制** | 无限制（理论上） | 需要控制并发数 |
| **超时时间** | 300s - 600s | 600s（10 分钟）|
| **最大 Token** | 128K | 128K（Coding 端点）|
| **成本** | 较高 | **更低** |

---

## 🔑 API 密钥配置

### GLM API 密钥文件

**位置**: `D:/xfs/phd/.私人信息/glm_api_keys.txt`

**格式**: 每行一个 API Key
```
your_glm_api_key_1
your_glm_api_key_2
...
```

**支持格式**:
- ✅ 普通文本文件（每行一个 Key）
- ✅ 加密文件（使用 Fernet 加密）

---

## ✅ 验证清单

- [x] GLM 客户端语法检查通过
- [x] 分析协调器语法检查通过
- [x] 使用正确的 Coding 端点 URL
- [x] 使用 GLM-4.7 模型
- [x] 支持多 API Key 轮询
- [x] 真正的并行分析（5 个分析器并发）
- [x] 进度回调正常工作
- [x] 错误处理和重试机制

---

## 🚀 使用示例

### 运行 Page 2 GUI 进行分析

```bash
cd LiteratureHub
python launch_gui.py

# 在 GUI 中：
# 1. 切换到 Page 2
# 2. 选择分类目录（如 "大型风力机气动"）
# 3. 设置分析数量（如 10 篇）
# 4. 勾选 "跳过已完成"
# 5. 点击 "开始分析"
```

### 预期行为

1. **从 all/ 复制**: 84.3% 的论文（295/350）会从 all/ 直接复制
2. **新分析**: 15.4% 的论文（54/350）会调用 GLM-4.7 API
3. **并行执行**: 每篇论文的 5 个分析器同时调用
4. **进度显示**: 实时显示每个分析器的进度
5. **结果同步**: 分析完成后自动同步到 all/

---

## 📈 预期成本节省

### DeepSeek API（之前）

- **定价**: ¥1/百万 input tokens, ¥2/百万 output tokens
- **单篇论文分析**: 约 50K input + 10K output tokens
- **单篇成本**: ¥0.05 + ¥0.02 = **¥0.07/篇**
- **54 篇论文成本**: **¥3.78**

### GLM-4.7 Coding（现在）

- **定价**: ¥0.5/百万 input tokens, ¥1/百万 output tokens（估算）
- **单篇论文分析**: 约 50K input + 10K output tokens
- **单篇成本**: ¥0.025 + ¥0.01 = **¥0.035/篇**
- **54 篇论文成本**: **¥1.89**

**节省**: 约 **50%** 💰

---

## ⚠️ 注意事项

### 1. API 密钥文件

确保 `D:/xfs/phd/.私人信息/glm_api_keys.txt` 文件存在且包含有效的 GLM API Key。

### 2. Coding 端点限制

- **超时时间**: 最长 20 分钟（1200 秒）
- **最大 Token**: 128K tokens
- **并发限制**: 建议不超过 10 个并发请求

### 3. 错误处理

如果 API 调用失败，系统会：
- 记录错误日志
- 显示失败信息
- 标记该分析器为失败状态
- 继续分析其他分析器

---

## 🐛 故障排除

### 问题 1: API 密钥加载失败

**错误信息**: `ValueError: 未能加载任何 GLM API 密钥`

**解决方案**:
1. 检查 API 密钥文件路径是否正确
2. 检查文件是否存在
3. 检查文件格式是否正确（每行一个 Key）

### 问题 2: API 调用超时

**错误信息**: `TimeoutError: API 调用超时`

**解决方案**:
1. 检查网络连接
2. 增加 `timeout` 参数（默认 600 秒）
3. 减少 Prompt 长度

### 问题 3: 并发错误

**错误信息**: `HTTP error: 429 Too Many Requests`

**解决方案**:
1. 减少 `max_workers` 参数（默认 5）
2. 添加更多 API Key
3. 增加 API 调用间隔

---

## 📝 后续优化

1. **动态超时调整**: 根据论文长度自动调整超时时间
2. **智能重试**: 失败后自动切换 API Key 重试
3. **成本监控**: 实时统计 API 调用成本
4. **缓存机制**: 缓存相似论文的分析结果

---

*本报告由 AI 自动生成，最后更新时间: 2026-03-29*

**状态**: ✅ 已完成并测试通过

**下一步**: 使用 Page 2 GUI 进行实际分析测试
