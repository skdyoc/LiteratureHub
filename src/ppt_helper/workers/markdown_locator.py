"""
Markdown 文献定位器（LiteratureHub 集成版）

职责：根据论文 ID 定位原始 full.md 文件的完整路径
设计原则：只做路径查找，不做文本读取或理解

支持两种模式（与 GUI1/GUI2 MinerU 处理逻辑一致）：
- all 模式：处理 data/projects/wind_aero/markdown/all 下的所有文献
- categories 模式：处理 data/projects/wind_aero/markdown/categories/{category} 下的分类文献
"""

from pathlib import Path
from typing import Optional, Dict, List


class MarkdownLocator:
    """Markdown 文献定位器（LiteratureHub 集成版）"""

    def __init__(self, base_dir: str, mode: str = "all", category: Optional[str] = None):
        """
        初始化定位器

        Args:
            base_dir: LiteratureHub 基础目录（例如：D:/xfs/phd/github项目/LiteratureHub）
            mode: 工作模式，"all" 或 "categories"
            category: 分类名称（仅在 categories 模式下使用）
        """
        self.base_dir = Path(base_dir)
        self.mode = mode
        self.category = category

        # 根据模式构建 markdown 路径
        if mode == "categories" and category:
            self.source_path = self.base_dir / "data" / "projects" / "wind_aero" / "markdown" / "categories" / category
        else:
            self.source_path = self.base_dir / "data" / "projects" / "wind_aero" / "markdown" / "all"

    def locate_full_md(self, paper_id: str) -> Optional[Path]:
        """
        定位指定论文的 full.md 文件

        Args:
            paper_id: 论文 ID，例如 "2018_3D_numerical_simulation..."

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

    def batch_locate(self, paper_ids: List[str]) -> Dict[str, Optional[Path]]:
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

    def get_all_paper_ids(self) -> List[str]:
        """
        获取所有论文 ID 列表

        通过扫描源目录，找到所有包含 full.md 的子目录

        Returns:
            论文 ID 列表
        """
        paper_ids = []

        if not self.source_path.exists():
            return paper_ids

        for subdir in self.source_path.iterdir():
            if subdir.is_dir():
                # 检查是否包含 full.md
                full_md_path = subdir / "full.md"
                if full_md_path.exists():
                    paper_ids.append(subdir.name)

        return sorted(paper_ids)

    def get_all_categories(self) -> List[str]:
        """
        获取所有可用的分类

        Returns:
            分类列表
        """
        categories_dir = self.base_dir / "data" / "projects" / "wind_aero" / "markdown" / "categories"

        if not categories_dir.exists():
            return []

        categories = []
        for item in categories_dir.iterdir():
            if item.is_dir():
                categories.append(item.name)

        return sorted(categories)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import sys
    import io

    # Windows UTF-8 支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    base_dir = "D:/xfs/phd/github项目/LiteratureHub"

    # All 模式
    print("=" * 60)
    print("All 模式测试")
    print("=" * 60)

    locator_all = MarkdownLocator(base_dir=base_dir, mode="all")

    paper_ids_all = locator_all.get_all_paper_ids()
    print(f"✅ 找到 {len(paper_ids_all)} 篇文献（all 模式）")

    if paper_ids_all:
        paper_id = paper_ids_all[0]
        path = locator_all.locate_full_md(paper_id)

        if path:
            print(f"✅ 找到: {path.name}")
        else:
            print(f"❌ 未找到: {paper_id}")

    # Categories 模式
    print("\n" + "=" * 60)
    print("Categories 模式测试")
    print("=" * 60)

    # 获取所有分类
    locator_test = MarkdownLocator(base_dir=base_dir, mode="categories")
    categories = locator_test.get_all_categories()
    print(f"✅ 找到 {len(categories)} 个分类")

    for cat in categories:
        locator_cat = MarkdownLocator(base_dir=base_dir, mode="categories", category=cat)
        paper_ids_cat = locator_cat.get_all_paper_ids()
        print(f"  - {cat}: {len(paper_ids_cat)} 篇文献")
