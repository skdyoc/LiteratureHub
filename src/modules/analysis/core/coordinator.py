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
import threading
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

from src.core.database import LiteratureDatabase
from src.utils.logger import setup_logger, get_logger
from src.api.deepseek_client import DeepSeekParallelAnalyzer

logger = setup_logger(log_file="logs/agent_analysis_v2.log")


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
        database_path: str,
        output_dir: str = "data/agent_results",
        analyzers: List[str] = None,
        max_concurrent_papers: int = 10,  # ⭐ NEW: 外层并发数
        max_concurrent_analyzers: int = 5,  # ⭐ NEW: 内层并发数
    ):
        """
        初始化协调器 V2

        Args:
            database_path: 数据库路径
            output_dir: 结果输出目录
            analyzers: 要运行的分析器列表
            max_concurrent_papers: 最大并发论文数（外层）
            max_concurrent_analyzers: 每篇论文的最大并发分析器数（内层）
        """
        self.database_path = database_path
        self.output_dir = Path(output_dir)
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

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 使用 DeepSeek API（从加密文件加载密钥）
        try:
            logger.info("初始化 DeepSeek 混合并行分析器 V2...")
            self.api_client = DeepSeekParallelAnalyzer(
                api_keys_file="D:/xfs/phd/.私人信息/deepseek_api_keys_encrypted.txt",  # 明确指定路径
                default_model="deepseek-chat",
                reasoning_model="deepseek-reasoner",
                password="2580",
                max_workers=max_concurrent_analyzers,  # 内层并发数
            )
            logger.info("DeepSeek API 客户端初始化成功")
        except Exception as e:
            logger.error(f"DeepSeek API 客户端初始化失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            logger.warning("将使用模拟模式")
            self.api_client = None

        # 分析器配置
        self.analyzer_config = {
            "innovation": {
                "agent_type": "ai-engineer",
                "prompt_file": "prompts/innovation_analyzer.txt",
            },
            "motivation": {
                "agent_type": "data-science:business-analyst",
                "prompt_file": "prompts/motivation_detector.txt",
            },
            "roadmap": {
                "agent_type": "backend-development:backend-architect",
                "prompt_file": "prompts/roadmap_analyzer.txt",
            },
            "mechanism": {
                "agent_type": "code-explain",
                "prompt_file": "prompts/mechanism_analyzer.txt",
            },
            "impact": {
                "agent_type": "observability-monitoring:performance-engineer",
                "prompt_file": "prompts/impact_assessor.txt",
            },
        }

        # 进度回调函数
        self.progress_callback = None

        logger.info(f"协调器 V2 初始化完成:")
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

        新的文件结构：data/agent_results/{paper_id}/{analyzer}.json
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

        Args:
            paper: 论文对象
            skip_completed: 是否跳过已完成的分析器

        Returns:
            分析结果字典
        """
        paper_id = paper.folder_name
        paper_context = self.prepare_paper_context(paper)

        with LOG_LOCK:
            logger.info(f"开始分析论文: {paper.metadata.title[:50]}...")
        self._notify_progress(f"正在分析: {paper.metadata.title[:50]}...", None)

        results = {}

        # 确定需要运行的分析器
        analyzers_to_run = []
        for analyzer in self.analyzers:
            if skip_completed and self.tracker.is_completed(paper_id, analyzer):
                with LOG_LOCK:
                    logger.info(f"跳过已完成的 {analyzer} 分析")
                # 从文件加载已有结果
                results[analyzer] = self._load_cached_result(paper_id, analyzer)
            else:
                analyzers_to_run.append(analyzer)

        # 使用 DeepSeek API 并行运行所有分析器
        if self.api_client:
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

            # 并行调用 API（带实时进度回调）
            api_results = self.api_client.analyze_paper(
                analyzer_prompts=analyzer_prompts,
                paper_id=paper_id,
                progress_callback=lambda analyzer, status, is_start: self._on_analyzer_progress(
                    analyzer, status, is_start, paper_id
                ),
            )

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

        # 连接数据库
        db = LiteratureDatabase(self.database_path)
        db.connect()

        # ✨ 如果提供了排名数据，使用排名顺序
        if ranked_papers:
            with LOG_LOCK:
                logger.info(f"✓ 使用评分排名顺序分析 {len(ranked_papers)} 篇文献")

            # 限制数量
            if max_papers:
                ranked_papers = ranked_papers[:max_papers]

            # 创建论文ID到Paper对象的映射
            all_papers_dict = {p.folder_name: p for p in db.get_all_papers()}

            # 按排名顺序构建论文列表
            papers = []
            for item in ranked_papers:
                paper_id = item.get("paper_id", "")
                if paper_id in all_papers_dict:
                    papers.append(all_papers_dict[paper_id])
                    # 添加排名和评分信息到Paper对象
                    papers[-1].metadata.rank = item.get("rank", 0)
                    papers[-1].metadata.score = item.get("score", 0.0)

            with LOG_LOCK:
                logger.info(f"✓ 按排名加载了 {len(papers)} 篇文献")
                logger.info(f"  最高分: {ranked_papers[0].get('score', 0):.1f}分")
                logger.info(f"  最低分: {ranked_papers[-1].get('score', 0):.1f}分")
        else:
            # 原有逻辑：从数据库获取所有论文
            papers = db.get_all_papers()
            if max_papers:
                papers = papers[:max_papers]

        # 更新进度跟踪器
        self.tracker.progress_data["total_papers"] = len(papers)
        self.tracker._save_progress()

        with LOG_LOCK:
            logger.info(f"总共 {len(papers)} 篇论文待分析")

        # ⭐ NEW: 双层并发执行
        all_results = []
        start_time = time.time()

        # 用于跟踪进度
        completed_count = [0]  # 使用列表以便在闭包中修改
        failed_count = [0]

        def process_paper(paper, index):
            """处理单篇论文（用于线程池）"""
            try:
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

                # 分析论文（内层并发：5个分析器）
                results = self.analyze_single_paper(paper, skip_completed)

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
        with ThreadPoolExecutor(max_workers=self.max_concurrent_papers) as executor:
            # 提交所有任务
            future_to_paper = {}
            for i, paper in enumerate(papers):
                future = executor.submit(process_paper, paper, i)
                future_to_paper[future] = paper

            # 收集结果（按完成顺序）
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
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

        with LOG_LOCK:
            logger.info("=" * 80)
            logger.info("批量分析完成！")
            logger.info(f"总耗时: {elapsed_time:.2f} 秒")
            logger.info(f"成功: {completed_count[0]} 篇")
            logger.info(f"失败: {failed_count[0]} 篇")
            logger.info(f"平均每篇: {elapsed_time / len(papers):.2f} 秒")
            logger.info("=" * 80)

        return {
            "total": len(papers),
            "completed": completed_count[0],
            "failed": failed_count[0],
            "elapsed_time": elapsed_time,
            "avg_time_per_paper": elapsed_time / len(papers) if papers else 0,
            "results": all_results,
        }


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
