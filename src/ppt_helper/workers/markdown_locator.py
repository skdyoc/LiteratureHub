"""
Markdown 文献定位器

职责：根据论文 ID 定位原始 full.md 文件的完整路径
设计原则：只做路径查找，不做文本读取或理解
"""

from pathlib import Path
from typing import Optional, Dict
import json


class MarkdownLocator:
    """Markdown 文献定位器"""

    def __init__(self, source_markdown_path: str):
        """
        初始化定位器

        Args:
            source_markdown_path: 原始 Markdown 文献根目录
                                例如：D:/xfs/phd/参考文献/气动/markdown
        """
        self.source_path = Path(source_markdown_path)

    def locate_full_md(self, paper_id: str) -> Optional[Path]:
        """
        定位指定论文的 full.md 文件

        Args:
            paper_id: 论文 ID，例如 "2026_Author_Title_Keywords"

        Returns:
            full.md 文件的完整路径，如果不存在返回 None
        """
        # 构建可能的路径
        possible_paths = [
            self.source_path / paper_id / "full.md",
            self.source_path / paper_id / "paper.md",
            self.source_path / paper_id / "main.md",
        ]

        # 尝试找到存在的文件
        for path in possible_paths:
            if path.exists():
                return path

        return None

    def batch_locate(self, paper_ids: list[str]) -> Dict[str, Optional[Path]]:
        """
        批量定位 full.md 文件

        Args:
            paper_ids: 论文 ID 列表

        Returns:
            字典 {paper_id: path}，不存在的文件对应 None
        """
        result = {}
        for paper_id in paper_ids:
            result[paper_id] = self.locate_full_md(paper_id)
        return result

    def validate_exists(self, paper_id: str) -> bool:
        """
        验证 full.md 是否存在

        Args:
            paper_id: 论文 ID

        Returns:
            True 如果存在，False 否则
        """
        path = self.locate_full_md(paper_id)
        return path is not None and path.exists()

    def get_all_paper_ids(self) -> list[str]:
        """
        获取所有论文 ID 列表

        通过扫描源目录，找到所有包含 full.md 的子目录

        Returns:
            论文 ID 列表
        """
        paper_ids = []

        for subdir in self.source_path.iterdir():
            if subdir.is_dir():
                # 检查是否包含 full.md
                full_md_path = subdir / "full.md"
                if full_md_path.exists():
                    paper_ids.append(subdir.name)

        return sorted(paper_ids)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 初始化定位器
    locator = MarkdownLocator(source_markdown_path="D:/xfs/phd/参考文献/气动/markdown")

    # 定位单个文件
    paper_id = "2026_Author_Title_Keywords"
    path = locator.locate_full_md(paper_id)

    if path:
        print(f"✅ 找到: {path}")
    else:
        print(f"❌ 未找到: {paper_id}")

    # 批量定位
    paper_ids = ["2026_Paper_1", "2026_Paper_2", "2026_Paper_3"]
    paths = locator.batch_locate(paper_ids)

    for pid, path in paths.items():
        status = "✅" if path else "❌"
        print(f"{status} {pid}: {path}")

    # 获取所有论文 ID
    all_ids = locator.get_all_paper_ids()
    print(f"\n总共找到 {len(all_ids)} 篇文献")
