# ========= Copyright 2025-2026 @ LiteratureHub All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2025-2026 @ LiteratureHub All Rights Reserved. =========

"""
Page 1 工作流程管理器

完整的文献管理工作流程：
1. Elsevier 搜索 → 保存 JSON 到 metadata/
2. SciHub 下载 → 年份_标题.pdf 格式到 all/
3. 失败导出 NoteExpress → 用户手动下载到 temp/
4. 处理 temp/ → 匹配标题重命名，移到 all/
5. 手动下载列表 → 用户下载后处理
6. 分类 → 基于内容智能分类
7. MinerU 转换 → PDF 转 Markdown
"""

import json
import re
import os
import shutil
import asyncio
import logging
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from difflib import SequenceMatcher

from ..search.elsevier_searcher import ElsevierSearcher
from ..search.keyword_translator import KeywordTranslationAgent
from ..download.scihub_downloader import SciHubDownloader
from ..download.multi_source_downloader import MultiSourceDownloader
from ..download.vpn_detector import VPNDetector
from ..download.proxy_manager import create_default_proxy_manager
from ..api.mineru_client import MinerUClient, ModelVersion, parse_pdf_file, parse_pdf_files
from .batch_classify import BatchPaperClassifier

# 配置文件路径
_config_file = Path(__file__).parent.parent.parent / "config" / "api_keys.yaml"


@dataclass
class PaperInfo:
    """文献信息"""
    doi: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    citations: Optional[int] = None
    pdf_downloaded: bool = False
    pdf_path: Optional[str] = None
    pdf_filename: Optional[str] = None
    source: str = "elsevier"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Page1Workflow:
    """Page 1 工作流程管理器

    完整的文献管理工作流程。

    用法：
    ```python
    workflow = Page1Workflow(
        project_dir="data/projects/wind_aero",
        api_key="your_elsevier_api_key"
    )

    # 执行搜索
    await workflow.search_elsevier(
        keywords=["wind turbine", "aerodynamic"],
        max_results=100
    )

    # 执行下载
    results = workflow.run_download_workflow()

    # 处理 temp 目录
    workflow.process_temp_pdfs()

    # 分类
    workflow.classify_papers(category_keywords="大型风机气动")

    # 转换 Markdown
    workflow.convert_to_markdown()
    ```
    """

    def __init__(
        self,
        project_dir: str,
        api_key: str = None,
        proxy_url: str = None
    ):
        """初始化工作流程

        Args:
            project_dir: 项目目录
            api_key: Elsevier API 密钥（可选，不提供则自动从配置文件读取）
            proxy_url: 代理 URL（可选，自动检测）
            mineru_path: MinerU 路径（可选）
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.info("[DEBUG] Page1Workflow.__init__() 开始执行")

        self.project_dir = Path(project_dir)

        # API 密钥优先级：参数 > 配置文件 > None
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_elsevier_api_key()

        self.proxy_url = proxy_url

        # 加载 MinerU 配置
        self.mineru_config = self._load_mineru_config()

        # 设置目录
        self._setup_directories()

        # 初始化组件
        self.searcher = ElsevierSearcher(api_key=self.api_key) if self.api_key else None

        # 关键词翻译 Agent
        self.translator = KeywordTranslationAgent()

        # 检测代理
        proxy_manager = None
        if not proxy_url:
            detector = VPNDetector()
            proxy_info = detector.detect()
            self.proxy_url = proxy_info.proxy_url if proxy_info else None
        else:
            self.proxy_url = proxy_url

        # 创建代理管理器
        proxy_manager = create_default_proxy_manager()

        # 从配置文件读取 Unpaywall 邮箱
        unpaywall_email = self._load_unpaywall_email()

        # 多源下载器（Unpaywall 优先 + SciHub 备用）
        self.downloader = MultiSourceDownloader(
            email=unpaywall_email,  # 从配置文件读取
            proxy_manager=proxy_manager,
            output_dir=str(self.all_dir),
            prefer_unpaywall=True  # 优先使用 Unpaywall（合法、不需要 VPN）
        )

        # 保留 SciHub 下载器以兼容旧代码
        self.scihub = self.downloader.scihub

        self.logger.info("多源下载器已初始化（Unpaywall 优先 + SciHub 备用）")

        # 状态
        self.logger.info("初始化工作流状态...")
        self.status = {
            "search_results": 0,
            "step1_success": 0,
            "step1_failed": 0,
            "temp_processed": 0,
            "manual_downloaded": 0,
            "classified": 0,
            "converted": 0
        }
        self.logger.info("Page1Workflow 初始化完成！")

    def _setup_directories(self):
        """设置目录结构"""
        # PDF 目录
        self.all_dir = self.project_dir / "pdfs" / "all"
        self.temp_dir = self.project_dir / "pdfs" / "temp"
        self.categories_dir = self.project_dir / "pdfs" / "categories"

        # 元数据目录
        self.metadata_dir = self.project_dir / "metadata"

        # 导出目录
        self.exports_dir = self.project_dir / "exports"

        # Markdown 目录
        self.markdown_dir = self.project_dir / "markdown"
        self.markdown_categories_dir = self.markdown_dir / "categories"  # 新增：分类 Markdown 目录

        # 创建所有目录
        for d in [self.all_dir, self.temp_dir, self.categories_dir,
                  self.metadata_dir, self.exports_dir, self.markdown_dir,
                  self.markdown_categories_dir]:  # 新增
            d.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"目录结构已创建: {self.project_dir}")

    def _load_elsevier_api_key(self) -> Optional[str]:
        """从配置文件加载 Elsevier API 密钥

        Returns:
            API 密钥，失败返回 None
        """
        try:
            if not _config_file.exists():
                return None

            with open(_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 读取 Elsevier API 密钥
            elsevier_config = config.get('elsevier', {})
            api_key = elsevier_config.get('api_key', '')

            if api_key and api_key != 'your_elsevier_api_key':
                self.logger.info("已从配置文件加载 Elsevier API 密钥")
                return api_key

        except Exception as e:
            self.logger.warning(f"从配置文件加载 API 密钥失败: {e}")

        return None

    def _load_mineru_config(self) -> dict:
        """加载 MinerU 配置

        Returns:
            MinerU 配置字典，包含 api_url 和 token
        """
        config = {
            "api_url": "http://localhost:9999/file_parse",
            "token": ""
        }

        try:
            # 尝试从私人信息文件夹读取 token
            private_info = Path("D:/xfs/phd/.私人信息")
            token_file = private_info / "mineru_token.txt"

            if token_file.exists():
                with open(token_file, 'r', encoding='utf-8') as f:
                    config["token"] = f.read().strip()
                self.logger.info("已加载 MinerU token")
            else:
                self.logger.warning("未找到 MinerU token 文件")

        except Exception as e:
            self.logger.warning(f"加载 MinerU 配置失败: {e}")

        return config

    def _load_unpaywall_email(self) -> str:
        """从配置文件加载 Unpaywall 邮箱

        Returns:
            Unpaywall 邮箱，失败返回默认邮箱
        """
        try:
            if not _config_file.exists():
                return "literaturehub@example.com"

            with open(_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 读取 Unpaywall 邮箱
            unpaywall_config = config.get('unpaywall', {})
            email = unpaywall_config.get('email', '')

            if email:
                self.logger.info(f"已从配置文件加载 Unpaywall 邮箱: {email}")
                return email

        except Exception as e:
            self.logger.warning(f"从配置文件加载 Unpaywall 邮箱失败: {e}")

        return "literaturehub@example.com"

    # ==================== Step 1: Elsevier 搜索 ====================

    async def search_elsevier(
        self,
        keywords: List[str],
        max_results: int = 100,
        year_range: Tuple[int, int] = None,
        exclude_keywords: List[str] = None,
        match_mode: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """执行 Elsevier 搜索

        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            year_range: 年份范围
            exclude_keywords: 排除关键词
            match_mode: 匹配模式 {"fields": ["title", "keywords", "abstract"], "combination": "all" | "any"}

        Returns:
            搜索结果列表
        """
        if not self.searcher:
            raise ValueError("Elsevier API 密钥未配置")

        # 翻译中文关键词为英文
        original_keywords = keywords.copy()
        translated_keywords = self.translator.translate_keywords(keywords)

        if translated_keywords != keywords:
            self.logger.info(f"关键词翻译: {keywords} -> {translated_keywords}")
            keywords = translated_keywords
        else:
            # 检测是否有中文关键词（翻译失败）
            import re
            has_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)
            if has_chinese:
                self.logger.warning(f"检测到中文关键词但翻译失败（需配置 GLM API 密钥）: {keywords}")
                self.logger.warning(f"将在 Elsevier 搜索中使用原始中文关键词，可能无法获得结果")

        self.logger.info(f"开始 Elsevier 搜索: {keywords}")

        # 执行搜索
        results = await self.searcher.search(
            keywords=keywords,
            max_results=max_results,
            year_range=year_range,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode
        )

        # 保存搜索结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_file = self.metadata_dir / f"elsevier_search_{timestamp}.json"

        search_data = {
            "keywords": keywords,
            "original_keywords": original_keywords if original_keywords != keywords else None,
            "exclude_keywords": exclude_keywords,
            "year_range": year_range,
            "max_results": max_results,
            "actual_results": len(results),
            "searched_at": datetime.now().isoformat(),
            "papers": results
        }

        with open(search_file, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"搜索结果已保存: {search_file}")

        # 更新总元数据
        self._update_all_metadata(results)

        self.status["search_results"] = len(results)

        return results

    def _update_all_metadata(self, new_papers: List[Dict]):
        """更新总元数据文件"""
        metadata_file = self.all_dir / "metadata.json"

        # 加载现有元数据
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = []

        # 合并（基于 DOI 去重）
        existing_dois = {p.get('doi') for p in existing}
        for paper in new_papers:
            if paper.get('doi') not in existing_dois:
                # 为新文献初始化 pdf_downloaded 字段
                paper['pdf_downloaded'] = False
                existing.append(paper)

        # 保存
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        self.logger.info(f"元数据已更新: {len(existing)} 条")

    # ==================== Step 2: SciHub 下载 ====================

    def run_download_workflow(
        self,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """执行下载工作流程

        Args:
            progress_callback: 进度回调

        Returns:
            下载结果统计
        """
        # 加载元数据
        metadata_file = self.all_dir / "metadata.json"
        if not metadata_file.exists():
            self.logger.error("元数据文件不存在，请先执行搜索")
            return {"error": "No metadata found"}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        # 过滤未下载的
        to_download = [p for p in papers if not p.get('pdf_downloaded')]

        self.logger.info(f"开始下载: {len(to_download)} 篇文献")

        # 执行下载
        success = 0
        failed = []

        for i, paper in enumerate(to_download):
            doi = paper.get('doi')
            if not doi:
                continue

            # 下载
            result = self.scihub.download(doi)

            if result.success:
                # 重命名为 年份_标题.pdf
                new_filename = self._generate_filename(paper)
                new_path = self.all_dir / new_filename

                if result.pdf_path and Path(result.pdf_path).exists():
                    shutil.move(result.pdf_path, new_path)

                    paper['pdf_downloaded'] = True
                    paper['pdf_path'] = str(new_path)
                    paper['pdf_filename'] = new_filename
                    success += 1
            else:
                failed.append(paper)

            if progress_callback:
                progress_callback(i + 1, len(to_download), result)

        # 更新元数据
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

        # 导出失败的为 NoteExpress
        if failed:
            self._export_failed_to_noteexpress(failed)

        self.status["step1_success"] = success
        self.status["step1_failed"] = len(failed)

        return {
            "total": len(to_download),
            "success": success,
            "failed": len(failed)
        }

    def _generate_filename(self, paper: Dict) -> str:
        """生成文件名：年份_标题.pdf"""
        year = paper.get('year', 'unknown')
        title = paper.get('title', 'untitled')

        # 清理标题
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'[\s-]+', '_', title)
        title = title[:100]  # 限制长度

        return f"{year}_{title}.pdf"

    def _export_failed_to_noteexpress(self, papers: List[Dict]):
        """导出失败的文献为 NoteExpress 格式"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.exports_dir / f"noteexpress_{timestamp}.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            for paper in papers:
                f.write("{Reference Type}: Generic\n")
                f.write(f"{{Author}}: {'; '.join(paper.get('authors', []))}\n")
                f.write(f"{{Title}}: {paper.get('title', '')}\n")

                if paper.get('year'):
                    f.write(f"{{Date}}: {paper['year']}\n")

                if paper.get('keywords'):
                    f.write(f"{{Keywords}}: {'; '.join(paper['keywords'])}\n")

                if paper.get('abstract'):
                    abstract = paper['abstract'].replace('\n', ' ').strip()
                    f.write(f"{{Abstract}}: {abstract}\n")

                if paper.get('doi'):
                    f.write(f"{{DOI}}: {paper['doi']}\n")

                if paper.get('journal'):
                    f.write(f"{{Journal}}: {paper['journal']}\n")

                f.write("\n\n")

        self.logger.info(f"NoteExpress 文件已导出: {output_file}")

        # 同时生成 JSON 供后续处理
        json_file = self.exports_dir / f"failed_papers_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

    # ==================== Step 3: 处理 temp 目录 ====================

    def process_temp_pdfs(self) -> int:
        """处理 temp 目录中的 PDF

        匹配文件名标题与元数据，重命名为 年份_标题.pdf，移动到 all/

        改进的匹配逻辑：
        1. 首先尝试从文件名提取 DOI 进行精确匹配
        2. 如果没有 DOI，使用宽松的标题匹配
        3. 支持文件名被截断的情况

        Returns:
            处理的文件数量
        """
        if not self.temp_dir.exists():
            return 0

        # 加载总元数据
        metadata_file = self.all_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            all_papers = json.load(f)

        # 创建 DOI 到文献的映射（用于快速查找）
        doi_to_paper = {}
        for paper in all_papers:
            doi = paper.get('doi')
            if doi:
                doi_to_paper[doi.lower()] = paper

        processed = 0
        failed_match = []

        for pdf_file in self.temp_dir.glob("*.pdf"):
            filename = pdf_file.name

            # 策略 1: 尝试从文件名提取 DOI
            doi = self._extract_doi_from_filename(filename)
            matched_paper = None

            if doi and doi.lower() in doi_to_paper:
                # DOI 匹配成功
                matched_paper = doi_to_paper[doi.lower()]
                self.logger.info(f"DOI 匹配: {doi}")
            else:
                # 策略 2: 使用改进的标题匹配
                extracted_title = self._extract_title_from_filename(filename)
                matched_paper = self._match_paper_improved(extracted_title, all_papers, filename)

                if matched_paper:
                    self.logger.info(f"标题匹配: {matched_paper.get('title', 'N/A')[:60]}...")
                else:
                    self.logger.warning(f"无法匹配: {filename}")
                    failed_match.append(filename)
                    continue

            # 生成新文件名并移动
            new_filename = self._generate_filename(matched_paper)
            new_path = self.all_dir / new_filename

            # 移动文件
            try:
                shutil.move(str(pdf_file), new_path)
            except Exception as e:
                self.logger.error(f"移动文件失败: {filename} -> {e}")
                continue

            # 更新元数据
            matched_paper['pdf_downloaded'] = True
            matched_paper['pdf_path'] = str(new_path)
            matched_paper['pdf_filename'] = new_filename

            self.logger.info(f"处理完成: {filename} -> {new_filename}")
            processed += 1

        # 保存更新后的元数据
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)

        # 输出匹配失败的文件
        if failed_match:
            self.logger.warning(f"有 {len(failed_match)} 个文件无法匹配:")
            for fname in failed_match:
                self.logger.warning(f"  - {fname}")

        self.status["temp_processed"] = processed

        return processed

    def _load_failed_papers(self) -> List[Dict]:
        """加载失败的文献列表"""
        failed_papers = []

        for json_file in self.exports_dir.glob("failed_papers_*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                failed_papers.extend(json.load(f))

        return failed_papers

    def _extract_title_from_filename(self, filename: str) -> str:
        """从文件名提取标题"""
        name = filename.replace('.pdf', '')
        # 移除年份前缀
        name = re.sub(r'^\d{4}_', '', name)
        # 移除 DOI 后缀
        name = re.sub(r'_10\.\d+.*$', '', name)
        # 下划线转空格
        name = name.replace('_', ' ')
        return name.strip()

    def _match_paper(self, title: str, papers: List[Dict], threshold: float = 0.8) -> Optional[Dict]:
        """匹配文献"""
        def normalize(t):
            t = t.lower()
            t = re.sub(r'[^\w\s]', ' ', t)
            return ' '.join(t.split())

        norm_title = normalize(title)
        best_match = None
        best_score = 0.0

        for paper in papers:
            paper_title = paper.get('title', '')
            norm_paper = normalize(paper_title)

            # 包含匹配
            if norm_title in norm_paper or norm_paper in norm_title:
                return paper

            # 相似度匹配
            score = SequenceMatcher(None, norm_title, norm_paper).ratio()
            if score > best_score:
                best_score = score
                best_match = paper

        if best_score >= threshold:
            return best_match

        return None

    def _extract_doi_from_filename(self, filename: str) -> Optional[str]:
        """从文件名提取 DOI

        支持多种 DOI 格式：
        - 10.xxxx/xxxxx（标准格式）
        - 10_xxxx_xxxx（下划线代替斜杠）

        Args:
            filename: 文件名

        Returns:
            提取的 DOI，如果未找到则返回 None
        """
        import re
        name = filename.replace('.pdf', '')

        # 标准 DOI 格式：10.xxxx/xxxxx
        doi_pattern = r'10\.\d{4,}/[^\s_]+(?:_[^\s_]+)*'
        match = re.search(doi_pattern, name)
        if match:
            return match.group(0)

        # 下划线格式的 DOI：10_xxxx_xxxx
        if name.startswith("10_"):
            return name.replace("_", "/")

        return None

    def _match_paper_improved(self, title: str, papers: List[Dict], filename: str = "") -> Optional[Dict]:
        """改进的文献匹配方法

        支持多种匹配策略：
        1. 精确标题匹配
        2. 包含匹配（处理截断的文件名）
        3. 关键词匹配（提取核心关键词）
        4. 相似度匹配（较低阈值）

        Args:
            title: 从文件名提取的标题
            papers: 文献列表
            filename: 原始文件名（用于调试）

        Returns:
            匹配的文献，如果未找到则返回 None
        """
        def normalize(t):
            t = t.lower()
            t = re.sub(r'[^\w\s]', ' ', t)
            return ' '.join(t.split())

        norm_title = normalize(title)

        # 策略 1: 精确匹配
        for paper in papers:
            paper_title = paper.get('title', '')
            if norm_title == normalize(paper_title):
                return paper

        # 策略 2: 包含匹配（处理截断）
        for paper in papers:
            paper_title = paper.get('title', '')
            norm_paper = normalize(paper_title)

            # 文件名标题在文献标题中（处理截断）
            if norm_title in norm_paper:
                # 确保匹配长度足够（避免误匹配）
                if len(norm_title) >= 30:  # 至少 30 个字符
                    return paper

            # 文献标题在文件名标题中
            if norm_paper in norm_title:
                if len(norm_paper) >= 30:
                    return paper

        # 策略 3: 关键词匹配（提取核心关键词）
        # 提取长单词（5个字符以上）作为关键词
        words = [w for w in norm_title.split() if len(w) >= 5]
        if len(words) >= 3:
            # 使用前 3 个长关键词进行匹配
            keywords = words[:3]

            for paper in papers:
                paper_title = paper.get('title', '')
                norm_paper = normalize(paper_title)

                # 检查是否所有关键词都存在
                if all(kw in norm_paper for kw in keywords):
                    return paper

        # 策略 4: 相似度匹配（较低阈值）
        best_match = None
        best_score = 0.0

        for paper in papers:
            paper_title = paper.get('title', '')
            norm_paper = normalize(paper_title)

            score = SequenceMatcher(None, norm_title, norm_paper).ratio()
            if score > best_score:
                best_score = score
                best_match = paper

        if best_score >= 0.75:  # 降低阈值到 0.75
            return best_match

        return None

    # ==================== Step 4: 手动下载列表 ====================

    def generate_manual_download_list(self) -> str:
        """生成手动下载列表

        Returns:
            列表文件路径
        """
        # 加载元数据
        metadata_file = self.all_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        # 找出未下载的
        not_downloaded = [p for p in papers if not p.get('pdf_downloaded')]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.exports_dir / f"manual_download_{timestamp}.json"

        download_list = []
        for p in not_downloaded:
            download_list.append({
                "doi": p.get('doi'),
                "title": p.get('title'),
                "authors": p.get('authors', []),
                "year": p.get('year'),
                "journal": p.get('journal')
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(download_list, f, ensure_ascii=False, indent=2)

        self.logger.info(f"手动下载列表已生成: {output_file} ({len(download_list)} 篇)")

        return str(output_file)

    # ==================== Step 5: 分类 ====================

    def classify_papers(
        self,
        category_name: str,
        scale_keywords: List[str] = None,
        aero_keywords: List[str] = None
    ) -> int:
        """分类文献

        Args:
            category_name: 分类名称
            scale_keywords: 规模关键词
            aero_keywords: 气动关键词

        Returns:
            匹配的文献数量
        """
        # 默认关键词
        if scale_keywords is None:
            scale_keywords = [
                'large-scale', 'large scale', 'megawatt', 'mw ', 'offshore',
                'utility-scale', 'multi-megawatt', '大型', '兆瓦', '海上', '大规模'
            ]

        if aero_keywords is None:
            aero_keywords = [
                'aerodynamic', 'aerodynamics', 'airfoil', 'wake', 'blade',
                'lift', 'drag', 'stall', 'vortex', 'turbulence', 'flow',
                '气动', '翼型', '尾流', '叶片', '升力', '阻力', '失速', '涡'
            ]

        # 加载元数据
        metadata_file = self.all_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        # 分类
        matched = []
        for p in papers:
            title = p.get('title', '').lower()
            abstract = (p.get('abstract') or '').lower()
            keywords = ' '.join(p.get('keywords', [])).lower()

            combined = f'{title} {abstract} {keywords}'

            has_scale = any(kw.lower() in combined for kw in scale_keywords)
            has_aero = any(kw.lower() in combined for kw in aero_keywords)

            if has_scale and has_aero:
                matched.append(p)

        # 创建分类目录
        cat_dir = self.categories_dir / category_name
        cat_dir.mkdir(parents=True, exist_ok=True)

        # 复制 PDF
        for p in matched:
            if p.get('pdf_path') and Path(p['pdf_path']).exists():
                dst = cat_dir / p['pdf_filename']
                if not dst.exists():
                    shutil.copy2(p['pdf_path'], dst)

        # 生成题录
        题录 = {
            "category": category_name,
            "total": len(matched),
            "updated_at": datetime.now().isoformat(),
            "papers": matched
        }

        with open(cat_dir / "题录.json", 'w', encoding='utf-8') as f:
            json.dump(题录, f, ensure_ascii=False, indent=2)

        self.logger.info(f"分类完成: {category_name} ({len(matched)} 篇)")
        self.status["classified"] = len(matched)

        return len(matched)

    def classify_papers_ai(
        self,
        progress_callback: callable = None,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """使用 AI 智能分类文献（基于 LITERATURE_CLASSIFY Agent）

        这是第5步的高级版本，使用 AI 模型根据标题、摘要和关键词进行智能分类。

        Args:
            progress_callback: 进度回调函数 callback(current, total, message)
            batch_size: 批处理大小（避免一次处理太多）

        Returns:
            分类统计信息
        """
        from ..core.factory import AgentFactoryRegistry
        from ..core.agents.types import AgentType
        from ..api.glm_client import GLMAPIClient

        # 1. 加载配置
        with open(_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        api_key = config.get('glm', {}).get('api_keys', [[]])[0]
        if not api_key:
            self.logger.error("未找到 GLM API 密钥，请在 config/api_keys.yaml 中配置")
            if progress_callback:
                progress_callback(0, 0, "错误：未配置 GLM API 密钥")
            return {"error": "未配置 GLM API 密钥"}

        # 2. 创建 AI 客户端
        api_client = GLMAPIClient(
            api_key=api_key,
            model="glm-4.7",
            timeout=60
        )

        # 3. 创建分类 Agent
        factory = AgentFactoryRegistry.create_factory(
            AgentType.LITERATURE_CLASSIFY,
            api_client=api_client,
            config={}
        )
        agent = factory.create_agent()

        # 4. 加载元数据
        metadata_file = self.all_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        # 5. 找出未分类的文献
        unclassified_papers = [p for p in papers if 'classification' not in p]
        total = len(unclassified_papers)

        if total == 0:
            self.logger.info("所有文献已分类，无需重复分类")
            if progress_callback:
                progress_callback(0, 0, "所有文献已分类")
            return {
                "total": len(papers),
                "classified": 0,
                "already_classified": len(papers),
                "domain_distribution": self._get_domain_distribution(papers)
            }

        self.logger.info(f"开始 AI 智能分类，共 {total} 篇文献待分类")
        if progress_callback:
            progress_callback(0, total, f"开始分类 {total} 篇文献...")

        # 6. 批量分类
        classified_count = 0
        failed_count = 0
        domain_counts = {}

        for i, paper in enumerate(unclassified_papers):
            try:
                # 调用 AI 分类
                result = asyncio.run(agent.execute({
                    "paper_id": paper.get('doi', f"paper_{i}"),
                    "paper_metadata": {
                        "title": paper.get("title", ""),
                        "abstract": paper.get("abstract", ""),
                        "keywords": paper.get("keywords", [])
                    }
                }))

                # 检查是否分类成功
                if result.get("confidence", 0) > 0.5:
                    # 更新 paper 的 classification 字段
                    paper['classification'] = {
                        "primary_domain": result.get("primary_domain"),
                        "primary_domain_cn": result.get("primary_domain_cn"),
                        "secondary_domains": result.get("secondary_domains", []),
                        "subdomains": result.get("subdomains", []),
                        "confidence": result.get("confidence", 0),
                        "reasoning": result.get("reasoning", ""),
                        "classified_at": datetime.now().strftime("%Y-%m-%d")
                    }

                    classified_count += 1

                    # 统计领域分布
                    domain = result.get("primary_domain_cn", "未分类")
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

                    self.logger.info(f"[{i+1}/{total}] {paper.get('title', 'N/A')[:50]}... → {domain} ({result.get('confidence', 0):.0%})")

                else:
                    failed_count += 1
                    self.logger.warning(f"[{i+1}/{total}] 分类置信度过低: {paper.get('title', 'N/A')[:50]}...")

                # 进度回调
                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(i + 1, total, f"已分类 {i + 1}/{total} 篇...")

                # 定期保存（每 batch_size 篇）
                if (i + 1) % batch_size == 0:
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(papers, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"已保存 {i + 1} 篇分类结果")

            except Exception as e:
                failed_count += 1
                self.logger.error(f"[{i+1}/{total}] 分类失败: {e}")

        # 7. 最终保存
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

        # 8. 创建分类目录结构
        self._create_category_directories(papers)

        # 9. 更新状态
        self.status["classified"] = sum(1 for p in papers if 'classification' in p)

        # 10. 统计信息
        stats = {
            "total": len(papers),
            "classified": classified_count,
            "failed": failed_count,
            "already_classified": len(papers) - total,
            "domain_distribution": self._get_domain_distribution(papers),
            "domain_counts": domain_counts
        }

        self.logger.info(f"AI 智能分类完成: {classified_count}/{total} 篇成功")
        if progress_callback:
            progress_callback(total, total, f"分类完成！{classified_count} 篇成功")

        return stats

    def classify_papers_ai_batch(
        self,
        domains: List[str],
        progress_callback: callable = None,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """使用 AI 批量智能分类文献（基于用户指定的领域）

        Args:
            domains: 用户指定的技术领域列表
            progress_callback: 进度回调函数 callback(current, total, message)
            batch_size: 单次处理的文献数量（推荐 20-50，默认 50）

        Returns:
            分类统计信息
        """
        self.logger.info(f"[DEBUG] classify_papers_ai_batch() 被调用，domains={domains}, batch_size={batch_size}")

        # 1. 加载配置
        self.logger.info("加载配置文件...")
        with open(_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.logger.info("配置文件加载成功")

        api_key = config.get('glm', {}).get('api_keys', [[]])[0]
        if not api_key:
            self.logger.error("未找到 GLM API 密钥")
            return {"error": "未配置 GLM API 密钥"}
        self.logger.info("API 密钥获取成功")

        # 2. 加载元数据
        self.logger.info("加载文献元数据...")
        metadata_file = self.all_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        self.logger.info(f"元数据加载成功，共 {len(papers)} 篇文献")

        # 3. 获取/创建 categories 目录
        categories_dir = self.project_dir / "pdfs" / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)

        # 4. 创建批量分类器
        self.logger.info("创建批量分类器...")
        classifier = BatchPaperClassifier(
            api_key=api_key,
            model="glm-4.7"
        )
        self.logger.info("批量分类器创建成功")

        # 5. 执行批量分类
        self.logger.info(f"准备调用分类器，领域: {domains}, 文献数: {len(papers)}")
        self.logger.info(f"开始 AI 批量分类，领域：{domains}，共 {len(papers)} 篇文献")
        if progress_callback:
            progress_callback(0, len(papers), f"准备批量分类...")

        try:
            stats = classifier.classify_papers_batch(
                papers=papers,
                domains=domains,
                categories_dir=categories_dir,
                metadata_file=metadata_file,
                progress_callback=progress_callback,
                batch_size=batch_size,
                relevance_threshold=0.7
            )

            # 7. 更新状态
            self.status["classified"] = sum(1 for p in papers if 'classification' in p)

            return stats

        except Exception as e:
            self.logger.error(f"AI 批量分类失败: {e}")
            return {"error": str(e)}

    def _get_domain_distribution(self, papers: List[Dict]) -> Dict[str, int]:
        """获取领域分布统计

        Args:
            papers: 文献列表

        Returns:
            领域分布字典
        """
        distribution = {}
        for paper in papers:
            if 'classification' in paper:
                domain = paper['classification'].get('primary_domain_cn', '未分类')
                distribution[domain] = distribution.get(domain, 0) + 1
        return distribution

    def _create_category_directories(self, papers: List[Dict]):
        """根据分类结果创建目录结构

        Args:
            papers: 文献列表
        """
        # 按 primary_domain 分组
        domain_papers = {}
        for paper in papers:
            if 'classification' in paper and paper.get('pdf_path'):
                domain = paper['classification'].get('primary_domain_cn', '未分类')
                if domain not in domain_papers:
                    domain_papers[domain] = []
                domain_papers[domain].append(paper)

        # 创建目录并复制 PDF
        for domain, papers_in_domain in domain_papers.items():
            # 创建目录（使用中文目录名）
            domain_dir = self.categories_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # 复制 PDF
            for paper in papers_in_domain:
                pdf_path = Path(paper['pdf_path'])
                if pdf_path.exists():
                    dst = domain_dir / paper['pdf_filename']
                    if not dst.exists():
                        shutil.copy2(pdf_path, dst)

            # 生成题录
            题录 = {
                "domain": domain,
                "total": len(papers_in_domain),
                "updated_at": datetime.now().isoformat(),
                "papers": papers_in_domain
            }

            with open(domain_dir / "题录.json", 'w', encoding='utf-8') as f:
                json.dump(题录, f, ensure_ascii=False, indent=2)

            self.logger.info(f"已创建分类目录: {domain} ({len(papers_in_domain)} 篇)")

    # ==================== Step 6: MinerU 转换 ====================

    def convert_to_markdown(
        self,
        category_name: str = None,
        progress_callback: callable = None
    ) -> int:
        """使用 MinerU 将 PDF 转换为 Markdown

        完整逻辑：
        1. 场景A（转换 all/）：只处理 pdfs/all/，输出到 markdown/all/
        2. 场景B（转换分类/）：检查 markdown/all/ 已有的，直接复制；只转换未有的

        Args:
            category_name: 分类名称（None 则转换 all/）
            progress_callback: 进度回调

        Returns:
            转换的文件数量
        """
        if not category_name:
            # ========== 场景A：转换 all/ 目录 ==========
            return self._convert_all_directory(progress_callback)
        else:
            # ========== 场景B：转换分类目录 ==========
            return self._convert_category_directory(category_name, progress_callback)

    def _convert_all_directory(self, progress_callback: callable = None) -> int:
        """转换 all/ 目录（场景A）

        逻辑：
        1. 读取 pdfs/all/metadata.json
        2. 读取 markdown/all/conversion_index.json
        3. 对比找出未转换的 PDF
        4. 转换 → markdown/all/
        5. 更新 markdown/all/conversion_index.json
        """
        self.logger.info("========== 开始转换 all/ 目录 ==========")

        source_dir = self.all_dir
        output_dir = self.markdown_dir / "all"
        index_file = output_dir / "conversion_index.json"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 步骤1: 获取 PDF 列表
        pdf_files = list(source_dir.glob("*.pdf"))
        self.logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")

        # 步骤2: 加载现有索引
        existing_index = self._load_conversion_index(index_file)
        self.logger.info(f"已加载索引: {len(existing_index)} 条记录")

        # 统计
        converted_new = 0  # 新转换的
        copied = 0         # 复制的（场景A不应该有）
        skipped = 0        # 跳过的

        # 步骤3: 遍历 PDF，判断是否需要转换
        for i, pdf_file in enumerate(pdf_files):
            pdf_name = pdf_file.name
            md_folder_name = pdf_file.stem

            # 检查是否已转换
            md_folder = output_dir / md_folder_name
            md_file = md_folder / "full.md"
            file_exists = md_file.exists()

            index_record = existing_index.get(pdf_name, {})
            is_converted_in_index = index_record.get('is_converted', False)

            # 判断逻辑
            if is_converted_in_index and file_exists:
                # 索引标记为已转换，且文件存在 -> 跳过
                skipped += 1
                if i % 10 == 0 or i == len(pdf_files) - 1:
                    self.logger.info(f"[{i+1}/{len(pdf_files)}] 已存在: {pdf_name}")

            elif not is_converted_in_index and file_exists:
                # 索引标记为未转换，但文件存在 -> 更新索引并跳过
                skipped += 1
                self.logger.info(f"[{i+1}/{len(pdf_files)}] 发现手动转换: {pdf_name}")
                existing_index[pdf_name] = {
                    "pdf_name": pdf_name,
                    "markdown_folder": md_folder_name,
                    "is_converted": True,
                    "converted_at": datetime.fromtimestamp(md_folder.stat().st_mtime).isoformat(),
                    "markdown_files": [str(f.name) for f in md_folder.iterdir() if f.is_file()]
                }

            else:
                # 需要转换
                self.logger.info(f"[{i+1}/{len(pdf_files)}] 开始转换: {pdf_name}")

                success = self._convert_pdf_with_mineru(pdf_file, output_dir, md_folder_name)

                if success:
                    converted_new += 1
                    existing_index[pdf_name] = {
                        "pdf_name": pdf_name,
                        "markdown_folder": md_folder_name,
                        "is_converted": True,
                        "converted_at": datetime.now().isoformat(),
                        "markdown_files": [str(f.name) for f in (output_dir / md_folder_name).iterdir() if f.is_file()]
                    }
                    self.logger.info(f"✅ 转换成功: {pdf_name}")
                else:
                    self.logger.error(f"❌ 转换失败: {pdf_name}")
                    existing_index[pdf_name] = {
                        "pdf_name": pdf_name,
                        "markdown_folder": md_folder_name,
                        "is_converted": False,
                        "error": "转换失败"
                    }

            if progress_callback:
                progress_callback(i + 1, len(pdf_files), pdf_name)

        # 步骤4: 保存索引
        self._save_conversion_index(
            index_file,
            existing_index,
            len(pdf_files),
            converted_new,
            skipped
        )

        self.logger.info(f"========== all/ 转换完成: 新转换 {converted_new} 篇，跳过 {skipped} 篇 ==========")

        return converted_new

    def _convert_category_directory(self, category_name: str, progress_callback: callable = None) -> int:
        """转换分类目录（场景B）

        逻辑：
        1. 读取 pdfs/categories/{分类}/metadata.json
        2. 读取 markdown/all/conversion_index.json（检查all里已有的）
        3. 读取 markdown/categories/{分类}/conversion_index.json
        4. 对比：
           - markdown/all/ 已存在 → 复制到分类目录
           - markdown/categories/{分类}/ 已存在 → 跳过
           - 都不存在 → 转换
        5. 新转换的文件同步到 markdown/all/
        6. 更新两个索引文件
        """
        self.logger.info(f"========== 开始转换分类目录: {category_name} ==========")

        source_dir = self.categories_dir / category_name
        output_dir = self.markdown_categories_dir / category_name
        category_index_file = output_dir / "conversion_index.json"

        all_output_dir = self.markdown_dir / "all"
        all_index_file = all_output_dir / "conversion_index.json"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 步骤1: 获取 PDF 列表
        pdf_files = list(source_dir.glob("*.pdf"))
        self.logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")

        # 步骤2: 加载两个索引
        all_index = self._load_conversion_index(all_index_file)
        category_index = self._load_conversion_index(category_index_file)

        self.logger.info(f"已加载 all/ 索引: {len(all_index)} 条记录")
        self.logger.info(f"已加载分类索引: {len(category_index)} 条记录")

        # 统计
        converted_new = 0  # 新转换的
        copied_from_all = 0  # 从 all/ 复制的
        skipped = 0        # 跳过的

        # 步骤3: 遍历 PDF，判断处理方式
        for i, pdf_file in enumerate(pdf_files):
            pdf_name = pdf_file.name
            md_folder_name = pdf_file.stem

            # 检查 all/ 是否已有
            all_md_folder = all_output_dir / md_folder_name
            all_md_exists = (all_md_folder / "full.md").exists()
            all_record = all_index.get(pdf_name, {})
            is_converted_in_all = all_record.get('is_converted', False)

            # 检查分类目录是否已有
            category_md_folder = output_dir / md_folder_name
            category_md_exists = (category_md_folder / "full.md").exists()
            category_record = category_index.get(pdf_name, {})
            is_converted_in_category = category_record.get('is_converted', False)

            # 判断处理方式
            if category_md_exists and is_converted_in_category:
                # 分类目录已存在 -> 跳过
                skipped += 1
                if i % 10 == 0 or i == len(pdf_files) - 1:
                    self.logger.info(f"[{i+1}/{len(pdf_files)}] 已存在（分类）: {pdf_name}")

            elif all_md_exists and is_converted_in_all:
                # all/ 已存在，但分类目录没有 -> 复制
                self.logger.info(f"[{i+1}/{len(pdf_files)}] 从 all/ 复制: {pdf_name}")

                # 复制整个文件夹
                if category_md_folder.exists():
                    shutil.rmtree(category_md_folder)
                shutil.copytree(all_md_folder, category_md_folder)

                # 更新分类索引
                category_index[pdf_name] = {
                    "pdf_name": pdf_name,
                    "markdown_folder": md_folder_name,
                    "is_converted": True,
                    "converted_at": datetime.fromtimestamp(all_md_folder.stat().st_mtime).isoformat(),
                    "markdown_files": [str(f.name) for f in category_md_folder.iterdir() if f.is_file()],
                    "source": "copied_from_all"
                }

                copied_from_all += 1
                self.logger.info(f"✅ 复制成功: {pdf_name}")

            else:
                # 都不存在 -> 转换
                self.logger.info(f"[{i+1}/{len(pdf_files)}] 开始转换: {pdf_name}")

                success = self._convert_pdf_with_mineru(pdf_file, output_dir, md_folder_name)

                if success:
                    converted_new += 1
                    timestamp = datetime.now().isoformat()

                    # 更新分类索引
                    category_index[pdf_name] = {
                        "pdf_name": pdf_name,
                        "markdown_folder": md_folder_name,
                        "is_converted": True,
                        "converted_at": timestamp,
                        "markdown_files": [str(f.name) for f in category_md_folder.iterdir() if f.is_file()],
                        "source": "newly_converted"
                    }

                    # 同步到 all/（如果 all/ 里没有）
                    if not all_md_exists:
                        self.logger.info(f"  → 同步到 all/: {pdf_name}")
                        shutil.copytree(category_md_folder, all_md_folder, dirs_exist_ok=True)

                        # 更新 all/ 索引
                        all_index[pdf_name] = {
                            "pdf_name": pdf_name,
                            "markdown_folder": md_folder_name,
                            "is_converted": True,
                            "converted_at": timestamp,
                            "markdown_files": [str(f.name) for f in all_md_folder.iterdir() if f.is_file()],
                            "source": "synced_from_category"
                        }

                    self.logger.info(f"✅ 转换成功: {pdf_name}")
                else:
                    self.logger.error(f"❌ 转换失败: {pdf_name}")
                    category_index[pdf_name] = {
                        "pdf_name": pdf_name,
                        "markdown_folder": md_folder_name,
                        "is_converted": False,
                        "error": "转换失败"
                    }

            if progress_callback:
                progress_callback(i + 1, len(pdf_files), pdf_name)

        # 步骤4: 保存两个索引
        self._save_conversion_index(
            category_index_file,
            category_index,
            len(pdf_files),
            converted_new,
            skipped + copied_from_all
        )

        # 同时更新 all/ 索引（如果有新增）
        if converted_new > 0:
            self._save_conversion_index(
                all_index_file,
                all_index,
                len(list(all_output_dir.parent.parent / "pdfs" / "all").glob("*.pdf")) if (all_output_dir.parent.parent / "pdfs" / "all").exists() else 0,
                0,  # all/ 的新增不计数
                0
            )

        self.logger.info(f"========== 分类转换完成: 新转换 {converted_new} 篇，从 all/ 复制 {copied_from_all} 篇，跳过 {skipped} 篇 ==========")

        return converted_new

    def _load_conversion_index(self, index_file: Path) -> dict:
        """加载转换索引文件

        Args:
            index_file: 索引文件路径

        Returns:
            dict: {pdf_name: record, ...}
        """
        if not index_file.exists():
            return {}

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 兼容多种格式
            if 'files' in data:
                # 新格式 - 可能是数组或字典
                files_data = data['files']
                if isinstance(files_data, dict):
                    # 格式1: {"files": {"pdf_name": {...}, ...}}
                    return files_data
                elif isinstance(files_data, list):
                    # 格式2: {"files": [{...}, {...}]}
                    return {item['pdf_name']: item for item in files_data}
                else:
                    return {}
            elif 'converted' in data:
                # 旧格式 - 需要扫描目录确认
                index = {}
                output_dir = index_file.parent
                for md_dir in output_dir.iterdir():
                    if not md_dir.is_dir():
                        continue
                    full_md = md_dir / 'full.md'
                    if full_md.exists():
                        pdf_name = md_dir.name + '.pdf'
                        index[pdf_name] = {
                            'pdf_name': pdf_name,
                            'markdown_folder': md_dir.name,
                            'is_converted': True,
                            'converted_at': datetime.fromtimestamp(full_md.stat().st_mtime).isoformat(),
                            'markdown_files': [str(f.name) for f in md_dir.iterdir() if f.is_file()]
                        }
                return index
            else:
                return {}

        except Exception as e:
            self.logger.warning(f"加载索引失败 {index_file.name}: {e}")
            return {}

    def _save_conversion_index(
        self,
        index_file: Path,
        index_data: dict,
        total_pdfs: int,
        converted_new: int,
        skipped: int
    ):
        """保存转换索引文件

        Args:
            index_file: 索引文件路径
            index_data: 索引数据 {pdf_name: record, ...}
            total_pdfs: 总 PDF 数量
            converted_new: 新转换的数量
            skipped: 跳过的数量
        """
        converted_count = len([f for f in index_data.values() if f.get('is_converted', False)])

        data = {
            "last_updated": datetime.now().isoformat(),
            "total_pdfs": total_pdfs,
            "converted": converted_count,
            "converted_new": converted_new,
            "skipped": skipped,
            "unconverted": total_pdfs - converted_count,
            "files": list(index_data.values())
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"索引已保存: {index_file.name} ({converted_count}/{total_pdfs} 已转换)")

    def _convert_pdf_with_mineru(self, pdf_file: Path, output_dir: Path, md_folder_name: str) -> bool:
        """使用 MinerU API 转换单个 PDF

        Args:
            pdf_file: PDF 文件路径
            output_dir: 输出目录
            md_folder_name: Markdown 文件夹名称（PDF 文件不含扩展名）

        Returns:
            是否转换成功
        """
        self.logger.info(f"使用 MinerU 转换: {pdf_file.name}")

        try:
            # 创建客户端并解析
            client = MinerUClient()

            # 批量解析（单个文件也使用批量接口）
            results = client.parse_files_batch(
                [pdf_file],
                model_version=ModelVersion.VLM,
                progress_callback=lambda cur, total, name: self.logger.info(f"{name}")
            )

            if not results:
                self.logger.error(f"转换失败: {pdf_file.name} - 无返回结果")
                return False

            result = results.get(pdf_file.name)
            if not result:
                self.logger.error(f"转换失败: {pdf_file.name} - 未找到结果")
                return False

            if result.state.value == "failed":
                self.logger.error(f"转换失败: {pdf_file.name} - {result.error_message}")
                return False

            if result.state.value != "done":
                self.logger.error(f"转换失败: {pdf_file.name} - 状态: {result.state.value}")
                return False

            # 下载并解压结果
            expected_dir = output_dir / md_folder_name
            full_md = client.download_and_extract(
                result.zip_url,
                expected_dir,
                "full.md"
            )

            if full_md and full_md.exists():
                file_size = full_md.stat().st_size
                self.logger.info(f"转换成功: {pdf_file.name} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"转换失败: {pdf_file.name} - full.md not found")
                return False

        except Exception as e:
            self.logger.error(f"转换异常: {pdf_file.name} - {e}")
            return False

    # ==================== 状态和报告 ====================

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self.status.copy()

    def generate_report(self) -> Dict[str, Any]:
        """生成工作报告"""
        # 加载元数据
        metadata_file = self.all_dir / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)

            total = len(papers)
            downloaded = sum(1 for p in papers if p.get('pdf_downloaded'))
        else:
            total = 0
            downloaded = 0

        report = {
            "project_dir": str(self.project_dir),
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_papers": total,
                "pdf_downloaded": downloaded,
                "download_rate": f"{downloaded/total*100:.1f}%" if total > 0 else "0%",
                **self.status
            },
            "directories": {
                "all": str(self.all_dir),
                "temp": str(self.temp_dir),
                "categories": str(self.categories_dir),
                "markdown": str(self.markdown_dir),
                "exports": str(self.exports_dir)
            }
        }

        return report
