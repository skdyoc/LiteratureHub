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
下载管理器

实现三步文献下载流程：
1. SciHub 自动下载（VPN 代理）
2. NoteExpress 辅助下载
3. Web of Science 手动下载
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from .scihub_downloader import SciHubDownloader, DownloadResult
from .vpn_detector import VPNDetector


@dataclass
class PaperInfo:
    """文献信息"""
    doi: str
    title: str
    authors: List[str]
    year: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None
    pdf_path: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class DownloadManager:
    """下载管理器

    实现三步文献下载流程。

    用法：
    ```python
    manager = DownloadManager(
        pdf_dir="pdfs",
        proxy_url="http://127.0.0.1:7890"
    )

    # 执行三步下载流程
    results = manager.execute_three_step_download(papers)

    # 导出 NoteExpress 格式
    manager.export_noteexpress(remaining_papers, "exports/failed.txt")
    ```
    """

    def __init__(
        self,
        pdf_dir: str = "pdfs",
        proxy_url: str = None,
        config: Dict[str, Any] = None
    ):
        """初始化下载管理器

        Args:
            pdf_dir: PDF 根目录
            proxy_url: 代理 URL
            config: 配置字典
        """
        self.pdf_dir = Path(pdf_dir)
        self.config = config or {}

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 创建目录结构
        self._setup_directories()

        # 初始化 SciHub 下载器
        self.scihub = SciHubDownloader(
            proxy_url=proxy_url,
            output_dir=str(self.pdf_dir / "all")
        )

        # 下载状态
        self.status = {
            "step1_success": [],
            "step1_failed": [],
            "step2_success": [],
            "step2_failed": [],
            "step3_failed": []
        }

    def _setup_directories(self):
        """设置目录结构

        目录结构：
        pdfs/
        ├── all/           # 所有成功下载的 PDF
        ├── temp/          # 待处理的临时文件
        └── categories/    # 分类后的 PDF
        """
        (self.pdf_dir / "all").mkdir(parents=True, exist_ok=True)
        (self.pdf_dir / "temp").mkdir(parents=True, exist_ok=True)
        (self.pdf_dir / "categories").mkdir(parents=True, exist_ok=True)

        self.logger.info(f"目录结构已创建: {self.pdf_dir}")

    def run_download_workflow(
        self,
        papers: List[PaperInfo],
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        执行三步下载流程

        Args:
            papers: 文献信息列表
            progress_callback: 进度回调

        Returns:
            下载结果统计
        """
        self.logger.info(f"开始三步下载流程: {len(papers)} 篇文献")

        # 重置状态
        self.status = {
            "step1_success": [],
            "step1_failed": [],
            "step2_success": [],
            "step2_failed": [],
            "step3_failed": []
        }

        # ===== 第一步：SciHub 自动下载 =====
        self.logger.info("=== 第一步：SciHub 自动下载 ===")

        remaining = self._execute_step1(papers, progress_callback)

        # ===== 第二步：NoteExpress 辅助下载 =====
        self.logger.info("=== 第二步：NoteExpress 辅助下载 ===")

        if remaining:
            self._prepare_step2(remaining)

        # ===== 第三步：Web of Science 手动下载 =====
        self.logger.info("=== 第三步：Web of Science 手动下载 ===")

        if self.status["step2_failed"]:
            self._prepare_step3(self.status["step2_failed"])

        # 返回结果
        results = {
            "total": len(papers),
            "step1_success": len(self.status["step1_success"]),
            "step1_failed": len(self.status["step1_failed"]),
            "step2_success": len(self.status["step2_success"]),
            "final_failed": len(self.status["step3_failed"]),
            "details": self.status
        }

        self.logger.info(
            f"下载流程完成: 第一步 {results['step1_success']}/{len(papers)} 成功, "
            f"剩余 {results['final_failed']} 篇需要手动下载"
        )

        return results

    def _execute_step1(
        self,
        papers: List[PaperInfo],
        progress_callback: callable = None
    ) -> List[PaperInfo]:
        """执行第一步：SciHub 自动下载"""

        def step1_progress(current, total, result):
            if progress_callback:
                progress_callback("step1", current, total, result)

        # 提取 DOI 列表
        doi_list = [p.doi for p in papers if p.doi]

        # 批量下载
        results = self.scihub.download_batch(
            doi_list,
            output_dir=str(self.pdf_dir / "all"),
            delay=self.config.get("download_delay", 2.0),
            progress_callback=step1_progress
        )

        # 整理结果
        remaining = []

        for paper, result in zip(papers, results):
            if result.success:
                paper.pdf_path = result.pdf_path
                self.status["step1_success"].append(paper)
            else:
                self.status["step1_failed"].append(paper)
                remaining.append(paper)

        return remaining

    def _prepare_step2(self, remaining_papers: List[PaperInfo]):
        """准备第二步：生成 NoteExpress 导入文件"""

        output_path = self.pdf_dir / "temp" / "noteexpress_import.txt"

        self.export_noteexpress(remaining_papers, str(output_path))

        self.logger.info(
            f"第二步准备完成: 已生成 NoteExpress 导入文件 ({len(remaining_papers)} 篇)\n"
            f"文件位置: {output_path}\n"
            f"请按以下步骤操作：\n"
            f"1. 打开 NoteExpress\n"
            f"2. 导入 {output_path}\n"
            f"3. 使用 NoteExpress 下载 PDF\n"
            f"4. 将下载的 PDF 放入 {self.pdf_dir / 'temp'}\n"
            f"5. 运行 manager.process_temp_pdfs() 处理临时文件"
        )

    def _prepare_step3(self, remaining_papers: List[PaperInfo]):
        """准备第三步：生成手动下载清单"""

        output_path = self.pdf_dir / "temp" / "manual_download_list.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== 需要手动下载的文献 ===\n\n")

            for i, paper in enumerate(remaining_papers, 1):
                f.write(f"[{i}] {paper.title}\n")
                f.write(f"    DOI: {paper.doi}\n")
                f.write(f"    作者: {', '.join(paper.authors[:3])}\n")
                if paper.year:
                    f.write(f"    年份: {paper.year}\n")
                if paper.journal:
                    f.write(f"    期刊: {paper.journal}\n")
                f.write("\n")

        self.status["step3_failed"] = remaining_papers

        self.logger.info(
            f"第三步准备完成: 已生成手动下载清单 ({len(remaining_papers)} 篇)\n"
            f"文件位置: {output_path}"
        )

    def export_noteexpress(
        self,
        papers: List[PaperInfo],
        output_path: str
    ) -> int:
        """
        导出 NoteExpress 格式文件

        Args:
            papers: 文献列表
            output_path: 输出路径

        Returns:
            导出的文献数量
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        count = 0

        with open(output_file, 'w', encoding='utf-8') as f:
            for paper in papers:
                # 写入 NoteExpress 格式
                f.write("{Reference Type}: Generic\n")
                f.write(f"{{Author}}: {'; '.join(paper.authors)}\n")
                f.write(f"{{Title}}: {paper.title}\n")

                if paper.year:
                    f.write(f"{{Date}}: {paper.year}\n")

                if paper.keywords:
                    f.write(f"{{Keywords}}: {'; '.join(paper.keywords)}\n")

                if paper.abstract:
                    # 清理摘要中的换行
                    abstract = paper.abstract.replace('\n', ' ').strip()
                    f.write(f"{{Abstract}}: {abstract}\n")

                if paper.doi:
                    f.write(f"{{DOI}}: {paper.doi}\n")

                if paper.journal:
                    f.write(f"{{Journal}}: {paper.journal}\n")

                f.write("\n\n")
                count += 1

        self.logger.info(f"NoteExpress 格式导出完成: {count} 篇 -> {output_file}")

        return count

    def process_temp_pdfs(self) -> int:
        """
        处理临时目录中的 PDF 文件

        根据文件名匹配 DOI，重命名并移动到 all 目录。

        Returns:
            处理的文件数量
        """
        temp_dir = self.pdf_dir / "temp"
        all_dir = self.pdf_dir / "all"

        if not temp_dir.exists():
            return 0

        processed = 0

        for pdf_file in temp_dir.glob("*.pdf"):
            try:
                # 尝试从文件名提取 DOI
                doi = self._extract_doi_from_filename(pdf_file.name)

                if doi:
                    # 重命名并移动
                    safe_doi = doi.replace("/", "_").replace("\\", "_")
                    new_name = f"{safe_doi}.pdf"
                    new_path = all_dir / new_name

                    pdf_file.rename(new_path)
                    self.logger.info(f"处理完成: {pdf_file.name} -> {new_path}")
                    processed += 1

            except Exception as e:
                self.logger.warning(f"处理失败 {pdf_file}: {e}")

        return processed

    def _extract_doi_from_filename(self, filename: str) -> Optional[str]:
        """从文件名提取 DOI"""
        # 去除 .pdf 后缀
        name = filename.replace(".pdf", "")

        # 常见的 DOI 格式：10.xxxx/xxxxx
        import re
        doi_pattern = r'10\.\d{4,}/[^\s]+'

        match = re.search(doi_pattern, name)
        if match:
            return match.group(0)

        # 如果文件名就是 DOI（用 _ 代替 /）
        if name.startswith("10."):
            return name.replace("_", "/")

        return None

    def get_download_status(self) -> Dict[str, Any]:
        """获取下载状态"""
        return self.status.copy()

    def save_status(self, output_path: str):
        """保存下载状态到文件"""
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": self.status,
            "scihub_stats": self.scihub.get_stats()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"状态已保存: {output_path}")
