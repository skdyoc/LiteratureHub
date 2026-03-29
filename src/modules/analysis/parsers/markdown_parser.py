"""
Markdown 解析器模块
Markdown Parser Module

从 full.md 文件中提取文献的结构化信息和内容
Extract structured information and content from full.md files
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.core.paper import Paper, PaperMetadata, PaperContent
from src.utils.logger import get_logger

logger = get_logger("markdown_parser")


class MarkdownParser:
    """Markdown 文献解析器"""

    def __init__(self, config: Dict = None):
        """
        初始化解析器

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 预编译正则表达式以提高性能
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译常用正则表达式"""
        self._title_pattern = re.compile(r'^#\s+(.+)$', re.MULTILINE)
        self._authors_pattern = re.compile(
            r'^([A-Z]\.\s*[A-Za-z]+(?:\s*[*,]\s*[A-Z]\.\s*[A-Za-z]+)*)',
            re.MULTILINE
        )
        self._year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        self._doi_pattern = re.compile(
            r'(?:DOI|doi):\s*(10\.\d{4,}/[^\s]+)',
            re.IGNORECASE
        )
        self._abstract_pattern = re.compile(
            r'#\s*a\s*b\s*s\s*t\s*r\s*a\s*c\s*t\s*\n+(.+?)(?=\n#|\Z)',
            re.IGNORECASE | re.DOTALL
        )
        self._keywords_pattern = re.compile(
            r'Keywords:\s*\n+((?:[^\n]+\n)+)',
            re.IGNORECASE
        )
        self._section_pattern = re.compile(
            r'^#\s+(\d+)\.\s*(.+?)$',
            re.MULTILINE
        )
        self._references_pattern = re.compile(
            r'#\s*R\s*e\s*f\s*e\s*r\s*e\s*n\s*c\s*e\s*s\s*\n+(.+)',
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
            content = f.read()

        # 解析各个部分
        metadata = self._parse_metadata(content, folder)
        paper_content = self._parse_content(content)

        # 创建 Paper 对象
        paper = Paper(
            folder_name=folder.name,
            metadata=metadata,
            content=paper_content
        )

        return paper

    def _parse_metadata(self, content: str, folder: Path) -> PaperMetadata:
        """
        解析元数据

        Args:
            content: Markdown 内容
            folder: 文件夹路径

        Returns:
            PaperMetadata 对象
        """
        # 提取标题
        title = self.extract_title(content)

        # 提取作者
        authors = self._extract_authors(content)

        # 提取年份（优先从文件夹名称提取）
        year = self._extract_year(content, folder)

        # 提取期刊信息
        journal = self._extract_journal(content)

        # 提取 DOI
        doi = self._extract_doi(content)

        # 提取卷号、期号、页码
        volume, issue, pages = self._extract_pub_info(content)

        # 创建元数据对象
        metadata = PaperMetadata(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi
        )

        logger.debug(f"解析元数据: {title[:50]}... ({year})")
        return metadata

    def _extract_authors(self, content: str) -> List[str]:
        """提取作者列表"""
        # 查找作者行（在标题后）
        lines = content.split('\n')
        authors = []

        # 跳过标题行，查找作者行
        for i, line in enumerate(lines[1:20]):  # 只检查前20行
            line = line.strip()
            # 匹配作者格式：首字母. 姓氏, 首字母. 姓氏
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

        # 2. 从内容中查找年份（Article history 部分）
        history_match = re.search(
            r'Article history:.*?Received\s+(\d{1,2})\s+\w+\s+(19|20\d{2})',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if history_match:
            return int(history_match.group(2))

        # 3. 查找所有年份，选择最合理的（最近50年）
        years = self._year_pattern.findall(content)
        if years:
            # 选择最大的年份（最接近当前）
            current_year = datetime.now().year
            valid_years = [int(y) for y in years if 1970 <= int(y) <= current_year]
            if valid_years:
                return max(valid_years)

        # 4. 默认返回当前年份
        logger.warning(f"无法提取年份: {folder.name}")
        return datetime.now().year

    def _extract_journal(self, content: str) -> str:
        """提取期刊名称"""
        # 查找期刊信息（通常在文章开头或 DOI 中）
        journal_patterns = [
            r'Available online\s+\w+\s+\d{4}\s+(.+?)\n',
            (r'journal\s+of\s+\w+', ''),  # 不需要捕获组
            (r'ternational\s+Journal\s+of', ''),  # 不需要捕获组
        ]

        for pattern in journal_patterns:
            if isinstance(pattern, tuple):
                pattern, _ = pattern
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(0).strip()
            else:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return ""

    def _extract_doi(self, content: str) -> str:
        """提取 DOI"""
        match = self._doi_pattern.search(content)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_pub_info(self, content: str) -> tuple:
        """提取卷号、期号、页码"""
        volume = ""
        issue = ""
        pages = ""

        # 查找卷号和期号
        volume_match = re.search(r'Volume\s+(\d+)', content, re.IGNORECASE)
        if volume_match:
            volume = volume_match.group(1)

        issue_match = re.search(r'Issue\s+(\d+)', content, re.IGNORECASE)
        if issue_match:
            issue = issue_match.group(1)

        # 查找页码
        pages_match = re.search(r'Pages\s+(\d+-\d+)', content, re.IGNORECASE)
        if pages_match:
            pages = pages_match.group(1)

        return volume, issue, pages

    def _parse_content(self, content: str) -> PaperContent:
        """
        解析正文内容

        Args:
            content: Markdown 内容

        Returns:
            PaperContent 对象
        """
        # 提取摘要
        abstract = self.extract_abstract(content)

        # 提取关键词
        keywords = self.extract_keywords(content)

        # 提取所有章节
        sections = self.extract_sections(content)

        # 提取引言（通常是 # 1. Introduction）
        introduction = self._extract_introduction(content, sections)

        # 提取结论
        conclusion = self._extract_conclusion(content, sections)

        # 提取参考文献
        references = self.extract_references(content)

        # 创建内容对象
        paper_content = PaperContent(
            abstract=abstract,
            keywords=keywords,
            introduction=introduction,
            sections=sections,
            conclusion=conclusion,
            references=references
        )

        logger.debug(f"解析内容: {len(sections)} 个章节, {len(keywords)} 个关键词")
        return paper_content

    def _extract_introduction(self, content: str, sections: Dict[str, str]) -> str:
        """提取引言部分"""
        # 1. 查找 "Introduction" 章节
        intro_keywords = ['introduction', 'intro']

        for section_title in sections.keys():
            lower_title = section_title.lower()
            for keyword in intro_keywords:
                if keyword in lower_title:
                    return sections[section_title]

        # 2. 如果没有找到，查找文档开头的引言段落
        intro_pattern = re.compile(
            r'#\s*1\.\s*.*Introduction.*?\n+(.+?)(?=\n#)',
            re.IGNORECASE | re.DOTALL
        )
        match = intro_pattern.search(content)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_conclusion(self, content: str, sections: Dict[str, str]) -> str:
        """提取结论部分"""
        # 1. 查找 "Conclusion" 章节
        conclusion_keywords = ['conclusion', 'conclusions', 'summary', 'discussion']

        for section_title in sections.keys():
            lower_title = section_title.lower()
            for keyword in conclusion_keywords:
                if keyword in lower_title:
                    return sections[section_title]

        # 2. 如果没有找到，查找文档末尾的结论段落
        conclusion_pattern = re.compile(
            r'#\s*\d+\.\s*.*(?:Conclusion|Summary).*?\n+(.+?)(?=\n#|$)',
            re.IGNORECASE | re.DOTALL
        )
        match = conclusion_pattern.search(content)
        if match:
            return match.group(1).strip()

        return ""

    def extract_title(self, content: str) -> str:
        """提取标题"""
        # 第一个 # 标题通常是文献标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def extract_abstract(self, content: str) -> str:
        """提取摘要"""
        # 优先查找 # a b s t r a c t 格式（MinerU 生成）
        match = self._abstract_pattern.search(content)
        if match:
            abstract = match.group(1).strip()
            # 清理摘要文本
            # 移除 Keywords: 行及其之后的内容
            abstract = re.sub(r'\nKeywords:.*', '', abstract, flags=re.DOTALL)
            # 移除多余的空行
            abstract = re.sub(r'\n\s*\n', '\n\n', abstract)
            return abstract.strip()

        # 备用：查找 Abstract: 或 ## Abstract 部分
        fallback_patterns = [
            r'Abstract:\s*(.+?)(?=\nKeywords:|\n#|\n\n\n)',
            r'##\s*Abstract\s*\n+(.+?)(?=\n##|\n\n\n)',
        ]
        for pattern in fallback_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 查找 Keywords: 部分（MinerU 格式：每行一个关键词）
        match = self._keywords_pattern.search(content)
        if match:
            keywords_text = match.group(1).strip()
            # 分割成行，每个关键词一行
            keywords = [line.strip() for line in keywords_text.split('\n')]
            # 过滤空行和 "Keywords:" 标题本身
            keywords = [k for k in keywords if k and k.lower() != 'keywords:']
            return keywords

        # 备用：查找单行关键词格式（逗号分隔）
        fallback_match = re.search(
            r'Keywords:\s*(.+?)(?=\n#|\n\n)',
            content,
            re.IGNORECASE
        )
        if fallback_match:
            keywords_str = fallback_match.group(1).strip()
            # 分割关键词（可能用逗号、分号或句号分隔）
            keywords = re.split(r'[,;．.、]', keywords_str)
            return [k.strip() for k in keywords if k.strip()]

        return []

    def extract_sections(self, content: str) -> Dict[str, str]:
        """
        提取各个章节

        Args:
            content: Markdown 内容

        Returns:
            章节标题 -> 内容的字典
        """
        sections = {}

        # 查找所有章节标题（# 1. 标题 或 ## 1. 标题）
        section_matches = list(self._section_pattern.finditer(content))

        if not section_matches:
            return sections

        # 提取每个章节的内容
        for i, match in enumerate(section_matches):
            section_num = match.group(1)
            section_title = match.group(2).strip()
            full_title = f"{section_num}. {section_title}"

            # 计算章节内容的起始和结束位置
            start_pos = match.end()

            # 下一个章节的开始位置，或文档结尾
            if i + 1 < len(section_matches):
                end_pos = section_matches[i + 1].start()
            else:
                # 查找 References 部分
                ref_match = self._references_pattern.search(content)
                if ref_match and ref_match.start() > start_pos:
                    end_pos = ref_match.start()
                else:
                    end_pos = len(content)

            # 提取章节内容
            section_content = content[start_pos:end_pos].strip()

            # 清理内容（移除多余的空行）
            section_content = re.sub(r'\n\s*\n', '\n\n', section_content)

            sections[full_title] = section_content

        logger.debug(f"提取了 {len(sections)} 个章节")
        return sections

    def extract_references(self, content: str) -> List[str]:
        """
        提取参考文献列表

        Args:
            content: Markdown 内容

        Returns:
            参考文献列表
        """
        # 查找 # R e f e r e n c e s 部分
        match = self._references_pattern.search(content)
        if not match:
            return []

        references_text = match.group(1).strip()

        # 分割参考文献（通常用数字编号 [1], [2] 或 1., 2.）
        # 移除空行
        references_text = re.sub(r'\n\s*\n', '\n', references_text)

        # 尝试多种分割模式
        references = []

        # 模式1：数字编号 [1], [2]
        if '[1]' in references_text or '[1]' in references_text:
            references = re.split(r'\n\[\d+\]', references_text)
            references[0] = re.sub(r'^\[\d+\]', '', references[0])  # 移除第一个 [1]

        # 模式2：数字编号 1., 2.
        elif re.match(r'^1\.', references_text):
            references = re.split(r'\n\d+\.', references_text)
            references[0] = re.sub(r'^\d+\.', '', references[0])  # 移除第一个 1.

        # 模式3：直接按行分割
        else:
            references = references_text.split('\n')

        # 清理每个参考文献
        cleaned_references = []
        for ref in references:
            ref = ref.strip()
            # 移除图片引用（如 ![](images/...)）
            ref = re.sub(r'!\[.*?\]\(images/.*?\)', '', ref)
            # 移除多余的空格
            ref = re.sub(r'\s+', ' ', ref)
            if ref and len(ref) > 10:  # 至少10个字符才认为是有效参考文献
                cleaned_references.append(ref)

        logger.debug(f"提取了 {len(cleaned_references)} 条参考文献")
        return cleaned_references

    def batch_parse(
        self,
        root_folder: str,
        max_papers: Optional[int] = None,
        show_progress: bool = True
    ) -> List[Paper]:
        """
        批量解析文献文件夹

        Args:
            root_folder: 包含所有文献文件夹的根目录
            max_papers: 最大解析数量（用于测试，None 表示全部）
            show_progress: 是否显示进度

        Returns:
            Paper 对象列表
        """
        from pathlib import Path
        import sys

        root_path = Path(root_folder)
        if not root_path.exists():
            raise FileNotFoundError(f"根目录不存在: {root_folder}")

        papers = []
        failed_papers = []

        # 遍历所有子文件夹
        folders = [f for f in root_path.iterdir() if f.is_dir()]
        total_folders = len(folders)

        if max_papers:
            folders = folders[:max_papers]

        logger.info(f"开始批量解析: {len(folders)} 个文献文件夹")

        for i, folder in enumerate(folders):
            try:
                # 显示进度
                if show_progress:
                    progress = (i + 1) / total_folders * 100
                    sys.stdout.write(
                        f"\r解析进度: {i+1}/{total_folders} ({progress:.1f}%) - "
                        f"当前: {folder.name[:40]}...     "
                    )
                    sys.stdout.flush()

                # 解析单个文献
                paper = self.parse(str(folder))
                papers.append(paper)

            except Exception as e:
                logger.error(f"解析失败: {folder.name}, 错误: {e}")
                failed_papers.append((folder.name, str(e)))

        # 清除进度行
        if show_progress:
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

        # 打印统计信息
        logger.info(f"批量解析完成: {len(papers)} 成功, {len(failed_papers)} 失败")

        if failed_papers:
            logger.warning(f"失败的文献 ({len(failed_papers)}):")
            for name, error in failed_papers[:5]:  # 只显示前5个
                logger.warning(f"  - {name}: {error[:50]}...")
            if len(failed_papers) > 5:
                logger.warning(f"  ... 还有 {len(failed_papers) - 5} 个失败")

        return papers


if __name__ == "__main__":
    # 测试代码
    print("Markdown 解析器模块已加载")
