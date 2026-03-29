"""
Agent 并行分析协调器 V2 - 双层并发版本
Agent Parallel Analysis Coordinator V2 - Dual-Layer Concurrency

改进：
1. 外层并发：同时处理 10 篇论文
2. 内层并发：每篇论文的 5 个分析器并发
3. 总并发：10 × 5 = 50 个 agent 请求
4. 线程安全：文件写入、进度更新使用锁保护
"""

import sys
import io
import json
import time
import os
import shutil
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ⭐ NOTE: 现在使用 GLM-4.7 而不是 DeepSeek
# from src.api.deepseek_client import DeepSeekParallelAnalyzer  # 已弃用

# 设置日志
logger = logging.getLogger("AgentAnalysisV2")
logger.setLevel(logging.INFO)

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 文件处理器
file_handler = logging.FileHandler(log_dir / "agent_analysis_v2.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# 添加处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ============================================================================
# 全局线程锁（保护共享资源）
# ============================================================================

WRITE_LOCK = threading.Lock()  # 保护文件写入
PROGRESS_LOCK = threading.Lock()  # 保护进度更新
LOG_LOCK = threading.Lock()  # 保护日志输出（确保顺序）


# ============================================================================
# 分析进度跟踪器（线程安全版本）
# ============================================================================

class AnalysisProgressTracker:
    """分析进度跟踪器 - 线程安全版本"""

    def __init__(
        self,
        progress_file: str = "data/analysis_progress_v2.json",
        output_dir: str = "data/agent_results",
    ):
        self.progress_file = Path(progress_file)
        self.output_dir = Path(output_dir)
        self.progress_data = self._load_progress()
        # 启动时自动同步
        self.sync_from_files()

    def _load_progress(self) -> Dict:
        """加载进度数据"""
        with PROGRESS_LOCK:
            if self.progress_file.exists():
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {
                "total_papers": 0,
                "completed_papers": [],
                "failed_papers": [],
                "last_update": None,
            }

    def _save_progress(self):
        """保存进度数据（线程安全）"""
        with PROGRESS_LOCK:
            self.progress_data["last_update"] = datetime.now().isoformat()
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)

    def sync_from_files(self):
        """
        从实际文件同步进度记录

        扫描输出目录，将实际存在的文件标记为已完成
        这确保进度记录与实际文件状态一致
        """
        if not self.output_dir.exists():
            return

        with PROGRESS_LOCK:
            completed_set = set(self.progress_data.get("completed_papers", []))
            new_completed = []

            # 扫描输出目录中的所有论文文件夹
            for paper_dir in self.output_dir.iterdir():
                if not paper_dir.is_dir():
                    continue

                paper_id = paper_dir.name

                # 检查该论文的每个分析器输出文件
                for analyzer in [
                    "innovation",
                    "motivation",
                    "roadmap",
                    "mechanism",
                    "impact",
                ]:
                    result_file = paper_dir / f"{analyzer}.json"
                    if result_file.exists():
                        key = f"{paper_id}/{analyzer}"
                        if key not in completed_set:
                            new_completed.append(key)
                            completed_set.add(key)

            # 更新进度记录
            if new_completed:
                self.progress_data.setdefault("completed_papers", []).extend(new_completed)
                self._save_progress()
                logger.info(f"从实际文件同步了 {len(new_completed)} 个已完成任务")

    def is_completed(self, paper_id: str, analyzer: str) -> bool:
        """
        检查某个论文的某个分析器是否已完成

        基于实际文件存在性，而非内存记录

        Args:
            paper_id: 论文ID
            analyzer: 分析器名称

        Returns:
            bool: 文件是否存在且有效
        """
        # 检查实际文件是否存在
        result_file = self.output_dir / paper_id / f"{analyzer}.json"

        if not result_file.exists():
            return False

        # 验证文件内容是否有效（非空JSON）
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 检查是否有基本结构，不是空的错误文件
                if isinstance(data, dict) and len(data) > 0:
                    # 排除只有raw_text的错误文件
                    if "raw_text" in data and len(data) == 1:
                        return False
                    return True
                return False
        except (json.JSONDecodeError, Exception):
            return False

    def mark_completed(self, paper_id: str, analyzer: str):
        """
        标记某个论文的某个分析器为已完成（线程安全）

        验证文件实际创建成功后才标记
        """
        # 首先验证文件确实存在且有效
        result_file = self.output_dir / paper_id / f"{analyzer}.json"

        if not result_file.exists():
            logger.warning(f"文件不存在，无法标记完成: {result_file}")
            return

        # 验证文件内容
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data or (isinstance(data, dict) and len(data) <= 1):
                    logger.warning(f"文件内容无效，无法标记完成: {result_file}")
                    return
        except Exception as e:
            logger.warning(f"文件读取失败，无法标记完成: {result_file}, 错误: {e}")
            return

        # 文件验证通过，标记为完成（使用锁保护）
        with PROGRESS_LOCK:
            key = f"{paper_id}/{analyzer}"
            if key not in self.progress_data.get("completed_papers", []):
                self.progress_data.setdefault("completed_papers", []).append(key)
                self._save_progress()

                # 线程安全的日志输出
                with LOG_LOCK:
                    logger.info(f"✓ 已标记完成: {paper_id}/{analyzer}")

    def mark_failed(self, paper_id: str, analyzer: str, error: str):
        """标记某个论文的某个分析器为失败（线程安全）"""
        with PROGRESS_LOCK:
            key = f"{paper_id}_{analyzer}"
            self.progress_data.setdefault("failed_papers", []).append(
                {"key": key, "error": error, "timestamp": datetime.now().isoformat()}
            )
            self._save_progress()

    def get_progress(self) -> Dict:
        """获取当前进度（线程安全）"""
        with PROGRESS_LOCK:
            total = self.progress_data.get("total_papers", 0)
            completed = len(self.progress_data.get("completed_papers", []))
            # 5个分析器
            total_tasks = total * 5
            completed_tasks = completed
            return {
                "total": total_tasks,
                "completed": completed_tasks,
                "percentage": (completed_tasks / total_tasks * 100)
                if total_tasks > 0
                else 0,
            }


# ============================================================================
# Agent 分析协调器 V2 - 双层并发版本
# ============================================================================

class AgentAnalysisCoordinatorV2:
    """Agent 分析协调器 V2 - 双层并发版本"""

    def __init__(
        self,
        markdown_root: Path,  # ⭐ NEW: Markdown 目录（从 Page 1 传入）
        output_dir: str = "data/agent_results",
        output_subdir: str = "all",  # ⭐ NEW: 输出子目录 ("all" 或 "categories/{分类名}")
        analyzers: List[str] = None,
        max_concurrent_papers: int = 10,  # ⭐ NEW: 外层并发数
        max_concurrent_analyzers: int = 5,  # ⭐ NEW: 内层并发数
        api_keys_file: Optional[str] = None,  # ⭐ NEW: API 密钥文件路径
        prompts_dir: Optional[str] = None,  # ⭐ NEW: Prompt 模板目录
        api_type: str = "glm",  # ⭐ NEW: API 类型 ("glm" 或 "deepseek")
    ):
        """
        初始化协调器 V2

        Args:
            markdown_root: Markdown 目录路径（从 Page 1 的输出目录传入）
            output_dir: 结果输出根目录
            output_subdir: 输出子目录 ("all" 或 "categories/{分类名}")
            analyzers: 要运行的分析器列表
            max_concurrent_papers: 最大并发论文数（外层）
            max_concurrent_analyzers: 每篇论文的最大并发分析器数（内层）
            api_keys_file: DeepSeek API 密钥文件路径
            prompts_dir: Prompt 模板目录路径
        """
        self.markdown_root = Path(markdown_root)
        self.output_root = Path(output_dir)
        self.output_subdir = output_subdir
        self.output_dir = self.output_root / output_subdir  # 完整输出路径
        self.analyzers = analyzers or [
            "innovation",
            "motivation",
            "roadmap",
            "mechanism",
            "impact",
        ]

        # ⭐ NEW: 双层并发配置
        self.max_concurrent_papers = max_concurrent_papers  # 外层：10篇论文并发
        self.max_concurrent_analyzers = max_concurrent_analyzers  # 内层：5个分析器并发

        # 计算理论最大并发数
        self.max_total_concurrent = max_concurrent_papers * max_concurrent_analyzers

        # 将 output_dir 传递给进度跟踪器
        self.tracker = AnalysisProgressTracker(output_dir=output_dir)

        # ⭐ NEW: 可配置的 API 密钥文件路径
        if api_keys_file is None:
            # 默认路径：尝试多个可能的 GLM API 密钥文件
            possible_paths = [
                "D:/xfs/phd/github项目/.私人信息/glm_api_keys_all.txt",
                "D:/xfs/phd/github项目/.私人信息/glm_api_key.txt",
                "D:/xfs/phd/.私人信息/glm_api_keys.txt",
                "D:/xfs/phd/github项目/LiteratureHub/config/api_keys.yaml",
            ]
            # 找到第一个存在的文件
            for path in possible_paths:
                if Path(path).exists():
                    api_keys_file = path
                    break
            else:
                api_keys_file = "D:/xfs/phd/github项目/.私人信息/glm_api_keys_all.txt"

        # ⭐ NEW: 根据 api_type 选择不同的 API 客户端
        self.api_type = api_type
        self.api_client = None
        api_init_success = False

        if api_type == "glm":
            # 使用智谱 GLM-4.7
            try:
                logger.info("初始化 GLM-4.7 并行分析器 V2...")
                from src.api.glm_client import GLMParallelAnalyzer

                self.api_client = GLMParallelAnalyzer(
                    api_keys_file=api_keys_file,
                    model="glm-4.7",
                    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
                    max_workers=max_concurrent_analyzers,
                )
                logger.info("GLM-4.7 API 客户端初始化成功（使用 coding 端点）")
                api_init_success = True
            except Exception as e:
                logger.error(f"GLM API 客户端初始化失败: {e}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                self.api_client = None

        elif api_type == "deepseek":
            # 使用 DeepSeek-V3
            try:
                logger.info("初始化 DeepSeek-V3 并行分析器...")
                from src.api.deepseek_client import DeepSeekParallelAnalyzer

                # ⭐ 修复：使用正确的路径
                possible_deepseek_paths = [
                    "D:/xfs/phd/github项目/.私人信息/deepseek_api_keys_encrypted.txt",
                    "D:/xfs/phd/.私人信息/deepseek_api_keys_encrypted.txt",
                ]

                deepseek_keys_file = None
                for path in possible_deepseek_paths:
                    if Path(path).exists():
                        deepseek_keys_file = path
                        break

                if deepseek_keys_file is None:
                    raise FileNotFoundError(f"未找到 DeepSeek API 密钥文件，已检查路径: {possible_deepseek_paths}")

                logger.info(f"使用 DeepSeek 密钥文件: {deepseek_keys_file}")

                self.api_client = DeepSeekParallelAnalyzer(
                    api_keys_file=deepseek_keys_file,
                    default_model="deepseek-chat",
                    reasoning_model="deepseek-reasoner",
                    password="2580",
                    max_workers=max_concurrent_analyzers,
                )
                logger.info("DeepSeek-V3 API 客户端初始化成功")
                api_init_success = True
            except Exception as e:
                logger.error(f"DeepSeek API 客户端初始化失败: {e}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                self.api_client = None
        else:
            logger.error(f"未知的 API 类型: {api_type}")
            self.api_client = None

        # ⭐ NEW: 如果 API 初始化失败，抛出异常阻止继续执行
        if self.api_client is None:
            error_msg = f"{api_type.upper()} API 初始化失败！请检查 API 密钥配置或切换到其他 API。"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # ⭐ BUG修复: API初始化成功后才创建输出目录！
        # （之前在line 301创建目录，导致API失败时目录仍被创建）
        logger.info(f"API 初始化成功，创建输出目录: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ 输出目录已创建: {self.output_dir}")

        # ⭐ NEW: 可配置的 Prompt 目录
        if prompts_dir is None:
            # 默认路径：src/prompts/analysis/
            prompts_dir = Path("src/prompts/analysis")
        else:
            prompts_dir = Path(prompts_dir)

        # 分析器配置（使用可配置的 Prompt 路径）
        self.analyzer_config = {
            "innovation": {
                "agent_type": "ai-engineer",
                "prompt_file": str(prompts_dir / "innovation.txt"),
            },
            "motivation": {
                "agent_type": "data-science:business-analyst",
                "prompt_file": str(prompts_dir / "motivation.txt"),
            },
            "roadmap": {
                "agent_type": "backend-development:backend-architect",
                "prompt_file": str(prompts_dir / "roadmap.txt"),
            },
            "mechanism": {
                "agent_type": "code-explain",
                "prompt_file": str(prompts_dir / "mechanism.txt"),
            },
            "impact": {
                "agent_type": "observability-monitoring:performance-engineer",
                "prompt_file": str(prompts_dir / "impact.txt"),
            },
        }

        # 进度回调函数
        self.progress_callback = None

        logger.info(f"协调器 V2 初始化完成:")
        logger.info(f"  - API 类型: {api_type.upper()}")
        logger.info(f"  - 分析器: {self.analyzers}")
        logger.info(f"  - 外层并发: {max_concurrent_papers} 篇论文")
        logger.info(f"  - 内层并发: {max_concurrent_analyzers} 个分析器")
        logger.info(f"  - 理论最大并发: {self.max_total_concurrent} 个请求")

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def _notify_progress(self, message: str, progress: float = None):
        """通知进度更新（线程安全）"""
        if self.progress_callback:
            try:
                self.progress_callback(message, progress)
            except Exception as e:
                with LOG_LOCK:
                    logger.warning(f"进度回调失败: {e}")

    def _on_analyzer_progress(
        self, analyzer: str, status: str, is_start: bool, paper_id: str
    ):
        """
        处理分析器级别的进度更新（线程安全）

        Args:
            analyzer: 分析器名称
            status: 状态描述
            is_start: True表示开始，False表示完成/失败
            paper_id: 论文ID
        """
        # 记录到日志（线程安全）
        with LOG_LOCK:
            if is_start:
                logger.info(f"🔄 [{paper_id}/{analyzer}] 开始分析...")
            else:
                logger.info(f"  [{paper_id}] {status}")

        # 通知GUI（实时更新）
        analyzer_names = {
            "innovation": "创新点分析",
            "motivation": "动机分析",
            "roadmap": "技术路线分析",
            "mechanism": "机理解析",
            "impact": "影响评估",
        }

        analyzer_cn = analyzer_names.get(analyzer, analyzer)

        if is_start:
            self._notify_progress(f"🔄 {analyzer_cn} 分析中...", None)
        else:
            self._notify_progress(f"✓ {analyzer_cn} {status}", None)

    def _load_papers_from_markdown(self) -> List:
        """
        ⭐ NEW: 从 Markdown 目录加载论文列表

        扫描 markdown_root 目录，读取所有 full.md 文件
        返回简化的 Paper 对象列表（不依赖数据库）

        Returns:
            List[SimplePaper]: 简化的 Paper 对象列表
        """
        papers = []

        if not self.markdown_root.exists():
            logger.error(f"Markdown 目录不存在: {self.markdown_root}")
            return []

        logger.info(f"从 Markdown 目录加载论文: {self.markdown_root}")
        logger.info(f"开始扫描目录...")

        # 扫描 Markdown 目录
        paper_dirs = [d for d in sorted(self.markdown_root.iterdir()) if d.is_dir()]
        total_dirs = len(paper_dirs)
        logger.info(f"发现 {total_dirs} 个文件夹，开始加载...")

        for i, paper_dir in enumerate(paper_dirs, 1):
            if not paper_dir.is_dir():
                continue

            md_file = paper_dir / "full.md"
            if not md_file.exists():
                continue

            try:
                # 读取 Markdown 内容
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 创建简化的 Paper 对象（不依赖数据库）
                class SimplePaper:
                    def __init__(self, folder_name, content):
                        self.folder_name = folder_name

                        # 提取标题（第一行 # 后面）
                        self.title = "Unknown"
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip().startswith('#'):
                                self.title = line.lstrip('#').strip()
                                break

                        # 元数据
                        class Metadata:
                            def __init__(self, title):
                                self.title = title
                                self.authors = []
                                self.year = None
                                self.journal = None
                                self.rank = None
                                self.score = None

                        self.metadata = Metadata(self.title)

                        # 内容
                        class Content:
                            def __init__(self, content):
                                self.full_text = content
                                self.abstract = ""
                                self.keywords = []
                                self.introduction = ""
                                self.conclusion = ""

                        self.content = Content(content)

                papers.append(SimplePaper(paper_dir.name, content))

                # ⭐ 每加载 10 篇输出一次进度
                if i % 10 == 0 or i == total_dirs:
                    logger.info(f"  加载进度: {i}/{total_dirs} ({i/total_dirs*100:.1f}%)")

            except Exception as e:
                logger.warning(f"加载论文 {paper_dir.name} 失败: {e}")
                continue

        logger.info(f"✓ 从 Markdown 目录加载了 {len(papers)} 篇论文")
        return papers

    def load_prompt_template(self, prompt_file: str) -> str:
        """加载 Prompt 模板"""
        prompt_path = Path(prompt_file)
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def prepare_paper_context(self, paper) -> Dict[str, Any]:
        """准备论文上下文"""
        return {
            "title": paper.metadata.title,
            "authors": paper.metadata.authors,
            "year": paper.metadata.year,
            "journal": paper.metadata.journal,
            "abstract": paper.content.abstract or "",
            "keywords": paper.content.keywords or [],
            "introduction": (paper.content.introduction or "")[:1000],
            "conclusion": (paper.content.conclusion or "")[:500],
        }

    def _save_result(self, paper_id: str, analyzer: str, result: Dict[str, Any]):
        """
        保存分析结果到论文专属文件夹（线程安全）

        新的文件结构：data/agent_results/{output_subdir}/{paper_id}/{analyzer}.json

        ⭐ NEW: 与 MinerU 相同的逻辑
        1. 保存到当前目录
        2. 如果是分类目录，同步到 all/
        3. 更新两个索引
        """
        # 使用锁保护文件写入
        with WRITE_LOCK:
            # 创建论文专属文件夹
            paper_dir = self.output_dir / paper_id
            paper_dir.mkdir(parents=True, exist_ok=True)

            # 保存到论文专属文件夹
            result_file = paper_dir / f"{analyzer}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.debug(f"结果已保存: {result_file}")

            # ⭐ NEW: 与 MinerU 相同的同步逻辑
            # 如果当前是分类目录（不是 all/），则同步到 all/
            if self.output_subdir != "all":
                all_dir = self.output_root / "all" / paper_id
                all_result_file = all_dir / f"{analyzer}.json"

                # 同步到 all/
                all_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(result_file, all_result_file)

                logger.debug(f"已同步到 all/: {all_result_file}")

                # ⭐ NEW: 更新 all/ 索引
                if result.get("success"):
                    self._update_analysis_status_in_dir(paper_id, analyzer, "completed", all_result_file, "all")
                else:
                    self._update_analysis_status_in_dir(paper_id, analyzer, "failed", all_result_file, "all")

        # ⭐ NEW: 更新当前目录的索引
        if result.get("success"):
            self._update_analysis_status(paper_id, analyzer, "completed", result_file)
        else:
            self._update_analysis_status(paper_id, analyzer, "failed", result_file)

    def _load_cached_result(self, paper_id: str, analyzer: str) -> Dict[str, Any]:
        """
        加载已缓存的分析结果

        新的文件结构：data/agent_results/{paper_id}/{analyzer}.json
        """
        # 创建论文专属文件夹
        paper_dir = self.output_dir / paper_id
        result_file = paper_dir / f"{analyzer}.json"

        if result_file.exists():
            with open(result_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"success": False, "error": "Result file not found"}

    def analyze_single_paper(
        self, paper, skip_completed: bool = True
    ) -> Dict[str, Any]:
        """
        分析单篇论文（所有分析器并行）- 线程安全版本

        ⭐ NEW: 支持从 all/ 复制已有结果（分类目录场景）

        Args:
            paper: 论文对象
            skip_completed: 是否跳过已完成的分析器

        Returns:
            分析结果字典
        """
        # 🔔 DEBUG: 方法入口
        paper_id = paper.folder_name
        with LOG_LOCK:
            logger.info(f"[DEBUG] analyze_single_paper 方法入口: paper_id={paper_id}, skip_completed={skip_completed}")

        paper_context = self.prepare_paper_context(paper)

        with LOG_LOCK:
            logger.info(f"开始分析论文: {paper.metadata.title[:50]}...")
        self._notify_progress(f"正在分析: {paper.metadata.title[:50]}...", None)

        results = {}

        # 🔔 DEBUG: 输出配置信息
        with LOG_LOCK:
            logger.info(f"[DEBUG] output_subdir={self.output_subdir}, skip_completed={skip_completed}")

        # ⭐ NEW: 分类目录智能处理（检查 all/ 是否已有结果）
        if self.output_subdir != "all" and skip_completed:
            with LOG_LOCK:
                logger.info(f"检查 all/ 目录是否已有 {paper_id} 的分析结果...")

            all_results = self._check_all_results(paper_id)

            # 🔔 DEBUG: 输出 all_results
            with LOG_LOCK:
                logger.info(f"[DEBUG] all_results exists={all_results.get('exists')}, innovation exists={all_results.get('innovation', {}).get('exists')}")

            if all_results.get("exists") and all_results.get("innovation", {}).get("exists"):
                # all/ 已有完整结果，直接复制
                with LOG_LOCK:
                    logger.info(f"✓ 从 all/ 复制完整结果: {paper_id}")

                self._copy_from_all(paper_id, self.output_dir)

                # 加载复制后的结果
                for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
                    if all_results.get(analyzer, {}).get("exists"):
                        results[analyzer] = self._load_cached_result(paper_id, analyzer)

                # ⭐ 照抄MinerU: 只在内存中更新索引，不频繁保存
                # 在单篇论文场景下，我们延迟更新索引，让调用方决定何时保存
                # 这样可以避免每次复制都写索引（从1475次IO减少到1次）

                # 🔔 DEBUG: 返回结果
                with LOG_LOCK:
                    logger.info(f"[DEBUG] 从 all/ 复制完成，返回 {len(results)} 个分析器结果")

                return results

            elif all_results.get("exists"):
                # all/ 有部分结果，复制已有的，分析缺失的
                with LOG_LOCK:
                    logger.info(f"✓ 从 all/ 复制部分结果: {paper_id}")

                # 复制已有的
                for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
                    if all_results.get(analyzer, {}).get("exists"):
                        # 从 all/ 复制单个文件
                        all_file = self.output_root / "all" / paper_id / f"{analyzer}.json"
                        target_file = self.output_dir / paper_id / f"{analyzer}.json"

                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(all_file, target_file)

                        results[analyzer] = self._load_cached_result(paper_id, analyzer)

                        # 更新状态
                        self._update_analysis_status(paper_id, analyzer, "completed")

                # 继续分析缺失的部分
                with LOG_LOCK:
                    completed_analyzers = list(results.keys())
                    logger.info(f"已复制 {len(completed_analyzers)} 个分析器，继续分析剩余的")

        # 确定需要运行的分析器
        analyzers_to_run = []
        for analyzer in self.analyzers:
            # 检查当前目录是否已完成
            if skip_completed and self._is_analyzer_completed(paper_id, analyzer):
                with LOG_LOCK:
                    logger.info(f"跳过已完成的 {analyzer} 分析")
                # 从文件加载已有结果
                if analyzer not in results:
                    results[analyzer] = self._load_cached_result(paper_id, analyzer)
            else:
                analyzers_to_run.append(analyzer)

        # 🔔 DEBUG: 输出需要运行的分析器
        with LOG_LOCK:
            logger.info(f"[DEBUG] 需要运行的分析器: {analyzers_to_run}, 已有结果: {list(results.keys())}")

        # 🔔 DEBUG: 如果所有分析器都已完成，直接返回
        if not analyzers_to_run and results:
            with LOG_LOCK:
                logger.info(f"[DEBUG] 所有分析器都已完成，直接返回 {len(results)} 个结果")
            return results

        # 使用 DeepSeek API 并行运行所有分析器
        if self.api_client and analyzers_to_run:
            # 🔔 DEBUG: 准备调用 API
            with LOG_LOCK:
                logger.info(f"[DEBUG] 准备调用 API，分析器数量: {len(analyzers_to_run)}")

            # 真正的 API 调用
            analyzer_prompts = {}
            for analyzer in analyzers_to_run:
                # 加载 Prompt 模板
                prompt_template = self.load_prompt_template(
                    self.analyzer_config[analyzer]["prompt_file"]
                )
                # 构建完整的 Prompt
                full_prompt = f"{prompt_template}\n\n论文数据:\n{json.dumps(paper_context, indent=2, ensure_ascii=False)}"
                analyzer_prompts[analyzer] = full_prompt

            # 🔔 DEBUG: 调用 API
            with LOG_LOCK:
                logger.info(f"[DEBUG] 调用 api_client.analyze_paper...")

            # 并行调用 API（带实时进度回调）
            api_results = self.api_client.analyze_paper(
                analyzer_prompts=analyzer_prompts,
                paper_id=paper_id,
                progress_callback=lambda analyzer, status, is_start: self._on_analyzer_progress(
                    analyzer, status, is_start, paper_id
                ),
            )

            # 🔔 DEBUG: API 返回
            with LOG_LOCK:
                logger.info(f"[DEBUG] API 返回，结果数量: {len(api_results)}")

            # 处理结果
            for analyzer, api_result in api_results.items():
                if api_result.get("success"):
                    results[analyzer] = {
                        "success": True,
                        "result": api_result["result"],
                        "analyzer_type": self.analyzer_config[analyzer]["agent_type"],
                        "parsed": api_result.get("parsed", False),
                        "usage": api_result.get("usage", {}),
                    }

                    # ✅ 保存结果到文件（线程安全）
                    self._save_result(paper_id, analyzer, results[analyzer])

                    # ✅ 标记完成（线程安全）
                    self.tracker.mark_completed(paper_id, analyzer)

                    with LOG_LOCK:
                        logger.info(f"{analyzer} 分析完成")
                else:
                    results[analyzer] = {
                        "success": False,
                        "error": api_result.get("error", "Unknown error"),
                        "analyzer_type": self.analyzer_config[analyzer]["agent_type"],
                    }

                    # ✅ 标记失败（线程安全）
                    error_msg = api_result.get("error", "Unknown error")
                    self.tracker.mark_failed(paper_id, analyzer, error_msg)

                    with LOG_LOCK:
                        logger.error(f"{analyzer} 分析失败: {error_msg}")
        else:
            # 🔔 DEBUG: 没有调用 API
            with LOG_LOCK:
                logger.info(f"[DEBUG] 没有调用 API: api_client={self.api_client is not None}, analyzers_to_run={len(analyzers_to_run)}")

        # 🔔 DEBUG: 方法即将返回
        with LOG_LOCK:
            logger.info(f"[DEBUG] analyze_single_paper 方法即将返回，结果数量: {len(results)}")

        return results

    def batch_analyze(
        self,
        max_papers: Optional[int] = None,
        skip_completed: bool = True,
        ranked_papers: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        批量分析所有论文 - 双层并发版本

        外层：同时处理 10 篇论文
        内层：每篇论文的 5 个分析器并发
        总并发：10 × 5 = 50 个请求

        Args:
            max_papers: 最大分析数量（None表示全部）
            skip_completed: 是否跳过已完成的论文
            ranked_papers: 评分排名数据（如果提供，按排名顺序分析）

        Returns:
            统计信息
        """
        with LOG_LOCK:
            logger.info("=" * 80)
            logger.info("开始批量 Agent 分析（双层并发 V2）")
            logger.info(f"外层并发: {self.max_concurrent_papers} 篇论文")
            logger.info(f"内层并发: {self.max_concurrent_analyzers} 个分析器")
            logger.info(f"理论最大并发: {self.max_total_concurrent} 个请求")
            logger.info("=" * 80)

        # ⭐ 记录开始时间（修复未定义变量bug）
        start_time = time.time()

        # ⭐ NEW: 从 Markdown 目录加载论文（不使用数据库）
        with LOG_LOCK:
            logger.info(f"从 Markdown 目录加载论文: {self.markdown_root}")

        papers = self._load_papers_from_markdown()

        if not papers:
            logger.error("没有找到论文，请检查 Markdown 目录")
            return {"total": 0, "completed": 0, "failed": 0}

        with LOG_LOCK:
            logger.info(f"✓ 从 Markdown 目录加载了 {len(papers)} 篇论文")
            logger.info(f"总共 {len(papers)} 篇论文待分析")

        # ✨ 如果提供了排名数据，按排名顺序排序
        if ranked_papers:
            with LOG_LOCK:
                logger.info(f"✓ 使用评分排名顺序分析 {len(ranked_papers)} 篇文献")

            # 创建论文ID到索引的映射
            paper_id_to_index = {p.folder_name: i for i, p in enumerate(papers)}

            # 按排名顺序重新排序
            ranked_paper_ids = [item.get("paper_id", "") for item in ranked_papers]
            ranked_papers_list = []
            for paper_id in ranked_paper_ids:
                if paper_id in paper_id_to_index:
                    paper = papers[paper_id_to_index[paper_id]]
                    # 添加排名和评分信息
                    rank_info = next((item for item in ranked_papers if item.get("paper_id") == paper_id), {})
                    paper.metadata.rank = rank_info.get("rank", 0)
                    paper.metadata.score = rank_info.get("score", 0.0)
                    ranked_papers_list.append(paper)

            # 使用排序后的列表
            if max_papers:
                papers = ranked_papers_list[:max_papers]
            else:
                papers = ranked_papers_list

            with LOG_LOCK:
                logger.info(f"✓ 按排名加载了 {len(papers)} 篇文献")
                if ranked_papers_list:
                    logger.info(f"  最高分: {ranked_papers_list[0].metadata.score:.1f}分" if ranked_papers_list[0].metadata.score else "  最高分: N/A")
                    logger.info(f"  最低分: {ranked_papers_list[-1].metadata.score:.1f}分" if ranked_papers_list[-1].metadata.score else "  最低分: N/A")
        else:
            # 原有逻辑：使用所有论文
            if max_papers:
                papers = papers[:max_papers]

        # 更新进度跟踪器
        self.tracker.progress_data["total_papers"] = len(papers)
        self.tracker._save_progress()

        with LOG_LOCK:
            logger.info(f"总共 {len(papers)} 篇论文待分析")

        # ⭐ 照抄 Wind-Aero：简化逻辑，不做预检查！直接进入并发执行
        # 所有论文都通过 analyze_single_paper 处理，skip_completed 在那里判断
        with LOG_LOCK:
            logger.info(f"总共 {len(papers)} 篇论文待分析")

        # ⭐ NEW: 双层并发执行
        all_results = []
        # start_time 已在方法开始时定义（第873行），这里不重复定义

        # 用于跟踪进度
        completed_count = [0]  # 使用列表以便在闭包中修改
        failed_count = [0]

        with LOG_LOCK:
            logger.info(f"准备启动外层并发处理...")
            logger.info(f"  - 外层并发数: {self.max_concurrent_papers}")
            logger.info(f"  - 内层并发数: {self.max_concurrent_analyzers}")
            logger.info(f"  - 理论最大并发: {self.max_total_concurrent}")
            logger.info(f"  - API 客户端: {'GLM-4.7' if self.api_client else 'None (模拟模式)'}")
            logger.info(f"开始提交论文到线程池...")

        def process_paper(paper, index):
            """处理单篇论文（用于线程池）"""
            try:
                # 🔔 DEBUG: 任务开始执行
                with LOG_LOCK:
                    logger.info(f"[DEBUG] [{index+1}/{len(papers)}] 任务开始执行: {paper.folder_name[:40]}...")

                # ✨ 显示排名信息（如果有）
                rank_info = ""
                if hasattr(paper.metadata, "rank") and paper.metadata.rank:
                    score_info = (
                        f" ({paper.metadata.score:.1f}分)"
                        if hasattr(paper.metadata, "score")
                        else ""
                    )
                    rank_info = f" [#{paper.metadata.rank}{score_info}]"

                # 更新进度
                with PROGRESS_LOCK:
                    current_completed = completed_count[0]
                    progress = self.tracker.get_progress()
                    self._notify_progress(
                        f"分析进度: {current_completed}/{len(papers)}{rank_info}",
                        progress["percentage"]
                    )

                # 🔔 DEBUG: 准备调用 analyze_single_paper
                with LOG_LOCK:
                    logger.info(f"[DEBUG] [{index+1}/{len(papers)}] 准备调用 analyze_single_paper: {paper.folder_name[:40]}...")

                # 分析论文（内层并发：5个分析器）
                results = self.analyze_single_paper(paper, skip_completed)

                # 🔔 DEBUG: analyze_single_paper 返回
                with LOG_LOCK:
                    logger.info(f"[DEBUG] [{index+1}/{len(papers)}] analyze_single_paper 返回: {paper.folder_name[:40]}... 返回了 {len(results)} 个分析器结果")

                # 更新完成计数
                with PROGRESS_LOCK:
                    completed_count[0] += 1

                return {
                    "paper_id": paper.folder_name,
                    "title": paper.metadata.title,
                    "rank": getattr(paper.metadata, "rank", None),
                    "score": getattr(paper.metadata, "score", None),
                    "results": results,
                    "success": True,
                }

            except Exception as e:
                with LOG_LOCK:
                    logger.error(f"分析论文 {paper.folder_name} 失败: {e}")

                with PROGRESS_LOCK:
                    failed_count[0] += 1

                return {
                    "paper_id": paper.folder_name,
                    "title": paper.metadata.title,
                    "error": str(e),
                    "success": False,
                }

        # ⭐ NEW: 使用线程池外层并发处理多篇论文
        with LOG_LOCK:
            logger.info(f"创建线程池（外层并发）: max_workers={self.max_concurrent_papers}")

        with ThreadPoolExecutor(max_workers=self.max_concurrent_papers) as executor:
            # 提交所有任务
            future_to_paper = {}

            with LOG_LOCK:
                logger.info(f"开始提交 {len(papers)} 篇论文到线程池...")

            for i, paper in enumerate(papers):
                future = executor.submit(process_paper, paper, i)
                future_to_paper[future] = paper

                # ⭐ 每 10 篇输出一次进度
                if (i + 1) % 10 == 0 or i == 0:
                    with LOG_LOCK:
                        logger.info(f"  已提交 {i+1}/{len(papers)} 篇论文到线程池...")

            with LOG_LOCK:
                logger.info(f"所有任务已提交，等待完成...")
                logger.info(f"开始收集结果（按完成顺序）...")

            # 收集结果（按完成顺序）
            completed_in_loop = 0
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]

                try:
                    # ⭐ 在获取结果前添加日志
                    with LOG_LOCK:
                        completed_in_loop += 1
                        logger.info(f"[{completed_in_loop}/{len(papers)}] 论文分析完成，正在获取结果: {paper.folder_name[:40]}...")

                    result = future.result()
                    all_results.append(result)

                    if result.get("success"):
                        with LOG_LOCK:
                            logger.info(
                                f"✓ 论文分析完成: {paper.metadata.title[:50]}... "
                                f"({completed_count[0]}/{len(papers)})"
                            )
                    else:
                        with LOG_LOCK:
                            logger.error(
                                f"✗ 论文分析失败: {paper.metadata.title[:50]}... "
                                f"错误: {result.get('error', 'Unknown')}"
                            )

                except Exception as e:
                    with LOG_LOCK:
                        logger.error(f"处理论文 {paper.folder_name} 时发生异常: {e}")

        # 统计
        elapsed_time = time.time() - start_time

        # ⭐ 照抄 Wind-Aero：简化统计
        total_papers = len(papers)
        analyzed_papers = completed_count[0]

        with LOG_LOCK:
            logger.info("=" * 80)
            logger.info("批量分析完成！")
            logger.info(f"总论文数: {total_papers}")
            logger.info(f"成功: {analyzed_papers} 篇")
            logger.info(f"失败: {failed_count[0]} 篇")
            logger.info(f"总耗时: {elapsed_time:.2f} 秒")
            logger.info(f"平均每篇: {elapsed_time / total_papers:.2f} 秒")
            logger.info("=" * 80)

        return {
            "total": total_papers,
            "completed": analyzed_papers,
            "failed": failed_count[0],
            "elapsed_time": elapsed_time,
            "avg_time_per_paper": elapsed_time / total_papers if total_papers else 0,
            "results": all_results,
        }

    # ⭐ NEW: 分层结构支持方法

    def _load_analysis_index(self) -> Dict:
        """加载分析索引文件（如果不存在则自动创建）"""
        index_file = self.output_dir / "analysis_index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载索引失败: {e}")

        # ⭐ 文件不存在或加载失败，创建新索引
        logger.info(f"创建新的分析索引文件: {index_file}")

        new_index = {
            "metadata": {
                "version": "2.0",
                "analyzers": ["innovation", "motivation", "roadmap", "mechanism", "impact"],
                "total_papers": 0,
                "analyzed_papers": 0,
                "pending_papers": 0,
                "partial_papers": 0,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "source": f"AgentAnalysisV2 ({self.output_subdir})"
            },
            "papers": {}
        }

        # ⭐ 保存新索引到文件
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(new_index, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ 已创建分析索引文件: {index_file}")
        except Exception as e:
            logger.error(f"创建索引文件失败: {e}")

        return new_index

    def _save_analysis_index(self, index: Dict):
        """保存分析索引文件（线程安全）"""
        with WRITE_LOCK:
            index_file = self.output_dir / "analysis_index.json"
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
    def _is_analyzer_completed(self, paper_id: str, analyzer: str) -> bool:
        """检查某个论文的某个分析器是否已完成"""
        # 先检查当前目录的索引
        index = self._load_analysis_index()

        if paper_id in index["papers"]:
            if analyzer in index["papers"][paper_id]["analyzers"]:
                return index["papers"][paper_id]["analyzers"][analyzer]["status"] == "completed"

        return False

    def _check_all_results(self, paper_id: str) -> Dict:
        """检查 all/ 目录是否已有该论文的分析结果"""
        all_dir = self.output_root / "all" / paper_id

        # 🔔 DEBUG: 检查目录是否存在
        if not all_dir.exists():
            logger.debug(f"[DEBUG] _check_all_results: {paper_id} - all_dir 不存在: {all_dir}")
            return {"exists": False}

        result = {"exists": True}
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            json_file = all_dir / f"{analyzer}.json"
            if json_file.exists():
                result[analyzer] = {
                    "exists": True,
                    "file": str(json_file),
                    "analyzed_at": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                }
            else:
                result[analyzer] = {"exists": False}

        # 🔔 DEBUG: 输出结果
        logger.debug(f"[DEBUG] _check_all_results: {paper_id} - exists={result['exists']}, " +
                    f"innovation={result.get('innovation', {}).get('exists')}, " +
                    f"motivation={result.get('motivation', {}).get('exists')}, " +
                    f"roadmap={result.get('roadmap', {}).get('exists')}, " +
                    f"mechanism={result.get('mechanism', {}).get('exists')}, " +
                    f"impact={result.get('impact', {}).get('exists')}")

        return result

    def _copy_from_all(self, paper_id: str, target_dir: Path):
        """
        从 all/ 复制分析结果到分类目录（线程安全）

        ⭐ 优化：不持有全局锁做耗时操作（rmtree/copytree）
        """
        all_dir = self.output_root / "all" / paper_id
        target_paper_dir = target_dir / paper_id

        # 🔔 DEBUG: 复制开始
        with LOG_LOCK:
            logger.info(f"[DEBUG] _copy_from_all 开始: {paper_id}")
            logger.info(f"[DEBUG] all_dir={all_dir}")
            logger.info(f"[DEBUG] target_paper_dir={target_paper_dir}")
            logger.info(f"[DEBUG] all_dir exists: {all_dir.exists()}")

        if not all_dir.exists():
            with LOG_LOCK:
                logger.error(f"[ERROR] all/ 目录不存在: {all_dir}")
            raise FileNotFoundError(f"all/ 目录不存在: {all_dir}")

        # ⭐ 优化：先检查源目录大小
        try:
            all_size = sum(f.stat().st_size for f in all_dir.rglob('*') if f.is_file())
            with LOG_LOCK:
                logger.info(f"[DEBUG] all/ 目录大小: {all_size / 1024:.1f} KB")
        except Exception as e:
            with LOG_LOCK:
                logger.warning(f"[WARNING] 无法计算目录大小: {e}")

        # ⭐ 优化：不持有锁做耗时操作
        try:
            # 删除现有目录（不持有锁）
            if target_paper_dir.exists():
                with LOG_LOCK:
                    logger.info(f"[DEBUG] 删除现有目录: {target_paper_dir}")
                shutil.rmtree(target_paper_dir)

            # 复制目录（不持有锁）
            with LOG_LOCK:
                logger.info(f"[DEBUG] 开始复制文件...")
            shutil.copytree(all_dir, target_paper_dir)
            with LOG_LOCK:
                logger.info(f"[DEBUG] 复制完成")
        except Exception as e:
            with LOG_LOCK:
                logger.error(f"[ERROR] 复制失败: {e}")
            raise

        with LOG_LOCK:
            logger.info(f"✓ 从 all/ 复制: {paper_id}")

    def _rebuild_analysis_index_after_copy(self, papers: List):
        """
        批量复制后重建分析索引（按照MinerU的逻辑）

        扫描所有复制过来的论文文件夹，一次性重建索引，避免逐个更新。

        Args:
            papers: 复制过来的论文列表
        """
        with WRITE_LOCK:
            with LOG_LOCK:
                logger.info(f"[DEBUG] 开始重建索引，论文数量: {len(papers)}")

            # 加载现有索引（如果存在）
            index = self._load_analysis_index()

            # 更新元数据
            index["metadata"]["total_papers"] = len(papers)
            index["metadata"]["last_updated"] = datetime.now().isoformat()

            # 重建论文条目
            for paper in papers:
                paper_id = paper.folder_name
                paper_dir = self.output_dir / paper_id

                if not paper_dir.exists():
                    with LOG_LOCK:
                        logger.warning(f"[WARNING] 论文目录不存在: {paper_dir}")
                    continue

                # 检查5个分析器文件
                analyzers = ["innovation", "motivation", "roadmap", "mechanism", "impact"]
                completed_analyzers = []

                for analyzer in analyzers:
                    result_file = paper_dir / f"{analyzer}.json"
                    if result_file.exists():
                        try:
                            # 验证文件内容
                            with open(result_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            if data and isinstance(data, dict) and len(data) > 0:
                                completed_analyzers.append(analyzer)
                        except Exception as e:
                            with LOG_LOCK:
                                logger.warning(f"[WARNING] 无法读取 {result_file.name}: {e}")

                # 更新论文条目
                if completed_analyzers:
                    index["papers"][paper_id] = {
                        "paper_id": paper_id,
                        "analyzers": {},
                        "overall_status": "pending"
                    }

                    for analyzer in completed_analyzers:
                        result_file = paper_dir / f"{analyzer}.json"
                        index["papers"][paper_id]["analyzers"][analyzer] = {
                            "status": "completed",
                            "file": f"{analyzer}.json",
                            "analyzed_at": datetime.fromtimestamp(result_file.stat().st_mtime).isoformat(),
                            "file_size": result_file.stat().st_size
                        }

                    # 更新整体状态
                    if len(completed_analyzers) == 5:
                        index["papers"][paper_id]["overall_status"] = "completed"
                        index["papers"][paper_id]["completed_at"] = datetime.fromtimestamp(result_file.stat().st_mtime).isoformat()
                    elif len(completed_analyzers) > 0:
                        index["papers"][paper_id]["overall_status"] = "partial"

            # 更新元数据统计
            index["metadata"]["analyzed_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "completed"
            )
            index["metadata"]["partial_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "partial"
            )

            # 保存索引
            self._save_analysis_index(index)

            with LOG_LOCK:
                logger.info(f"[DEBUG] 索引重建完成: {len(index['papers'])} 篇论文")

    def _batch_update_index(self, index_updates: Dict[str, List[str]]):
        """
        批量更新分析索引（避免频繁IO操作）

        Args:
            index_updates: {paper_id: [analyzer1, analyzer2, ...]}
        """
        with WRITE_LOCK:
            with LOG_LOCK:
                logger.info(f"[DEBUG] 开始批量更新索引，论文数量: {len(index_updates)}")

            # 加载一次索引
            index = self._load_analysis_index()

            # 更新所有论文的状态
            updated_count = 0
            for paper_id, analyzers in index_updates.items():
                # 确保论文条目存在
                if paper_id not in index["papers"]:
                    index["papers"][paper_id] = {
                        "paper_id": paper_id,
                        "analyzers": {},
                        "overall_status": "pending"
                    }

                # 更新所有分析器状态
                for analyzer in analyzers:
                    result_file = self.output_dir / paper_id / f"{analyzer}.json"
                    if result_file.exists():
                        index["papers"][paper_id]["analyzers"][analyzer] = {
                            "status": "completed",
                            "file": f"{analyzer}.json",
                            "analyzed_at": datetime.now().isoformat(),
                            "file_size": result_file.stat().st_size
                        }
                        updated_count += 1

                # 更新整体状态
                completed_count = sum(
                    1 for a in index["papers"][paper_id]["analyzers"].values()
                    if a["status"] == "completed"
                )
                total_analyzers = 5
                if completed_count == total_analyzers:
                    index["papers"][paper_id]["overall_status"] = "completed"
                    index["papers"][paper_id]["completed_at"] = datetime.now().isoformat()
                elif completed_count > 0:
                    index["papers"][paper_id]["overall_status"] = "partial"

            # 更新元数据
            index["metadata"]["analyzed_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "completed"
            )
            index["metadata"]["partial_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "partial"
            )
            index["metadata"]["last_updated"] = datetime.now().isoformat()

            # 保存一次索引
            self._save_analysis_index(index)

            with LOG_LOCK:
                logger.info(f"[DEBUG] 批量索引更新完成: {updated_count} 个分析器状态")

    def _update_analysis_status(self, paper_id: str, analyzer: str, status: str, result_file: Path = None):
        """更新分析状态（线程安全）"""
        with WRITE_LOCK:
            index = self._load_analysis_index()

            # 确保论文条目存在
            if paper_id not in index["papers"]:
                index["papers"][paper_id] = {
                    "paper_id": paper_id,
                    "analyzers": {},
                    "overall_status": "pending"
                }

            # 更新分析器状态
            if result_file and result_file.exists():
                index["papers"][paper_id]["analyzers"][analyzer] = {
                    "status": status,
                    "file": f"{analyzer}.json",
                    "analyzed_at": datetime.now().isoformat(),
                    "file_size": result_file.stat().st_size
                }

            # 更新整体状态
            completed_count = sum(
                1 for a in index["papers"][paper_id]["analyzers"].values()
                if a["status"] == "completed"
            )
            total_analyzers = 5
            if completed_count == total_analyzers:
                index["papers"][paper_id]["overall_status"] = "completed"
                index["papers"][paper_id]["completed_at"] = datetime.now().isoformat()
            elif completed_count > 0:
                index["papers"][paper_id]["overall_status"] = "partial"

            # 更新元数据
            index["metadata"]["analyzed_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "completed"
            )
            index["metadata"]["partial_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "partial"
            )
            index["metadata"]["last_updated"] = datetime.now().isoformat()

            # 保存索引
            self._save_analysis_index(index)

    def _update_analysis_status_in_dir(self, paper_id: str, analyzer: str, status: str, result_file: Path, subdir: str):
        """
        更新指定目录的分析状态（线程安全）

        Args:
            paper_id: 论文ID
            analyzer: 分析器名称
            status: 状态（completed/failed）
            result_file: 结果文件路径
            subdir: 子目录名称（all/ 或分类目录）
        """
        with WRITE_LOCK:
            # 加载指定目录的索引
            target_dir = self.output_root / subdir
            index_file = target_dir / "analysis_index.json"

            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                # 如果索引文件不存在，创建新的
                index = {
                    "papers": {},
                    "metadata": {
                        "version": "2.0",
                        "analyzers": ["innovation", "motivation", "roadmap", "mechanism", "impact"],
                        "total_papers": 0,
                        "analyzed_papers": 0,
                        "partial_papers": 0,
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "source": f"synced_from_{self.output_subdir}"
                    }
                }

            # 确保论文条目存在
            if paper_id not in index["papers"]:
                index["papers"][paper_id] = {
                    "paper_id": paper_id,
                    "analyzers": {},
                    "overall_status": "pending"
                }

            # 更新分析器状态
            if result_file and result_file.exists():
                index["papers"][paper_id]["analyzers"][analyzer] = {
                    "status": status,
                    "file": f"{analyzer}.json",
                    "analyzed_at": datetime.now().isoformat(),
                    "file_size": result_file.stat().st_size
                }

            # 更新整体状态
            completed_count = sum(
                1 for a in index["papers"][paper_id]["analyzers"].values()
                if a["status"] == "completed"
            )
            total_analyzers = 5
            if completed_count == total_analyzers:
                index["papers"][paper_id]["overall_status"] = "completed"
                index["papers"][paper_id]["completed_at"] = datetime.now().isoformat()
            elif completed_count > 0:
                index["papers"][paper_id]["overall_status"] = "partial"

            # 更新元数据
            index["metadata"]["analyzed_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "completed"
            )
            index["metadata"]["partial_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "partial"
            )
            index["metadata"]["last_updated"] = datetime.now().isoformat()

            # 保存索引到目标目录
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)

            logger.debug(f"已更新 {subdir}/ 索引: {paper_id} - {analyzer} - {status}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数 - 测试双层并发"""
    import argparse

    parser = argparse.ArgumentParser(description="Agent 分析协调器 V2 - 双层并发")
    parser.add_argument("--max-papers", type=int, default=10, help="最大分析数量")
    parser.add_argument("--skip-completed", action="store_true", help="跳过已完成的论文")
    parser.add_argument("--concurrent-papers", type=int, default=10, help="并发论文数（外层）")
    parser.add_argument("--concurrent-analyzers", type=int, default=5, help="并发分析器数（内层）")

    args = parser.parse_args()

    # 创建协调器
    coordinator = AgentAnalysisCoordinatorV2(
        database_path="data/database.db",
        max_concurrent_papers=args.concurrent_papers,
        max_concurrent_analyzers=args.concurrent_analyzers,
    )

    # 加载排名数据
    ranked_papers_file = Path("data/analysis_results/ranked_papers.json")
    ranked_papers = None

    if ranked_papers_file.exists():
        with open(ranked_papers_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            ranked_papers = data.get("ranked_papers", [])
        logger.info(f"✓ 加载了 {len(ranked_papers)} 篇排名文献")

    # 执行分析
    stats = coordinator.batch_analyze(
        max_papers=args.max_papers,
        skip_completed=args.skip_completed,
        ranked_papers=ranked_papers,
    )

    # 输出统计
    print("\n" + "=" * 80)
    print("分析完成统计:")
    print(f"  总数: {stats['total']} 篇")
    print(f"  成功: {stats['completed']} 篇")
    print(f"  失败: {stats['failed']} 篇")
    print(f"  总耗时: {stats['elapsed_time']:.2f} 秒")
    print(f"  平均每篇: {stats['avg_time_per_paper']:.2f} 秒")
    print("=" * 80)


if __name__ == "__main__":
    main()
