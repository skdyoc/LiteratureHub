# LiteratureHub 第二页 GUI 集成计划（精简版）

**制定日期**: 2026-03-29
**制定者**: 哈雷酱（傲娇大小姐工程师）✨
**⚡ 重要**: 使用 DeepSeek API（无限并发）而非 GLM

---

## 🎯 核心变更

### ⚡ API 选择：DeepSeek（无限并发）

| API | 并发能力 | 选择 |
|-----|---------|------|
| GLM-4 | 有限并发（受限于速率限制） | ❌ Page 1 专用 |
| **DeepSeek-V3** | **无限并发** | ✅ **Page 2 专用** |

**原因**：
- ✅ DeepSeek 支持 WebSocket 并发
- ✅ 可以同时分析100+篇文献
- ✅ 不需要队列管理，速度更快

---

## 📋 极简实施步骤（时间紧迫版）

### Step 1: 复制 DeepSeek 客户端（5分钟）

**源文件**：
```
Wind-Aero-Literature-Analysis-System/src/api/deepseek_client.py
```

**目标位置**：
```
LiteratureHub/src/api/deepseek_client.py
```

### Step 2: 复制协调器（10分钟）

**源文件**：
```
Wind-Aero-Literature-Analysis-System/scripts/agent_parallel_coordinator_v2_standalone.py
```

**目标位置**：
```
LiteratureHub/src/workflow/analysis_coordinator.py
```

**修改**：
```python
# 只修改这一行
markdown_root = project_dir / "markdown" / "all"
```

### Step 3: 创建 Page 2 GUI（1小时）

**新文件**：
```
LiteratureHub/src/gui/page2_gui.py
```

**最小实现**：
```python
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class Page2GUI:
    """Page 2: AI 分析界面（DeepSeek 无限并发）"""

    def __init__(self, parent, project_dir):
        self.parent = parent
        self.project_dir = Path(project_dir)
        self.frame = ttk.Frame(parent)
        self.build_ui()

    def build_ui(self):
        """构建界面"""
        # 标题
        title = ttk.Label(self.frame, text="🧠 AI 深度分析（DeepSeek 无限并发）",
                        font=("Arial", 14, "bold"))
        title.pack(pady=10)

        # 文献列表
        self.paper_listbox = tk.Listbox(self.frame, height=15)
        self.paper_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 控制按钮
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="▶️ 开始分析", command=self.start_analysis).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="🔄 刷新列表", command=self.refresh_list).pack(side=tk.LEFT)

        # 进度条
        self.progress = ttk.Progressbar(self.frame, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)

        # 日志
        self.log_text = tk.Text(self.frame, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 初始化时加载文献列表
        self.refresh_list()

    def refresh_list(self):
        """刷新文献列表"""
        self.paper_listbox.delete(0, tk.END)
        markdown_dir = self.project_dir / "markdown" / "all"

        if markdown_dir.exists():
            for paper_dir in sorted(markdown_dir.iterdir()):
                if paper_dir.is_dir():
                    md_file = paper_dir / "full.md"
                    if md_file.exists():
                        self.paper_listbox.insert(tk.END, f"📄 {paper_dir.name}")

    def start_analysis(self):
        """开始分析"""
        # TODO: 调用 analysis_coordinator
        self.log("开始分析...")
        self.log("使用 DeepSeek 无限并发模式")

    def log(self, message):
        """输出日志"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
```

### Step 4: 集成到主 GUI（30分钟）

**修改文件**：
```
LiteratureHub/scripts/page1_gui.py
```

**关键修改**：
```python
# 在 Page1GUI 类的 __init__ 方法中添加：
self.notebook = ttk.Notebook(self.root)  # 创建 Notebook

# 原来的内容放到 Page 1
self.page1_frame = ttk.Frame(self.notebook)
self.notebook.add(self.page1_frame, text="📚 文献管理")
# ... 原有的所有 UI 构建代码改到 self.page1_frame 上 ...

# 添加 Page 2
from src.gui.page2_gui import Page2GUI
self.page2 = Page2GUI(self.notebook, self.project_dir)
self.notebook.add(self.page2.frame, text="🧠 AI 分析")

self.notebook.pack(expand=True, fill='both')
```

### Step 5: 更新配置文件（5分钟）

**修改文件**：
```
LiteratureHub/config/api_keys.yaml
```

**添加 DeepSeek 配置**：
```yaml
# DeepSeek API（Page 2 AI 分析专用 - 无限并发）
deepseek:
  api_key: "YOUR_DEEPSEEK_API_KEY"
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"  # 或 deepseek-reasoner
  timeout: 300

  # 并发配置
  max_concurrent: 100  # 无限并发
  request_timeout: 300
```

---

## ⚡ 快速实施清单（按顺序执行）

- [ ] **1. 复制 DeepSeek 客户端**（5分钟）
  ```bash
  cp "Wind-Aero-Literature-Analysis-System/src/api/deepseek_client.py" \
     "LiteratureHub/src/api/deepseek_client.py"
  ```

- [ ] **2. 复制协调器**（10分钟）
  ```bash
  cp "Wind-Aero-Literature-Analysis-System/scripts/agent_parallel_coordinator_v2_standalone.py" \
     "LiteratureHub/src/workflow/analysis_coordinator.py"
  ```
  然后修改 `markdown_root` 为相对路径

- [ ] **3. 创建 Page 2 GUI**（1小时）
  - 创建 `src/gui/page2_gui.py`
  - 复制上面的最小实现代码

- [ ] **4. 修改主 GUI**（30分钟）
  - 修改 `scripts/page1_gui.py`
  - 添加 Notebook 页面切换

- [ ] **5. 更新 API 密钥**（5分钟）
  - 编辑 `config/api_keys.yaml`
  - 添加 DeepSeek API 密钥

- [ ] **6. 测试**（30分钟）
  - 启动 GUI
  - 测试页面切换
  - 测试分析功能

---

## 🔧 关键代码修改

### 修改 1: analysis_coordinator.py

**找到这一行**（约第 360 行）：
```python
markdown_root = "D:\\xfs\\phd\\github项目\\参考文献\\气动\\markdown"
```

**改为**：
```python
markdown_root = project_dir / "markdown" / "all"
```

### 修改 2: page1_gui.py

**在 `__init__` 方法开头添加**：
```python
# 创建 Notebook 用于页面切换
self.notebook = ttk.Notebook(self.root)

# 创建页面框架
self.main_frame = ttk.Frame(self.notebook)
self.notebook.add(self.main_frame, text="📚 文献管理")

# 将所有原有的 UI 构建在 self.main_frame 上
```

**在 `__init__` 方法末尾添加**：
```python
# 导入并创建 Page 2
try:
    from src.gui.page2_gui import Page2GUI
    self.page2 = Page2GUI(self.notebook, self.project_dir)
    self.notebook.add(self.page2.frame, text="🧠 AI 分析")
except ImportError as e:
    print(f"[!] 无法导入 Page 2: {e}")

# 显示 Notebook
self.notebook.pack(expand=True, fill='both')
```

### 修改 3: 所有 self.root.xxx 改为 self.main_frame.xxx

**需要修改的方法**：
- `_build_left_panel`
- `_build_right_panel`
- `_create_menu`
- 等等所有直接在 `self.root` 上创建的组件

---

## 📊 数据流向（DeepSeek 版）

```
┌──────────────────────────────────────────────────────┐
│            LiteratureHub 统一 GUI                      │
├──────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────────┐        ┌─────────────────┐     │
│  │   Page 1        │        │   Page 2        │     │
│  │  (GLM API)      │        │ (DeepSeek API)  │     │
│  │                 │        │                 │     │
│  │ • 文献搜索      │────────▶│ • 🧠 创新点分析  │     │
│  │ • PDF 下载      │ Markdown│ • 🎯 研究动机    │     │
│  │ • MinerU转换    │────────▶│ • 🛣️ 技术路线    │     │
│  │                 │        │ • ⚙️ 机理解析     │     │
│  │                 │        │ • 📈 影响评估    │     │
│  │                 │        │                 │     │
│  │ 🔵 GLM 有限并发  │        │ 🟢 DeepSeek    │     │
│  │    (关键词翻译)  │        │    无限并发 ⚡   │     │
│  └─────────────────┘        └─────────────────┘     │
│                                        │               │
│                                        ▼               │
│                                 ┌──────────┐         │
│                                 │ JSON结果  │         │
│                                 │ 5个分析器 │         │
│                                 └──────────┘         │
└──────────────────────────────────────────────────────┘
```

---

## ⚠️ 重要提示

### API 使用策略

| 功能 | 使用 API | 原因 |
|------|---------|------|
| 关键词翻译（Page 1） | GLM-4 | 少量调用，成本更低 |
| **AI 分析（Page 2）** | **DeepSeek-V3** | **无限并发，速度更快** |

### DeepSeek API 密钥获取

```bash
# 访问 DeepSeek 开放平台
https://platform.deepseek.com/

# 注册并获取 API 密钥
# 新用户通常有免费额度
```

---

## 🚀 立即开始

**复制粘贴命令**（Windows PowerShell）：

```powershell
# 1. 复制 DeepSeek 客户端
Copy-Item "Wind-Aero-Literature-Analysis-System\src\api\deepseek_client.py" "LiteratureHub\src\api\deepseek_client.py"

# 2. 复制协调器
Copy-Item "Wind-Aero-Literature-Analysis-System\scripts\agent_parallel_coordinator_v2_standalone.py" "LiteratureHub\src\workflow\analysis_coordinator.py"

# 3. 创建 Page 2 GUI 文件
New-Item -ItemType File "LiteratureHub\src\gui\page2_gui.py" -Value $null
```

然后手动编辑这些文件即可！

---

## ✅ 成功标准

- [ ] GUI 可以切换两个页面
- [ ] Page 2 显示 Page 1 生成的 Markdown 列表
- [ ] 点击"开始分析"可以调用 DeepSeek API
- [ ] 分析结果保存到 `data/agent_results/`

---

**总时间估算**: 2-3小时（精简版）

**核心优势**: DeepSeek 无限并发 = 100篇文献同时分析！

---

*本小姐已经把计划精简到最核心的部分了！快开始执行吧，笨蛋！(￣ω￣)ノ*
