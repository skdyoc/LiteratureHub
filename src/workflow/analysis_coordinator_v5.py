"""
Agent 分析协调器 V5 - 完全照抄 Wind-Aro 版本

⭐ 完全照抄 Wind-Aro 的实现：
1. Paper 数据模型（PaperMetadata, PaperContent）
2. MarkdownParser（解析 full.md）
3. prepare_paper_context 方法
4. 完整的分析流程
5. Prompt 模板加载
"""

import sys
import io
import json
import time
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# Windows UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ⭐ 导入 Prompt 加载器
from src.modules.analysis.prompts import load_prompt

import logging
logger = logging.getLogger("AgentAnalysisV5")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(handler)

# 全局锁
WRITE_LOCK = threading.Lock()
PROGRESS_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()


# ==================== 数据模型（照抄 Wind-Aro）====================

@dataclass
class PaperMetadata:
    """论文元数据"""
    title: str
    authors: List[str]
    year: int
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""


@dataclass
class PaperContent:
    """论文内容"""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    introduction: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    conclusion: str = ""
    full_content: str = ""  # ⭐ 完整的 full.md 内容


@dataclass
class Paper:
    """完整的论文对象"""
    folder_name: str
    metadata: PaperMetadata
    content: PaperContent
    full_content: str = ""  # ⭐ 完整的 full.md 内容

    def __init__(self, folder_name: str, metadata: PaperMetadata, content: PaperContent, full_content: str = ""):
        self.folder_name = folder_name
        self.metadata = metadata
        self.content = content
        self.full_content = full_content  # ⭐ 保存完整的 full.md 内容


# ==================== Markdown 解析器（照抄 Wind-Aro）====================

class SimpleMarkdownParser:
    """简化的 Markdown 解析器（照抄 Wind-Aro 的核心逻辑）"""

    def __init__(self):
        """预编译正则表达式"""
        self._title_pattern = re.compile(r'^#\s+(.+)$', re.MULTILINE)
        self._authors_pattern = re.compile(
            r'^([A-Z]\.\s*[A-Za-z]+(?:\s*[*,]\s*[A-Z]\.\s*[A-Za-z]+)*)',
            re.MULTILINE
        )
        self._year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        self._abstract_pattern = re.compile(
            r'#\s*A\s*b\s*s\s*t\s*r\s*a\s*c\s*t\s*\n+(.+?)(?=\n#|\Z)',
            re.IGNORECASE | re.DOTALL
        )
        self._keywords_pattern = re.compile(
            r'K\s*e\s*y\s*w\s*o\s*r\s*d\s*s\s*:\s*\n+((?:[^\n]+\n)+)',
            re.IGNORECASE
        )
        self._introduction_pattern = re.compile(
            r'#\s*\d+\.\s*I\s*n\s*t\s*r\s*o\s*d\s*u\s*c\s*t\s*i\s*o\s*n\s*\n+(.+?)(?=\n#|\n\d+\.|$)',
            re.IGNORECASE | re.DOTALL
        )
        self._conclusion_pattern = re.compile(
            r'#\s*\d+\.\s*(?:C\s*o\s*n\s*c\s*l\s*u\s*s\s*i\s*o\s*n\s*|D\s*i\s*s\s*c\s*u\s*s\s*s\s*i\s*o\s*n\s*)\s*\n+(.+?)(?=\n#|\n\d+\.|References|$)',
            re.IGNORECASE | re.DOTALL
        )

    def parse(self, folder_path: str) -> Paper:
        """
        解析单个文献文件夹

        Args:
            folder_path: 文献文件夹路径

        Returns:
            Paper 对象
        """
        folder = Path(folder_path)
        full_md_path = folder / "full.md"

        if not full_md_path.exists():
            raise FileNotFoundError(f"未找到 full.md 文件: {full_md_path}")

        # 读取 Markdown 文件
        with open(full_md_path, 'r', encoding='utf-8') as f:
            full_content = f.read()

        # 解析各个部分
        metadata = self._parse_metadata(full_content, folder)
        paper_content = self._parse_content(full_content)

        # 创建 Paper 对象
        paper = Paper(
            folder_name=folder.name,
            metadata=metadata,
            content=paper_content,
            full_content=full_content  # ⭐ 保存完整的 full.md 内容
        )

        return paper

    def _parse_metadata(self, content: str, folder: Path) -> PaperMetadata:
        """解析元数据"""
        # 提取标题
        title = self._extract_title(content)

        # 提取作者
        authors = self._extract_authors(content)

        # 提取年份（优先从文件夹名称提取）
        year = self._extract_year(content, folder)

        # 提取期刊信息
        journal = self._extract_journal(content)

        # 提取 DOI
        doi = self._extract_doi(content)

        # 创建元数据对象
        metadata = PaperMetadata(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            doi=doi
        )

        return metadata

    def _parse_content(self, content: str) -> PaperContent:
        """解析论文内容"""
        # 提取摘要
        abstract = self._extract_abstract(content)

        # 提取关键词
        keywords = self._extract_keywords(content)

        # 提取引言
        introduction = self._extract_introduction(content)

        # 提取结论
        conclusion = self._extract_conclusion(content)

        # 创建内容对象
        paper_content = PaperContent(
            abstract=abstract,
            keywords=keywords,
            introduction=introduction,
            conclusion=conclusion
        )

        return paper_content

    def _extract_title(self, content: str) -> str:
        """提取标题"""
        match = self._title_pattern.search(content)
        if match:
            return match.group(1).strip()
        return "Unknown"

    def _extract_authors(self, content: str) -> List[str]:
        """提取作者列表"""
        lines = content.split('\n')
        authors = []

        # 跳过标题行，查找作者行
        for i, line in enumerate(lines[1:20]):
            line = line.strip()
            # 匹配作者格式：首字母. 姓氏
            if re.match(r'^[A-Z]\.\s*[A-Za-z]+', line):
                # 清理作者字符串
                author_line = line.rstrip('*')
                # 分割作者（用逗号分隔）
                author_list = [a.strip() for a in author_line.split(',')]
                authors.extend(author_list)
                # 如果遇到空行或"#"开头的行，停止
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    break
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('#'):
                    break

        return authors

    def _extract_year(self, content: str, folder: Path) -> int:
        """提取发表年份"""
        # 1. 尝试从文件夹名称提取（格式：年份_论文标题）
        folder_match = re.match(r'^(\d{4})_', folder.name)
        if folder_match:
            return int(folder_match.group(1))

        # 2. 查找所有年份，选择最合理的（最近50年）
        years = self._year_pattern.findall(content)
        if years:
            # 选择最大的年份（最接近当前）
            current_year = datetime.now().year
            valid_years = [int(y) for y in years if 1970 <= int(y) <= current_year]
            if valid_years:
                return max(valid_years)

        # 3. 默认返回当前年份
        return datetime.now().year

    def _extract_journal(self, content: str) -> str:
        """提取期刊名称"""
        # 简化版：查找期刊信息
        journal_patterns = [
            r'Available online\s+\w+\s+\d{4}\s+(.+?)\n',
            r'Energy\s+(.+?)\s+Journal',
            r'Journal\s+of\s+(.+?)\s+,',
        ]

        for pattern in journal_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_doi(self, content: str) -> str:
        """提取 DOI"""
        doi_pattern = re.compile(
            r'(?:DOI|doi):\s*(10\.\d{4,}/[^\s]+)',
            re.IGNORECASE
        )
        match = doi_pattern.search(content)
        if match:
            return match.group(1)
        return ""

    def _extract_abstract(self, content: str) -> str:
        """提取摘要"""
        match = self._abstract_pattern.search(content)
        if match:
            abstract = match.group(1).strip()
            # 限制长度（前2000字符）
            return abstract[:2000]
        return ""

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        match = self._keywords_pattern.search(content)
        if match:
            keywords_str = match.group(1).strip()
            # 分割关键词（支持多种分隔符）
            keywords = re.split(r'[;,\n]+', keywords_str)
            return [k.strip() for k in keywords if k.strip()]
        return []

    def _extract_introduction(self, content: str) -> str:
        """提取引言"""
        match = self._introduction_pattern.search(content)
        if match:
            intro = match.group(1).strip()
            # 限制长度（前1000字符）
            return intro[:1000]
        return ""

    def _extract_conclusion(self, content: str) -> str:
        """提取结论"""
        match = self._conclusion_pattern.search(content)
        if match:
            conclusion = match.group(1).strip()
            # 限制长度（前500字符）
            return conclusion[:500]
        return ""


# ==================== 分析协调器 V5（完全照抄 Wind-Aro）====================

class AgentAnalysisCoordinatorV5:
    """Agent 分析协调器 V5 - 完全照抄 Wind-Aro 版本"""

    def __init__(
        self,
        markdown_root: Path,
        output_dir: str = "data/agent_results",
        output_subdir: str = "all",
        max_concurrent_papers: int = 10,
        max_concurrent_analyzers: int = 5,
        api_type: str = "deepseek",
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

        # ⭐ 初始化 Markdown 解析器（照抄 Wind-Aro）
        self.parser = SimpleMarkdownParser()

        # ⭐ 加载所有 Prompt 模板（照抄 Wind-Aro）
        self.prompt_templates = {
            "innovation": load_prompt("innovation_analyzer"),
            "motivation": load_prompt("motivation_detector"),
            "roadmap": load_prompt("roadmap_analyzer"),
            "mechanism": load_prompt("mechanism_analyzer"),
            "impact": load_prompt("impact_assessor"),
        }

        # 分析器配置（照抄 Wind-Aro）
        self.analyzer_config = {
            "innovation": {
                "prompt_file": "innovation_analyzer",
                "agent_type": "ai-engineer",
            },
            "motivation": {
                "prompt_file": "motivation_detector",
                "agent_type": "data-science:business-analyst",
            },
            "roadmap": {
                "prompt_file": "roadmap_analyzer",
                "agent_type": "backend-development:backend-architect",
            },
            "mechanism": {
                "prompt_file": "mechanism_analyzer",
                "agent_type": "code-explain",
            },
            "impact": {
                "prompt_file": "impact_assessor",
                "agent_type": "observability-monitoring:performance-engineer",
            },
        }

        # 初始化 API 客户端
        self._init_api_client()

        logger.info(f"协调器 V5 初始化完成（照抄 Wind-Aro）:")
        logger.info(f"  - Markdown 目录: {self.markdown_root}")
        logger.info(f"  - 输出目录: {self.output_dir}")
        logger.info(f"  - 外层并发: {max_concurrent_papers}")
        logger.info(f"  - 内层并发: {max_concurrent_analyzers}")
        logger.info(f"  - Prompt 模板: {len(self.prompt_templates)} 个")

    def _init_api_client(self):
        """初始化 API 客户端"""
        try:
            if self.api_type == "deepseek":
                # ⭐ 使用 DeepSeek（照抄 Wind-Aro）
                from src.api.deepseek_client import DeepSeekParallelAnalyzer

                # ⭐ 修复路径：使用项目根目录下的私人信息目录
                deepseek_keys_file = "d:/xfs/phd/github项目/.私人信息/deepseek_api_keys_encrypted.txt"

                self.api_client = DeepSeekParallelAnalyzer(
                    api_keys_file=deepseek_keys_file,
                    max_workers=self.max_concurrent_analyzers,
                )
                logger.info(f"DeepSeek API 客户端初始化成功（混合模式: chat + reasoner, 并发: {self.max_concurrent_analyzers}）")
            else:
                raise ValueError(f"不支持的 API 类型: {self.api_type}")

        except Exception as e:
            logger.error(f"API 客户端初始化失败: {e}")
            self.api_client = None

    def _load_papers_from_markdown(self) -> List[Paper]:
        """从 Markdown 目录加载论文（照抄 Wind-Aro）"""
        papers = []

        if not self.markdown_root.exists():
            logger.error(f"Markdown 目录不存在: {self.markdown_root}")
            return []

        logger.info(f"从 Markdown 目录加载论文: {self.markdown_root}")

        paper_dirs = [d for d in sorted(self.markdown_root.iterdir()) if d.is_dir()]

        for paper_dir in paper_dirs:
            try:
                # ⭐ 使用 MarkdownParser 解析论文（照抄 Wind-Aro）
                paper = self.parser.parse(str(paper_dir))
                papers.append(paper)
            except Exception as e:
                logger.warning(f"加载论文 {paper_dir.name} 失败: {e}")

        logger.info(f"加载了 {len(papers)} 篇论文")
        return papers

    def prepare_paper_context(self, paper: Paper) -> Dict[str, Any]:
        """
        准备论文上下文（⭐ 完全照抄 Wind-Aro + 添加 full.md 内容）

        返回给 API 的结构化论文信息
        """
        return {
            "title": paper.metadata.title,
            "authors": paper.metadata.authors,
            "year": paper.metadata.year,
            "journal": paper.metadata.journal,
            "abstract": paper.content.abstract or "",
            "keywords": paper.content.keywords or [],
            "introduction": (paper.content.introduction or "")[:1000],
            "conclusion": (paper.content.conclusion or "")[:500],
            # ⭐⭐⭐ 添加完整的 full.md 内容（截取前 10000 字符以避免超过 token 限制）
            "full_content": (paper.full_content or "")[:10000],
        }

    def _check_all_results(self, paper_id: str) -> Dict:
        """检查 all/ 目录是否有完整结果"""
        all_dir = self.output_root / "all" / paper_id
        if not all_dir.exists():
            return {"exists": False}

        results = {}
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            result_file = all_dir / f"{analyzer}.json"
            results[analyzer] = {"exists": result_file.exists()}

        results["exists"] = any(r["exists"] for r in results.values())
        return results

    def _copy_from_all(self, paper_id: str):
        """从 all/ 复制到分类目录"""
        all_dir = self.output_root / "all" / paper_id
        target_dir = self.output_dir / paper_id
        target_dir.mkdir(parents=True, exist_ok=True)

        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            src_file = all_dir / f"{analyzer}.json"
            if src_file.exists():
                import shutil
                shutil.copy2(src_file, target_dir / f"{analyzer}.json")

    def analyze_single_paper(self, paper: Paper, skip_completed: bool = True) -> Dict[str, Any]:
        """
        分析单篇论文（⭐ 完全照抄 Wind-Aro）
        """
        paper_id = paper.folder_name
        paper_context = self.prepare_paper_context(paper)

        with LOG_LOCK:
            logger.info(f"开始分析论文: {paper.metadata.title[:50]}...")

        results = {}

        # 确定需要运行的分析器
        analyzers_to_run = []
        for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
            # 简化：不检查 skip_completed，直接运行
            analyzers_to_run.append(analyzer)

        # 使用 API 并行运行所有分析器
        if self.api_client:
            # 真正的 API 调用（⭐ 照抄 Wind-Aro）
            analyzer_prompts = {}
            for analyzer in analyzers_to_run:
                # 获取 Prompt 模板
                prompt_template = self.prompt_templates[analyzer]
                # 构建完整的 Prompt（⭐ 照抄 Wind-Aro 的格式）
                full_prompt = f"{prompt_template}\n\n论文数据:\n{json.dumps(paper_context, indent=2, ensure_ascii=False)}"
                analyzer_prompts[analyzer] = full_prompt

            # 并行调用 API
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

    def set_progress_callback(self, callback):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，签名为 callback(analyzer, status, is_start)
        """
        self.progress_callback = callback

    def _notify_progress(self, message: str, analyzer: str = None):
        """通知进度更新"""
        if hasattr(self, 'progress_callback') and self.progress_callback:
            try:
                if analyzer:
                    self.progress_callback(analyzer, message, False)
                else:
                    self.progress_callback("general", message, False)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")

    def _load_analysis_index(self) -> Dict:
        """加载分析索引"""
        index_file = self.output_dir / "analysis_index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 返回默认索引
        return {
            "version": "2.0",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_papers": 0,
                "analyzed_papers": 0,
                "partial_papers": 0,
                "pending_papers": 0,
                "last_updated": None
            },
            "papers": {}
        }

    def _save_analysis_index(self, index: Dict):
        """保存分析索引"""
        index_file = self.output_dir / "analysis_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _batch_update_all_papers(self, papers: List[Paper]):
        """
        批量更新所有论文的索引（统一在 batch_analyze 结束时调用）

        Args:
            papers: 所有处理过的论文列表（复制的 + 分析的）
        """
        with WRITE_LOCK:
            # 只加载一次索引
            index = self._load_analysis_index()

            updated_count = 0
            total_papers = len(papers)

            with LOG_LOCK:
                logger.info(f"正在扫描 {total_papers} 篇论文的分析结果...")

            for i, paper in enumerate(papers):
                paper_id = paper.folder_name
                paper_dir = self.output_dir / paper_id

                # 确保论文条目存在
                if paper_id not in index["papers"]:
                    index["papers"][paper_id] = {
                        "paper_id": paper_id,
                        "analyzers": {},
                        "overall_status": "pending"
                    }

                # 扫描所有分析器结果文件
                for analyzer in ["innovation", "motivation", "roadmap", "mechanism", "impact"]:
                    result_file = paper_dir / f"{analyzer}.json"
                    if result_file.exists():
                        index["papers"][paper_id]["analyzers"][analyzer] = {
                            "status": "completed",
                            "file": f"{analyzer}.json",
                            "analyzed_at": datetime.fromtimestamp(result_file.stat().st_mtime).isoformat(),
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

                # ⭐ 每 100 篇论文输出一次进度
                if (i + 1) % 100 == 0:
                    with LOG_LOCK:
                        logger.info(f"  索引扫描进度: {i+1}/{total_papers} ({(i+1)/total_papers*100:.1f}%)")

            # 更新元数据
            index["metadata"]["total_papers"] = total_papers
            index["metadata"]["analyzed_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "completed"
            )
            index["metadata"]["partial_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "partial"
            )
            index["metadata"]["pending_papers"] = sum(
                1 for p in index["papers"].values()
                if p["overall_status"] == "pending"
            )
            index["metadata"]["last_updated"] = datetime.now().isoformat()

            # 只保存一次索引
            self._save_analysis_index(index)

            with LOG_LOCK:
                logger.info(f"✓ 索引更新完成: {updated_count} 个分析器状态, {total_papers} 篇论文")

    def batch_analyze(
        self,
        max_papers: Optional[int] = None,
        skip_completed: bool = True,
    ) -> Dict[str, Any]:
        """
        批量分析（⭐ 完全照抄 Wind-Aro 结构）
        """
        try:
            with LOG_LOCK:
                logger.info("=" * 70)
                logger.info("开始批量 Agent 分析（V5：完全照抄 Wind-Aro 版本）")
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

            # ⭐ MinerU 预检查：区分可复制的论文和需要分析的论文
            papers_to_copy = []
            papers_to_analyze = []

            for paper in papers:
                paper_id = paper.folder_name

                # 检查 all/ 目录是否有完整结果
                if self.output_subdir != "all" and skip_completed:
                    all_results = self._check_all_results(paper_id)

                    # 如果 all/ 有完整结果（至少有 innovation），可以复制
                    if all_results.get("exists") and all_results.get("innovation", {}).get("exists"):
                        papers_to_copy.append(paper)
                    else:
                        papers_to_analyze.append(paper)
                else:
                    # 不跳过已完成，需要分析
                    papers_to_analyze.append(paper)

            with LOG_LOCK:
                logger.info(f"预检查完成:")
                logger.info(f"  - 可从 all/ 复制: {len(papers_to_copy)} 篇")
                logger.info(f"  - 需要 API 分析: {len(papers_to_analyze)} 篇")

            # ⭐ 批量复制可以从 all/ 复制的论文（照抄 MinerU）
            if papers_to_copy:
                with LOG_LOCK:
                    logger.info(f"开始批量复制 {len(papers_to_copy)} 篇论文...")

                copy_start = time.time()
                copied_count = 0

                for paper in papers_to_copy:
                    paper_id = paper.folder_name
                    try:
                        self._copy_from_all(paper_id)
                        copied_count += 1
                    except Exception as e:
                        with LOG_LOCK:
                            logger.error(f"复制论文 {paper_id} 失败: {e}")

                copy_elapsed = time.time() - copy_start
                with LOG_LOCK:
                    logger.info(f"✓ 批量复制完成: {copied_count} 篇, 耗时 {copy_elapsed:.2f} 秒")

            # ⭐⭐⭐ Agent 调用模块：双层并发（外层线程池 + 内层并发）
            completed = 0
            failed = 0

            if papers_to_analyze:
                with LOG_LOCK:
                    logger.info(f"\n开始 Agent 并发分析（外层并发: {self.max_concurrent_papers} 篇论文）")

                def process_paper(paper, index):
                    """处理单篇论文（外层并发）"""
                    try:
                        with LOG_LOCK:
                            logger.info(f"[{index+1}/{len(papers_to_analyze)}] 处理论文: {paper.folder_name[:40]}...")

                        # 检查 API 客户端是否可用
                        if not self.api_client:
                            with LOG_LOCK:
                                logger.error(f"API 客户端未初始化，无法分析论文: {paper.folder_name}")
                            return {"success": False, "paper_id": paper.folder_name, "error": "API 客户端未初始化"}

                        # 分析论文（内层并发在 api_client.analyze_paper 内部）
                        results = self.analyze_single_paper(paper, skip_completed)

                        # ⭐ 检查是否真的生成了分析结果
                        if not results:
                            with LOG_LOCK:
                                logger.error(f"论文分析未生成任何结果: {paper.folder_name}")
                            return {"success": False, "paper_id": paper.folder_name, "error": "未生成分析结果"}

                        # 检查是否有至少一个成功的分析器
                        has_success = any(r.get("success") for r in results.values())
                        if not has_success:
                            with LOG_LOCK:
                                logger.error(f"论文所有分析器均失败: {paper.folder_name}")
                            return {"success": False, "paper_id": paper.folder_name, "error": "所有分析器均失败"}

                        return {"success": True, "paper_id": paper.folder_name, "results": results}
                    except Exception as e:
                        with LOG_LOCK:
                            logger.error(f"分析论文 {paper.folder_name} 失败: {e}")
                        return {"success": False, "paper_id": paper.folder_name, "error": str(e)}

                # ⭐ 外层并发：使用线程池处理多篇论文
                with ThreadPoolExecutor(max_workers=self.max_concurrent_papers) as executor:
                    # 提交所有任务
                    future_to_paper = {}
                    for i, paper in enumerate(papers_to_analyze):
                        future = executor.submit(process_paper, paper, i)
                        future_to_paper[future] = paper

                    # 收集结果
                    for future in as_completed(future_to_paper):
                        paper = future_to_paper[future]
                        try:
                            result = future.result()
                            if result.get("success"):
                                completed += 1
                                with LOG_LOCK:
                                    logger.info(f"✓ 论文分析完成: {paper.folder_name[:40]}...")
                            else:
                                failed += 1
                        except Exception as e:
                            with LOG_LOCK:
                                logger.error(f"处理论文 {paper.folder_name} 时发生异常: {e}")
                            failed += 1

            # ⭐ 统一更新所有论文的索引（批量复制 + API 分析完成后）
            all_processed_papers = papers_to_copy + papers_to_analyze
            if all_processed_papers:
                with LOG_LOCK:
                    logger.info(f"\n开始批量更新索引（{len(all_processed_papers)} 篇论文）...")
                self._batch_update_all_papers(all_processed_papers)

            # 统计
            elapsed_time = time.time() - start_time
            total_papers = len(papers_to_copy) + len(papers_to_analyze)

            with LOG_LOCK:
                logger.info("\n" + "=" * 70)
                logger.info("批量分析完成！")
                logger.info(f"总论文数: {total_papers}")
                logger.info(f"从 all/ 复制: {len(papers_to_copy)}")
                logger.info(f"API 分析: {completed}")
                logger.info(f"失败: {failed}")
                logger.info(f"总耗时: {elapsed_time:.2f} 秒")
                logger.info("=" * 70)

            return {
                "total": total_papers,
                "completed": len(papers_to_copy) + completed,
                "copied_from_all": len(papers_to_copy),
                "analyzed_with_api": completed,
                "failed": failed,
                "elapsed_time": elapsed_time,
            }

        except Exception as e:
            # ⭐ 捕获所有异常，确保总是返回一个有效的字典
            with LOG_LOCK:
                logger.error(f"批量分析发生异常: {e}")
                import traceback
                logger.error(traceback.format_exc())

            # 返回错误信息
            return {
                "total": 0,
                "completed": 0,
                "copied_from_all": 0,
                "analyzed_with_api": 0,
                "failed": 0,
                "error": str(e),
            }


def main():
    """主函数"""
    coordinator = AgentAnalysisCoordinatorV5(
        markdown_root=Path("data/projects/wind_aero/markdown/all"),
        output_subdir="categories/test_v5",
        api_type="deepseek",
    )

    stats = coordinator.batch_analyze(max_papers=2)

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
