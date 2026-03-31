"""
文献元数据提取器（LiteratureHub 集成版）

职责：从 LiteratureHub 的 agent_results JSON 文件中提取元数据
设计原则：只提取结构化数据，不做文本理解或分析

支持两种模式（与 GUI1/GUI2 MinerU 处理逻辑一致）：
- all 模式：处理 data/agent_results/all 下的所有文献
- categories 模式：处理 data/agent_results/categories/{category} 下的分类文献
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass


@dataclass
class PaperMetadata:
    """文献元数据"""

    paper_id: str
    title: str
    authors: list[str]
    year: int
    journal: str
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    impact_factor: Optional[float] = None
    score: Optional[float] = None  # 综合评分


class ContentExtractor:
    """文献内容提取器（LiteratureHub 集成版）"""

    def __init__(self, base_dir: str, mode: str = "all", category: Optional[str] = None):
        """
        初始化提取器

        Args:
            base_dir: LiteratureHub 基础目录（例如：D:/xfs/phd/github项目/LiteratureHub）
            mode: 工作模式，"all" 或 "categories"
            category: 分类名称（仅在 categories 模式下使用）
        """
        self.base_dir = Path(base_dir)
        self.mode = mode
        self.category = category

        # 根据模式构建 agent_results 路径
        if mode == "categories" and category:
            self.results_path = self.base_dir / "data" / "agent_results" / "categories" / category
        else:
            self.results_path = self.base_dir / "data" / "agent_results" / "all"

        # ⭐ 加载元数据索引（从 pdfs/all/metadata.json）
        self.metadata_index = self._load_metadata_index()

    def _load_metadata_index(self) -> Dict[str, Dict[str, Any]]:
        """
        加载元数据索引（从 metadata.json）

        Returns:
            字典 {paper_id: metadata_dict}
        """
        metadata_file = self.base_dir / "data" / "projects" / "wind_aero" / "pdfs" / "all" / "metadata.json"

        if not metadata_file.exists():
            return {}

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)

            # 构建 paper_id -> metadata 的映射
            # paper_id 是 pdf_filename 去掉 .pdf 后缀
            index = {}
            for item in metadata_list:
                pdf_filename = item.get("pdf_filename", "")
                if pdf_filename:
                    # 去掉 .pdf 后缀得到 paper_id
                    paper_id = pdf_filename.replace(".pdf", "")
                    index[paper_id] = item

            return index
        except Exception as e:
            print(f"⚠️ 加载元数据索引失败: {e}")
            return {}

    def extract_metadata(self, paper_id: str) -> Optional[PaperMetadata]:
        """
        从元数据索引中提取单篇文献的元数据

        Args:
            paper_id: 论文 ID

        Returns:
            PaperMetadata 对象，如果提取失败返回 None
        """
        # ⭐ 优先从元数据索引中查找
        if paper_id in self.metadata_index:
            meta = self.metadata_index[paper_id]
            return PaperMetadata(
                paper_id=paper_id,
                title=self._safe_str(meta.get("title", "")),
                authors=self._safe_list(meta.get("authors", [])),
                year=int(meta.get("year", 0) or 0),
                journal=self._safe_str(meta.get("journal", "")),
                volume=meta.get("volume"),
                issue=meta.get("issue"),
                pages=meta.get("pages"),
                doi=meta.get("doi"),
                impact_factor=meta.get("impact_factor"),
                score=meta.get("relevance_score"),  # 使用 relevance_score 作为初始评分
            )

        # 降级方案：尝试从 agent_results 中提取（旧逻辑）
        paper_dir = self.results_path / paper_id
        if not paper_dir.exists():
            return None

        # 尝试从不同的 JSON 文件中提取元数据
        json_files = [
            "motivation.json",
            "innovation.json",
            "roadmap.json",
            "mechanism.json",
            "impact.json"
        ]

        metadata_json = None
        for json_name in json_files:
            json_file = paper_dir / json_name
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # 检查数据结构
                    if isinstance(data, dict):
                        # 如果有 paper_info 字段
                        if "paper_info" in data:
                            metadata_json = data["paper_info"]
                            break
                        # 如果有 metadata 字段
                        elif "metadata" in data:
                            metadata_json = data["metadata"]
                            break
                        # 如果有 result 字段，尝试从中提取
                        elif "result" in data:
                            result = data["result"]
                            if isinstance(result, dict):
                                if "paper_info" in result:
                                    metadata_json = result["paper_info"]
                                    break
                                elif "metadata" in result:
                                    metadata_json = result["metadata"]
                                    break
                                # 直接从 result 中提取
                                elif "title" in result and "authors" in result:
                                    metadata_json = result
                                    break
                except Exception as e:
                    continue

        if not metadata_json:
            return None

        # 提取元数据字段
        return PaperMetadata(
            paper_id=paper_id,
            title=self._safe_str(metadata_json.get("title", "")),
            authors=self._safe_list(metadata_json.get("authors", [])),
            year=int(metadata_json.get("year", 0) or 0),
            journal=self._safe_str(metadata_json.get("journal", "")),
            volume=metadata_json.get("volume"),
            issue=metadata_json.get("issue"),
            pages=metadata_json.get("pages"),
            doi=metadata_json.get("doi"),
            impact_factor=metadata_json.get("impact_factor"),
            score=metadata_json.get("score"),
        )

    def extract_all_agent_results(self, paper_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        提取所有论文的完整 agent_results（5 个 JSON 文件）

        Args:
            paper_ids: 论文 ID 列表

        Returns:
            字典 {paper_id: {json_name: full_content}}
        """
        all_results = {}

        # 5 个 JSON 文件名
        json_files = [
            "motivation.json",
            "innovation.json",
            "mechanism.json",
            "impact.json",
            "roadmap.json"
        ]

        for paper_id in paper_ids:
            paper_dir = self.results_path / paper_id

            if not paper_dir.exists():
                continue

            paper_results = {}

            # 读取所有 5 个 JSON
            for json_name in json_files:
                json_file = paper_dir / json_name

                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # 提取 result 字段（如果存在）
                        if isinstance(data, dict) and "result" in data:
                            result_data = data["result"]
                            # 如果 result 是字符串（JSON 格式），需要解析
                            if isinstance(result_data, str):
                                try:
                                    result_data = json.loads(result_data)
                                except:
                                    result_data = {}
                            paper_results[json_name.replace(".json", "")] = result_data
                        else:
                            paper_results[json_name.replace(".json", "")] = data

                    except Exception as e:
                        continue

            if paper_results:
                all_results[paper_id] = paper_results

        return all_results

    def get_available_paper_ids(self) -> List[str]:
        """
        获取所有可用的论文 ID

        Returns:
            论文 ID 列表
        """
        paper_ids = []

        if not self.results_path.exists():
            return paper_ids

        for subdir in self.results_path.iterdir():
            if subdir.is_dir():
                # 检查是否包含至少一个 JSON 文件
                json_files = list(subdir.glob("*.json"))
                if json_files:
                    paper_ids.append(subdir.name)

        return sorted(paper_ids)

    def get_all_categories(self) -> List[str]:
        """
        获取所有可用的分类

        Returns:
            分类列表
        """
        categories_dir = self.base_dir / "data" / "agent_results" / "categories"

        if not categories_dir.exists():
            return []

        categories = []
        for item in categories_dir.iterdir():
            if item.is_dir():
                categories.append(item.name)

        return sorted(categories)

    def _safe_str(self, s: Any) -> str:
        """安全转换为字符串"""
        if s is None:
            return ""
        if isinstance(s, str):
            return s
        if isinstance(s, list):
            return ", ".join(str(item) for item in s)
        return str(s)

    def _safe_list(self, lst: Any) -> list[str]:
        """安全转换为字符串列表"""
        if lst is None:
            return []
        if isinstance(lst, list):
            return [str(item) for item in lst]
        if isinstance(lst, str):
            return [lst]
        return [str(lst)]


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

    extractor_all = ContentExtractor(base_dir=base_dir, mode="all")

    paper_ids_all = extractor_all.get_available_paper_ids()
    print(f"✅ 找到 {len(paper_ids_all)} 篇文献（all 模式）")

    if paper_ids_all:
        paper_id = paper_ids_all[0]
        metadata = extractor_all.extract_metadata(paper_id)

        if metadata:
            print(f"\n📄 文献信息:")
            print(f"  Paper ID: {metadata.paper_id}")
            print(f"  标题: {metadata.title[:80]}...")
            print(f"  年份: {metadata.year}")
            print(f"  评分: {metadata.score}")

    # Categories 模式
    print("\n" + "=" * 60)
    print("Categories 模式测试")
    print("=" * 60)

    # 获取所有分类
    extractor_test = ContentExtractor(base_dir=base_dir, mode="categories")
    categories = extractor_test.get_all_categories()
    print(f"✅ 找到 {len(categories)} 个分类")

    for cat in categories:
        extractor_cat = ContentExtractor(base_dir=base_dir, mode="categories", category=cat)
        paper_ids_cat = extractor_cat.get_available_paper_ids()
        print(f"  - {cat}: {len(paper_ids_cat)} 篇文献")
