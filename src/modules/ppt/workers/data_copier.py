"""
数据复制器

职责：将 agent_results 从原项目复制到新项目
设计原则：只做文件复制，不做任何修改
"""

import shutil
from pathlib import Path
from typing import List, Optional
import sys
import io


class DataCopier:
    """数据复制器"""

    def __init__(self, source_path: str, target_path: str):
        """
        初始化复制器

        Args:
            source_path: 源 agent_results 目录
            target_path: 目标 data/raw/agent_results 目录
        """
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)

    def copy_all(self, overwrite: bool = False) -> dict:
        """
        复制所有 agent_results

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            复制统计信息
        """
        if not self.source_path.exists():
            raise FileNotFoundError(f"源路径不存在: {self.source_path}")

        # 创建目标目录
        self.target_path.mkdir(parents=True, exist_ok=True)

        stats = {"total": 0, "copied": 0, "skipped": 0, "failed": 0, "errors": []}

        # 遍历源目录
        for paper_dir in self.source_path.iterdir():
            if not paper_dir.is_dir():
                continue

            stats["total"] += 1
            paper_id = paper_dir.name
            target_dir = self.target_path / paper_id

            # 跳过已存在的目录
            if target_dir.exists() and not overwrite:
                stats["skipped"] += 1
                continue

            try:
                # 复制整个目录
                if target_dir.exists():
                    shutil.rmtree(target_dir)

                shutil.copytree(paper_dir, target_dir)
                stats["copied"] += 1

                print(f"✅ 已复制: {paper_id}")

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"{paper_id}: {str(e)}")
                print(f"❌ 复制失败: {paper_id} - {e}")

        return stats

    def copy_single(self, paper_id: str, overwrite: bool = False) -> bool:
        """
        复制单篇文献的 agent_results

        Args:
            paper_id: 论文 ID
            overwrite: 是否覆盖已存在的文件

        Returns:
            True 如果成功，False 否则
        """
        source_dir = self.source_path / paper_id
        target_dir = self.target_path / paper_id

        if not source_dir.exists():
            print(f"❌ 源目录不存在: {source_dir}")
            return False

        # 跳过已存在的目录
        if target_dir.exists() and not overwrite:
            print(f"⏭️  已存在，跳过: {paper_id}")
            return True

        try:
            # 复制目录
            if target_dir.exists():
                shutil.rmtree(target_dir)

            shutil.copytree(source_dir, target_dir)
            print(f"✅ 已复制: {paper_id}")
            return True

        except Exception as e:
            print(f"❌ 复制失败: {paper_id} - {e}")
            return False

    def verify_copy(self, paper_ids: Optional[List[str]] = None) -> dict:
        """
        验证复制结果

        Args:
            paper_ids: 要验证的论文 ID 列表，如果为 None 则验证所有

        Returns:
            验证结果统计
        """
        if paper_ids is None:
            paper_ids = [d.name for d in self.source_path.iterdir() if d.is_dir()]

        stats = {
            "total": len(paper_ids),
            "exists": 0,
            "missing": 0,
            "incomplete": 0,
            "details": [],
        }

        for paper_id in paper_ids:
            source_dir = self.source_path / paper_id
            target_dir = self.target_path / paper_id

            # 统计源目录中的 JSON 文件
            source_files = set([f.name for f in source_dir.glob("*.json")])

            if not target_dir.exists():
                stats["missing"] += 1
                stats["details"].append(
                    {
                        "paper_id": paper_id,
                        "status": "missing",
                        "message": "目标目录不存在",
                    }
                )
                continue

            # 统计目标目录中的 JSON 文件
            target_files = set([f.name for f in target_dir.glob("*.json")])

            if source_files == target_files:
                stats["exists"] += 1
                stats["details"].append(
                    {
                        "paper_id": paper_id,
                        "status": "complete",
                        "message": f"{len(source_files)} 个文件",
                    }
                )
            else:
                stats["incomplete"] += 1
                missing_files = source_files - target_files
                stats["details"].append(
                    {
                        "paper_id": paper_id,
                        "status": "incomplete",
                        "message": f"缺少 {len(missing_files)} 个文件: {missing_files}",
                    }
                )

        return stats

    def get_size_info(self) -> dict:
        """
        获取目录大小信息

        Returns:
            大小信息字典
        """

        def get_dir_size(path):
            total = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total

        source_size = get_dir_size(self.source_path) if self.source_path.exists() else 0
        target_size = get_dir_size(self.target_path) if self.target_path.exists() else 0

        return {
            "source_size_mb": source_size / (1024 * 1024),
            "target_size_mb": target_size / (1024 * 1024),
            "source_papers": (
                len([d for d in self.source_path.iterdir() if d.is_dir()])
                if self.source_path.exists()
                else 0
            ),
            "target_papers": (
                len([d for d in self.target_path.iterdir() if d.is_dir()])
                if self.target_path.exists()
                else 0
            ),
        }


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # Windows UTF-8 支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    # 初始化复制器
    copier = DataCopier(
        source_path="D:/xfs/phd/github项目/Wind-Aero-Literature-Analysis-System/data/agent_results",
        target_path="data/raw/agent_results",
    )

    # 查看大小信息
    print("📊 数据大小信息:")
    size_info = copier.get_size_info()
    print(
        f"  源目录: {size_info['source_size_mb']:.2f} MB, {size_info['source_papers']} 篇文献"
    )
    print(
        f"  目标目录: {size_info['target_size_mb']:.2f} MB, {size_info['target_papers']} 篇文献"
    )

    # 复制所有数据
    print("\n🚀 开始复制...")
    stats = copier.copy_all(overwrite=False)

    print("\n📈 复制统计:")
    print(f"  总计: {stats['total']} 篇")
    print(f"  ✅ 已复制: {stats['copied']} 篇")
    print(f"  ⏭️  已跳过: {stats['skipped']} 篇")
    print(f"  ❌ 失败: {stats['failed']} 篇")

    if stats["errors"]:
        print("\n❌ 错误详情:")
        for error in stats["errors"]:
            print(f"  - {error}")

    # 验证复制结果
    print("\n🔍 验证复制结果...")
    verify_stats = copier.verify_copy()
    print(f"  完整: {verify_stats['exists']} 篇")
    print(f"  缺失: {verify_stats['missing']} 篇")
    print(f"  不完整: {verify_stats['incomplete']} 篇")

    if verify_stats["incomplete"] > 0:
        print("\n⚠️ 不完整的文献:")
        for detail in verify_stats["details"]:
            if detail["status"] == "incomplete":
                print(f"  - {detail['paper_id']}: {detail['message']}")
