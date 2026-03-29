"""
文献元数据提取器

职责：从 agent_results JSON 文件中提取元数据（标题、作者、年份、期刊等）
设计原则：只提取结构化数据，不做文本理解或分析
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
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
    """文献内容提取器"""

    def __init__(self, agent_results_path: str, ranked_papers_path: Optional[str] = None):
        """
        初始化提取器

        Args:
            agent_results_path: agent_results 根目录
                               例如：data/raw/agent_results
            ranked_papers_path: ranked_papers.json 文件路径
                               例如：原系统/data/analysis_results/ranked_papers.json
                               如果不提供，将尝试从原系统默认路径加载
        """
        self.results_path = Path(agent_results_path)

        # 加载文献元数据映射
        self._metadata_map: Dict[str, Dict[str, Any]] = {}
        self._load_metadata_map(ranked_papers_path)

    def _load_metadata_map(self, ranked_papers_path: Optional[str] = None):
        """
        加载文献元数据映射表

        Args:
            ranked_papers_path: ranked_papers.json 文件路径
        """
        # 如果未提供路径，尝试从原系统默认路径加载
        if not ranked_papers_path:
            # 尝试常见路径
            possible_paths = [
                Path("../Wind-Aero-Literature-Analysis-System/data/analysis_results/ranked_papers.json"),
                Path("D:/xfs/phd/github项目/Wind-Aero-Literature-Analysis-System/data/analysis_results/ranked_papers.json"),
            ]

            ranked_papers_path = None
            for path in possible_paths:
                if path.exists():
                    ranked_papers_path = str(path)
                    break

        if not ranked_papers_path:
            print("⚠️  未找到 ranked_papers.json，元数据提取将失败")
            return

        try:
            with open(ranked_papers_path, "r", encoding="utf-8") as f:
                papers_list = json.load(f)

            # 构建 {paper_id: metadata} 映射
            for paper in papers_list:
                paper_id = paper.get("paper_id", "")
                if paper_id:
                    self._metadata_map[paper_id] = paper

            print(f"✅ 加载了 {len(self._metadata_map)} 篇文献的元数据映射")
        except Exception as e:
            print(f"⚠️ 加载 ranked_papers.json 失败: {e}")

    def extract_metadata(self, paper_id: str) -> Optional[PaperMetadata]:
        """
        提取单篇文献的元数据

        Args:
            paper_id: 论文 ID

        Returns:
            PaperMetadata 对象，如果提取失败返回 None
        """
        # 从元数据映射表中查找
        if paper_id in self._metadata_map:
            paper_info = self._metadata_map[paper_id]

            return PaperMetadata(
                paper_id=paper_id,
                title=paper_info.get("title", ""),
                authors=paper_info.get("authors", []),
                year=paper_info.get("year", 0),
                journal=paper_info.get("journal", ""),
                volume=paper_info.get("volume"),
                issue=paper_info.get("issue"),
                pages=paper_info.get("pages"),
                doi=paper_info.get("doi"),
                impact_factor=paper_info.get("impact_factor"),
                score=paper_info.get("score"),
            )

        # 如果映射表中没有，尝试旧的提取方式（向后兼容）
        paper_dir = self.results_path / paper_id

        # 尝试从不同的 JSON 文件中提取元数据
        # 优先级：innovation.json > motivation.json > roadmap.json
        json_files = [
            paper_dir / "innovation.json",
            paper_dir / "motivation.json",
            paper_dir / "roadmap.json",
        ]

        metadata_json = None
        for json_file in json_files:
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "paper_info" in data or "metadata" in data:
                            metadata_json = data
                            break
                except Exception as e:
                    print(f"⚠️ 读取 {json_file} 失败: {e}")
                    continue

        if not metadata_json:
            return None

        # 提取元数据字段
        paper_info = metadata_json.get("paper_info", metadata_json.get("metadata", {}))

        return PaperMetadata(
            paper_id=paper_id,
            title=paper_info.get("title", ""),
            authors=paper_info.get("authors", []),
            year=paper_info.get("year", 0),
            journal=paper_info.get("journal", ""),
            volume=paper_info.get("volume"),
            issue=paper_info.get("issue"),
            pages=paper_info.get("pages"),
            doi=paper_info.get("doi"),
            impact_factor=paper_info.get("impact_factor"),
            score=paper_info.get("score"),
        )

    def extract_innovation_summary(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        提取创新点摘要（结构化数据，不做理解）

        Args:
            paper_id: 论文 ID

        Returns:
            创新点摘要字典，如果提取失败返回 None
        """
        innovation_file = self.results_path / paper_id / "innovation.json"

        if not innovation_file.exists():
            return None

        try:
            with open(innovation_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # ⭐ 添加类型检查
            if not isinstance(data, dict):
                # 如果 data 不是字典，尝试解析
                if isinstance(data, str):
                    # 可能是 JSON 字符串，尝试再次解析
                    try:
                        data = json.loads(data)
                    except:
                        print(f"Warning: innovation.json 格式错误（内容是字符串）: {paper_id}")
                        return None
                else:
                    print(f"Warning: innovation.json 格式错误（类型: {type(data)}）: {paper_id}")
                    return None

            # 数据在 result 字段中
            result = data.get("result", {})
            if not isinstance(result, dict):
                result = {}

            # ⭐ 返回完整的结果，而不是只提取计数
            return result
        except Exception as e:
            print(f"Warning: Failed to extract innovation summary for {paper_id}: {e}")
            return None

    def extract_all_summaries(self, paper_ids: list[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量提取摘要信息

        Args:
            paper_ids: 论文 ID 列表

        Returns:
            字典 {paper_id: summary}
        """
        summaries = {}

        for paper_id in paper_ids:
            metadata = self.extract_metadata(paper_id)
            innovation = self.extract_innovation_summary(paper_id)

            if metadata:
                summaries[paper_id] = {
                    "metadata": metadata,
                    "innovation_summary": innovation,
                }

        return summaries

    def extract_all_agent_results(self, paper_ids: list[str]) -> Dict[str, Dict[str, Any]]:
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
                            result = data["result"]
                            # 如果 result 是字符串（JSON 格式），需要解析
                            if isinstance(result, str):
                                try:
                                    result = json.loads(result)
                                except:
                                    result = {}
                            paper_results[json_name.replace(".json", "")] = result
                        else:
                            paper_results[json_name.replace(".json", "")] = data

                    except Exception as e:
                        print(f"⚠️ 读取 {paper_id}/{json_name} 失败: {e}")
                        continue

            if paper_results:
                all_results[paper_id] = paper_results

        return all_results

    def get_available_paper_ids(self) -> list[str]:
        """
        获取所有可用的论文 ID

        Returns:
            论文 ID 列表
        """
        paper_ids = []

        for subdir in self.results_path.iterdir():
            if subdir.is_dir():
                # 检查是否包含至少一个 JSON 文件
                json_files = list(subdir.glob("*.json"))
                if json_files:
                    paper_ids.append(subdir.name)

        return sorted(paper_ids)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 初始化提取器
    extractor = ContentExtractor(agent_results_path="data/raw/agent_results")

    # 获取所有论文 ID
    paper_ids = extractor.get_available_paper_ids()
    print(f"✅ 找到 {len(paper_ids)} 篇文献")

    # 提取单篇文献元数据
    if paper_ids:
        paper_id = paper_ids[0]
        metadata = extractor.extract_metadata(paper_id)

        if metadata:
            print(f"\n📄 文献信息:")
            # ⭐ 安全打印标题（处理特殊字符）
            try:
                safe_title = metadata.title.encode('gbk', errors='replace').decode('gbk')
            except:
                safe_title = "（标题包含无法显示的字符）"
            print(f"  标题: {safe_title}")

            # ⭐ 安全打印作者
            try:
                safe_authors = ', '.join(metadata.authors).encode('gbk', errors='replace').decode('gbk')
            except:
                safe_authors = "（作者名包含无法显示的字符）"
            print(f"  作者: {safe_authors}")

            print(f"  年份: {metadata.year}")

            # ⭐ 安全打印期刊
            try:
                safe_journal = metadata.journal.encode('gbk', errors='replace').decode('gbk')
            except:
                safe_journal = "（期刊名包含无法显示的字符）"
            print(f"  期刊: {safe_journal}")

            print(f"  评分: {metadata.score}")

    # 批量提取
    summaries = extractor.extract_all_summaries(paper_ids[:5])

    print(f"\n📊 前 5 篇文献摘要:")
    for paper_id, summary in summaries.items():
        metadata = summary["metadata"]
        innovation = summary["innovation_summary"]

        print(f"\n  {paper_id}:")
        # ⭐ 安全打印标题
        try:
            safe_title = metadata.title[:60].encode('gbk', errors='replace').decode('gbk')
        except:
            safe_title = "（标题包含无法显示的字符）"
        print(f"    标题: {safe_title}...")
        print(f"    年份: {metadata.year}")
        if innovation:
            print(
                f"    创新点: {innovation['new_phenomena_count']} 现象, "
                f"{innovation['new_methods_count']} 方法, "
                f"{innovation['new_objects_count']} 对象"
            )
