"""
Agent 分析协调器 V3 - 极简版本

完全重写，去掉所有复杂逻辑：
1. 不用线程池
2. 直接遍历论文
3. 简单的串行执行
4. 清晰的日志输出
"""

import sys
import io
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Windows UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("AgentAnalysisV3")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(handler)


class AgentAnalysisCoordinatorV3:
    """Agent 分析协调器 V3 - 极简版本"""

    def __init__(
        self,
        markdown_root: Path,
        output_dir: str = "data/agent_results",
        output_subdir: str = "all",
        api_type: str = "glm",
    ):
        """初始化协调器"""
        self.markdown_root = Path(markdown_root)
        self.output_root = Path(output_dir)
        self.output_subdir = output_subdir
        self.output_dir = self.output_root / output_subdir
        self.api_type = api_type

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"协调器 V3 初始化完成:")
        logger.info(f"  - Markdown 目录: {self.markdown_root}")
        logger.info(f"  - 输出目录: {self.output_dir}")

    def _load_papers(self) -> List:
        """从 Markdown 目录加载论文列表"""
        papers = []

        if not self.markdown_root.exists():
            logger.error(f"Markdown 目录不存在: {self.markdown_root}")
            return []

        logger.info(f"从 Markdown 目录加载论文: {self.markdown_root}")

        # 扫描目录
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

                        # 提取标题
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

    def _check_all_results(self, paper_id: str) -> Dict:
        """检查 all/ 目录是否已有结果"""
        all_dir = self.output_root / "all" / paper_id

        if not all_dir.exists():
            return {"exists": False}

        result = {"exists": True}
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            json_file = all_dir / f"{analyzer}.json"
            if json_file.exists():
                result[analyzer] = {"exists": True}
            else:
                result[analyzer] = {"exists": False}

        return result

    def _copy_from_all(self, paper_id: str):
        """从 all/ 复制结果"""
        all_dir = self.output_root / "all" / paper_id
        target_dir = self.output_dir / paper_id

        if not all_dir.exists():
            raise FileNotFoundError(f"all/ 目录不存在: {all_dir}")

        # 复制
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(all_dir, target_dir)

        logger.info(f"  [复制] 从 all/ 复制: {paper_id}")

    def _call_mock_api(self, paper_id: str) -> Dict:
        """调用 Mock API（用于测试）"""
        logger.info(f"  [API] 调用 API 分析: {paper_id}")

        # 模拟 API 调用耗时
        time.sleep(0.5)

        # 返回 mock 结果
        results = {}
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            results[analyzer] = {
                "success": True,
                "result": f"Mock result for {analyzer}",
                "analyzed_at": datetime.now().isoformat()
            }

        logger.info(f"  [API] API 返回: {len(results)} 个分析器结果")

        return results

    def _save_results(self, paper_id: str, results: Dict):
        """保存分析结果"""
        paper_dir = self.output_dir / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)

        for analyzer, result in results.items():
            result_file = paper_dir / f"{analyzer}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"  [保存] 保存结果: {paper_id}")

    def analyze_single_paper(self, paper, skip_completed: bool = True) -> Dict:
        """分析单篇论文"""
        paper_id = paper.folder_name
        logger.info(f"\n[论文] {paper_id}: {paper.title[:50]}...")

        # 如果是分类目录，检查 all/ 是否有结果
        if self.output_subdir != "all" and skip_completed:
            all_results = self._check_all_results(paper_id)

            if all_results.get("exists") and all_results.get("innovation", {}).get("exists"):
                # all/ 有完整结果，复制
                logger.info(f"  [跳过] all/ 有完整结果，直接复制")
                self._copy_from_all(paper_id)
                return {"status": "copied_from_all"}
            elif all_results.get("exists"):
                # all/ 有部分结果
                logger.info(f"  [部分] all/ 有部分结果")
                # TODO: 复制已有的，分析缺失的
                # 这里简化处理，直接调用 API
                pass

        # 调用 API 分析
        logger.info(f"  [分析] 开始分析...")
        results = self._call_mock_api(paper_id)

        # 保存结果
        self._save_results(paper_id, results)

        return {"status": "analyzed", "results": results}

    def batch_analyze(
        self,
        max_papers: Optional[int] = None,
        skip_completed: bool = True,
    ) -> Dict[str, Any]:
        """批量分析 - 极简版本，不用线程池"""

        logger.info("=" * 70)
        logger.info("开始批量分析（V3 极简版本）")
        logger.info("=" * 70)

        start_time = time.time()

        # 加载论文
        papers = self._load_papers()

        if not papers:
            logger.error("没有找到论文")
            return {"total": 0, "completed": 0, "failed": 0}

        # 限制数量
        if max_papers:
            papers = papers[:max_papers]

        logger.info(f"总共 {len(papers)} 篇论文待分析")

        # ⭐ 逐个处理（不用线程池）
        completed = 0
        failed = 0
        copied_from_all = 0

        for i, paper in enumerate(papers, 1):
            logger.info(f"\n进度: [{i}/{len(papers)}]")

            try:
                result = self.analyze_single_paper(paper, skip_completed)

                if result.get("status") == "copied_from_all":
                    copied_from_all += 1
                    completed += 1
                elif result.get("status") == "analyzed":
                    completed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"分析失败: {e}")
                failed += 1

        # 统计
        elapsed_time = time.time() - start_time

        logger.info("\n" + "=" * 70)
        logger.info("批量分析完成！")
        logger.info(f"总论文数: {len(papers)}")
        logger.info(f"从 all/ 复制: {copied_from_all}")
        logger.info(f"API 分析: {completed - copied_from_all}")
        logger.info(f"失败: {failed}")
        logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        logger.info("=" * 70)

        return {
            "total": len(papers),
            "completed": completed,
            "copied_from_all": copied_from_all,
            "analyzed_with_api": completed - copied_from_all,
            "failed": failed,
            "elapsed_time": elapsed_time,
        }


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数 - 测试 V3 极简版本"""
    import argparse

    parser = argparse.ArgumentParser(description="Agent 分析协调器 V3 - 极简版本")
    parser.add_argument("--max-papers", type=int, default=2, help="最大分析数量")
    parser.add_argument("--skip-completed", action="store_true", help="跳过已完成")

    args = parser.parse_args()

    # 创建协调器
    coordinator = AgentAnalysisCoordinatorV3(
        markdown_root=Path("data/projects/wind_aero/markdown/all"),
        output_subdir="categories/test_v3",
        api_type="glm",
    )

    # 执行分析
    stats = coordinator.batch_analyze(
        max_papers=args.max_papers,
        skip_completed=args.skip_completed,
    )

    # 输出统计
    print("\n" + "=" * 70)
    print("分析完成统计:")
    print(f"  总数: {stats['total']} 篇")
    print(f"  成功: {stats['completed']} 篇")
    print(f"  从 all/ 复制: {stats['copied_from_all']} 篇")
    print(f"  API 分析: {stats['analyzed_with_api']} 篇")
    print(f"  失败: {stats['failed']} 篇")
    print(f"  总耗时: {stats['elapsed_time']:.2f} 秒")
    print("=" * 70)


if __name__ == "__main__":
    main()
