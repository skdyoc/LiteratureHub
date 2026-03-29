# LiteratureHub GUI 使用说明

## 快速启动

### 方式 1：双击启动（Windows）
双击项目根目录下的 `启动GUI.bat` 文件

### 方式 2：命令行启动
```bash
cd d:\xfs\phd\github项目\LiteratureHub
python launch_gui.py
```

## 界面功能

### 左侧面板 - 控制区

#### 📊 仪表盘
显示项目统计信息：
- 文献总数
- 已下载 / 下载率
- 已分类 / 分类数
- Markdown 文件数

#### 🎛️ 工作流操作
1. **Elsevier 搜索** - 搜索学术文献
2. **SciHub 下载** - 批量下载 PDF
3. **处理临时文件** - 处理手动下载的 PDF
4. **手动下载列表** - 生成手动下载列表
5. **文献分类** - 智能分类文献
6. **MinerU 转换** - PDF 转 Markdown

#### 📊 进度和日志
- 实时显示操作进度
- 日志窗口显示详细操作信息

### 右侧面板 - 数据区

#### 🔍 搜索栏
- 支持关键词搜索
- 过滤：全部 / 已下载 / 未下载

#### 📋 文献列表
显示字段：
- 年份
- 标题
- 作者
- 期刊
- PDF 状态（是/否）
- DOI

#### 📄 文献详情
双击列表项查看详细信息

## 使用流程

### 完整工作流程

```
1. Elsevier 搜索 → 获取文献列表
2. SciHub 下载 → 自动下载 PDF
3. 处理临时文件 → 处理手动下载的 PDF
4. 文献分类 → 按主题分类
5. MinerU 转换 → 转为 Markdown 格式
```

### 详细步骤

#### Step 1: 搜索文献
1. 点击「1. Elsevier 搜索」
2. 输入关键词（支持中文，会自动翻译）
3. 设置年份范围
4. 选择匹配模式：
   - 匹配字段：标题 / 关键词 / 摘要
   - 组合模式：全部匹配(AND) / 至少一个(OR)
5. 点击「翻译预览」查看翻译结果
6. 点击「搜索」开始搜索

#### Step 2: 下载 PDF
1. 点击「2. SciHub 下载」
2. 系统会自动：
   - 优先使用 Unpaywall（合法、免费）
   - 失败后使用 SciHub（需要代理）
   - 自动检测并启动 Mihomo 代理
3. 等待下载完成
4. 查看下载统计

#### Step 3: 处理失败的下载
如果某些文献下载失败：
1. 系统会自动导出 NoteExpress 格式列表
2. 手动下载 PDF 到 `pdfs/temp/` 目录
3. 点击「3. 处理临时文件」
4. 系统会自动匹配并重命名文件

#### Step 4: 分类文献
1. 点击「5. 文献分类」
2. 输入分类名称（如：large_scale_aero）
3. 系统会基于内容智能分类

#### Step 5: 转换为 Markdown
1. 点击「6. MinerU 转换」
2. 等待转换完成（可能需要较长时间）
3. Markdown 文件保存在 `markdown/` 目录

## 配置说明

### API 密钥配置

编辑 `config/api_keys.yaml`：

```yaml
# Unpaywall 邮箱（用于开放获取文献下载）
unpaywall:
  email: "your-email@example.com"

# Elsevier API（用于文献搜索）
elsevier:
  api_key: "your_elsevier_api_key"

# GLM API（用于关键词翻译，可选）
glm:
  api_keys:
    - "your_glm_api_key"
```

### 代理配置

系统会自动检测以下代理：
- Mihomo (127.0.0.1:7890)
- 其他 HTTP/SOCKS5 代理

如果使用 Mihomo：
- 确保可执行文件在 `D:/mihomo/mihomo.exe`
- 配置文件在 `C:/Users/19874/.config/clash/profiles/`
- 系统会自动启动

## 常见问题

### Q1: GUI 启动失败
**A**: 检查 Python 版本（需要 3.9+）和依赖：
```bash
python --version
pip install -r requirements.txt
```

### Q2: 搜索返回 0 结果
**A**: 检查：
- Elsevier API 密钥是否正确
- 关键词是否太宽泛
- 尝试使用英文关键词

### Q3: 下载失败
**A**: 可能的原因：
- 文献太新（2025-2026 年）→ SciHub 尚未收录
- 代理未启动 → 系统会自动尝试启动 Mihomo
- DOI 不存在 → 检查文献元数据

### Q4: 中文关键词搜索不工作
**A**: 系统会自动翻译中文关键词为英文。
如果翻译失败，请配置 GLM API 密钥。

### Q5: 如何取消操作
**A**: GUI 没有取消按钮，只能关闭程序重启。

## 系统测试

运行系统测试验证所有组件：

```bash
python test_system.py
```

应该看到：
```
✅ 通过 - 模块导入
✅ 通过 - 配置文件
✅ 通过 - 下载组件
✅ 通过 - 搜索组件
✅ 通过 - 工作流
✅ 通过 - GUI
```

## 技术架构

```
GUI (Tkinter)
    ↓
Page1Workflow (工作流管理器)
    ↓
├── ElsevierSearcher (文献搜索)
├── KeywordTranslationAgent (关键词翻译)
└── MultiSourceDownloader (多源下载)
    ├── UnpaywallClient (开放获取)
    └── SciHubDownloader (备用)
        └── ProxyManager (代理管理)
            └── VPNDetector (VPN 检测和自动启动)
```

## 下载策略

1. **Unpaywall 优先**
   - 合法、免费
   - 不需要 VPN
   - 约 20-30% 的文献有开放获取版本

2. **SciHub 备用**
   - 需要 VPN
   - 自动检测并启动 Mihomo
   - 支持新的 SciHub 格式（2024+）

3. **智能代理**
   - 并发测试所有代理
   - 自动选择延迟最低的
   - 每 10 篇自动切换

## 文件组织

```
data/projects/wind_aero/
├── pdfs/
│   ├── all/              # 所有 PDF 文件
│   ├── temp/             # 手动下载的临时文件
│   └── categories/       # 分类后的 PDF
├── markdown/             # Markdown 格式文献
├── metadata/             # 搜索结果元数据
└── exports/              # 导出的列表和报告
```

---

*最后更新: 2026-03-28*
*版本: 1.0*
