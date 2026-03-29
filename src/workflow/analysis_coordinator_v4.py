"""
Agent 分析协调器 V4 - 完全照抄 Wind-Aero 版本

简化原则：
1. 去掉复杂的预检查逻辑
2. 去掉批量复制逻辑
3. 直接照抄 Wind-Aero 的 batch_analyze 结构
4. 保持 analyze_single_paper 简单明了
"""

import sys
import io
import json
import time
import shutil
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

import logging
logger = logging.getLogger("AgentAnalysisV4")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(handler)

# 全局锁
WRITE_LOCK = threading.Lock()
PROGRESS_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()


class AgentAnalysisCoordinatorV4:
    """Agent 分析协调器 V4 - 照抄 Wind-Aero 版本"""

    def __init__(
        self,
        markdown_root: Path,
        output_dir: str = "data/agent_results",
        output_subdir: str = "all",
        max_concurrent_papers: int = 10,
        max_concurrent_analyzers: int = 5,
        api_type: str = "glm",
    ):
        """初始化协调器"""
        self.markdown_root = Path(markdown_root)
        self.output_root = Path(output_dir)
        self.output_subdir = output_subdir
        self.output_dir = self.output_root / output_subdir
        self.max_concurrent_papers = max_concurrent_papers
        self.max_concurrent_analyzers = max_concurrent_analyzers
        self.api_type = api_type

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 API 客户端
        self._init_api_client()

        logger.info(f"协调器 V4 初始化完成:")
        logger.info(f"  - Markdown 目录: {self.markdown_root}")
        logger.info(f"  - 输出目录: {self.output_dir}")
        logger.info(f"  - 外层并发: {max_concurrent_papers}")
        logger.info(f"  - 内层并发: {max_concurrent_analyzers}")

    def _init_api_client(self):
        """初始化 API 客户端"""
        try:
            if self.api_type == "glm":
                # ⭐ 修复导入路径
                from src.api.glm_client import GLMParallelAnalyzer

                # 检查 API 密钥文件
                api_keys_file = Path("D:/xfs/phd/github项目/.私人信息/glm_api_keys_all.txt")
                if not api_keys_file.exists():
                    # 尝试其他可能的路径
                    possible_paths = [
                        "D:/xfs/phd/.私人信息/glm_api_keys.txt",
                        "../config/api_keys.yaml",
                    ]
                    for path in possible_paths:
                        if Path(path).exists():
                            api_keys_file = Path(path)
                            break

                if not api_keys_file.exists():
                    raise FileNotFoundError(f"找不到 GLM API 密钥文件")

                # 使用 GLM 的 analyze_paper 方法（内部已实现并发）
                self.api_client = GLMParallelAnalyzer(
                    api_keys_file=str(api_keys_file),
                    model="glm-4.7",
                    base_url="https://open.bigmodel.cn/api/coding/paas/v4",
                    max_workers=self.max_concurrent_analyzers,
                )
                logger.info("GLM API 客户端初始化成功")
            else:
                raise ValueError(f"不支持的 API 类型: {self.api_type}")
        except Exception as e:
            logger.error(f"API 客户端初始化失败: {e}")
            self.api_client = None

    def _load_papers_from_markdown(self) -> List:
        """从 Markdown 目录加载论文"""
        papers = []

        if not self.markdown_root.exists():
            logger.error(f"Markdown 目录不存在: {self.markdown_root}")
            return []

        logger.info(f"从 Markdown 目录加载论文: {self.markdown_root}")

        paper_dirs = [d for d in sorted(self.markdown_root.iterdir()) if d.is_dir()]

        for paper_dir in paper_dirs:
            md_file = paper_dir / "full.md"
            if not md_file.exists():
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                class SimplePaper:
                    def __init__(self, folder_name, content):
                        self.folder_name = folder_name
                        self.title = "Unknown"
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip().startswith('#'):
                                self.title = line.lstrip('#').strip()
                                break

                papers.append(SimplePaper(paper_dir.name, content))

            except Exception as e:
                logger.warning(f"加载论文 {paper_dir.name} 失败: {e}")

        logger.info(f"加载了 {len(papers)} 篇论文")
        return papers

    def analyze_single_paper(self, paper, skip_completed: bool = True) -> Dict[str, Any]:
        """
        分析单篇论文

        ⭐ 照抄 Wind-Aero 的简洁逻辑：
        1. 检查哪些分析器需要运行
        2. 调用 api_client.analyze_paper（内部会并发）
        3. 保存结果
        """
        paper_id = paper.folder_name

        with LOG_LOCK:
            logger.info(f"开始分析论文: {paper.title[:50]}...")

        results = {}

        # 确定需要运行的分析器
        analyzers_to_run = []
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            # ⭐ 简化：不检查 skip_completed，直接运行
            analyzers_to_run.append(analyzer)

        if not analyzers_to_run:
            with LOG_LOCK:
                logger.info(f"所有分析器都已完成")
            return results

        # 准备 Prompts
        analyzer_prompts = {}
        for analyzer in analyzers_to_run:
            # ⭐ 使用简单的 Prompt
            analyzer_prompts[analyzer] = f"请分析这篇论文的{analyzer}：\n\n论文标题：{paper.title}\n\n论文ID：{paper_id}"

        # ⭐ 关键：调用 api_client.analyze_paper（内部会并发执行）
        if self.api_client:
            with LOG_LOCK:
                logger.info(f"调用 API 分析: {len(analyzers_to_run)} 个分析器")

            api_results = self.api_client.analyze_paper(
                analyzer_prompts=analyzer_prompts,
                paper_id=paper_id,
                progress_callback=None,
            )

            # 处理结果
            for analyzer, api_result in api_results.items():
                if api_result.get("success"):
                    results[analyzer] = api_result
                    # 保存结果
                    self._save_result(paper_id, analyzer, api_result)
                else:
                    results[analyzer] = {"success": False, "error": api_result.get("error")}

        return results

    def _save_result(self, paper_id: str, analyzer: str, result: Dict):
        """保存分析结果"""
        with WRITE_LOCK:
            paper_dir = self.output_dir / paper_id
            paper_dir.mkdir(parents=True, exist_ok=True)

            result_file = paper_dir / f"{analyzer}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

    def batch_analyze(
        self,
        max_papers: Optional[int] = None,
        skip_completed: bool = True,
    ) -> Dict[str, Any]:
        """
        批量分析 - 照抄 Wind-Areo 结构

        外层：并发处理 N 篇论文
        内层：每篇论文的 5 个分析器并发（在 api_client 内部）
        """
        with LOG_LOCK:
            logger.info("=" * 70)
            logger.info("开始批量 Agent 分析（V4 照抄 Wind-Areo 版本）")
            logger.info("=" * 70)

        start_time = time.time()

        # 加载论文
        papers = self._load_papers_from_markdown()

        if not papers:
            logger.error("没有找到论文")
            return {"total": 0, "completed": 0, "failed": 0}

        if max_papers:
            papers = papers[:max_papers]

        logger.info(f"总共 {len(papers)} 篇论文待分析")

        # 用于跟踪进度
        completed_count = [0]
        failed_count = [0]

        def process_paper(paper, index):
            """处理单篇论文"""
            try:
                with LOG_LOCK:
                    logger.info(f"[{index+1}/{len(papers)}] 处理论文: {paper.folder_name[:40]}...")

                # 分析论文（内层并发在 api_client.analyze_paper 内部）
                results = self.analyze_single_paper(paper, skip_completed)

                completed_count[0] += 1

                return {
                    "paper_id": paper.folder_name,
                    "success": True,
                }

            except Exception as e:
                with LOG_LOCK:
                    logger.error(f"分析论文 {paper.folder_name} 失败: {e}")

                failed_count[0] += 1

                return {
                    "paper_id": paper.folder_name,
                    "success": False,
                }

        # ⭐ 照抄 Wind-Areo：使用线程池外层并发
        with ThreadPoolExecutor(max_workers=self.max_concurrent_papers) as executor:
            # 提交所有任务
            future_to_paper = {}
            for i, paper in enumerate(papers):
                future = executor.submit(process_paper, paper, i)
                future_to_paper[future] = paper

            # 收集结果
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        with LOG_LOCK:
                            logger.info(f"✓ 论文分析完成: {paper.folder_name[:40]}...")
                except Exception as e:
                    with LOG_LOCK:
                        logger.error(f"处理论文 {paper.folder_name} 时发生异常: {e}")

        # 统计
        elapsed_time = time.time() - start_time

        with LOG_LOCK:
            logger.info("=" * 70)
            logger.info("批量分析完成！")
            logger.info(f"总论文数: {len(papers)}")
            logger.info(f"成功: {completed_count[0]} 篇")
            logger.info(f"失败: {failed_count[0]} 篇")
            logger.info(f"总耗时: {elapsed_time:.2f} 秒")
            logger.info("=" * 70)

        return {
            "total": len(papers),
            "completed": completed_count[0],
            "failed": failed_count[0],
            "elapsed_time": elapsed_time,
        }


def main():
    """主函数"""
    coordinator = AgentAnalysisCoordinatorV4(
        markdown_root=Path("data/projects/wind_aero/markdown/all"),
        output_subdir="categories/test_v4",
        max_concurrent_papers=2,
        api_type="glm",
    )

    stats = coordinator.batch_analyze(max_papers=2)

    print("\n" + "=" * 70)
    print("分析完成统计:")
    print(f"  总数: {stats['total']} 篇")
    print(f"  成功: {stats['completed']} 篇")
    print(f"  失败: {stats['failed']} 篇")
    print(f"  总耗时: {stats['elapsed_time']:.2f} 秒")
    print("=" * 70)


if __name__ == "__main__":
    main()
