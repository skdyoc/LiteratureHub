"""
数据库操作模块
Database Operations Module

处理文献数据的存储、查询、更新等操作
Handle storage, query, and update operations of paper data
"""

import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
from contextlib import contextmanager

from .paper import Paper


class LiteratureDatabase:
    """文献数据库管理类"""

    def __init__(self, db_path: str):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 返回字典格式

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def initialize_tables(self):
        """
        初始化数据库表结构

        创建以下表：
        1. papers - 论文基础信息表
        2. innovations - 创新点分类表
        3. motivations - 研究动机表
        4. roadmaps - 技术路线表
        5. impacts - 影响评估表
        6. mechanisms - 机理解析表
        7. references - 参考文献表
        8. citations - 引用关系表
        """
        with self.get_cursor() as cursor:
            # 1. 论文基础信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    journal TEXT NOT NULL,
                    volume TEXT,
                    issue TEXT,
                    pages TEXT,
                    doi TEXT,
                    published_date TEXT,
                    received_date TEXT,
                    accepted_date TEXT,

                    -- 论文内容
                    abstract TEXT,
                    keywords TEXT,
                    introduction TEXT,
                    sections TEXT,
                    conclusion TEXT,
                    acknowledgments TEXT,

                    -- 分析状态
                    analysis_completed BOOLEAN DEFAULT 0,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- 全文搜索字段
                    full_text TEXT,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 为 papers 表创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_analysis ON papers(analysis_completed)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, abstract, full_text, content='papers', content_rowid='id')")

            # 2. 创新点分类表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS innovations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    innovation_type TEXT NOT NULL,

                    -- 创新点分类
                    new_phenomena TEXT,
                    new_methods TEXT,
                    new_objects TEXT,

                    -- 创新点摘要
                    summary TEXT,

                    -- 置信度
                    confidence_phenomena REAL DEFAULT 0.0,
                    confidence_methods REAL DEFAULT 0.0,
                    confidence_objects REAL DEFAULT 0.0,
                    confidence_overall REAL DEFAULT 0.0,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_innovations_paper ON innovations(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_innovations_type ON innovations(innovation_type)")

            # 3. 研究动机表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS motivations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL UNIQUE,

                    -- 研究动机要素
                    problem_statement TEXT,
                    research_objective TEXT,
                    research_gap TEXT,
                    industry_pain_point TEXT,

                    -- 动机强度
                    motivation_strength REAL DEFAULT 0.0,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_motivations_paper ON motivations(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_motivations_strength ON motivations(motivation_strength)")

            # 4. 技术路线表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS roadmaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL UNIQUE,

                    -- 技术路线要素
                    methodology TEXT,
                    tools TEXT,
                    algorithms TEXT,
                    validation_method TEXT,

                    -- 技术路线类型
                    roadmap_type TEXT,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmaps_paper ON roadmaps(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmaps_type ON roadmaps(roadmap_type)")

            # 5. 影响评估表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL UNIQUE,

                    -- 影响因子
                    time_weight REAL DEFAULT 0.0,
                    impact_factor REAL DEFAULT 0.0,
                    journal_tier TEXT,

                    -- 引用信息
                    citation_count INTEGER DEFAULT 0,

                    -- 综合评分
                    overall_score REAL DEFAULT 0.0,

                    -- 技术成熟度
                    maturity_level TEXT,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impacts_paper ON impacts(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impacts_score ON impacts(overall_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_impacts_tier ON impacts(journal_tier)")

            # 6. 机理解析表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mechanisms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL UNIQUE,

                    -- 机理解析要素
                    physical_mechanism TEXT,
                    theoretical_basis TEXT,
                    key_principles TEXT,

                    -- 解释质量
                    explanation_quality REAL DEFAULT 0.0,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mechanisms_paper ON mechanisms(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mechanisms_quality ON mechanisms(explanation_quality)")

            # 7. 参考文献表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    reference_order INTEGER NOT NULL,

                    -- 参考文献信息
                    authors TEXT,
                    title TEXT,
                    year INTEGER,
                    journal TEXT,
                    volume TEXT,
                    issue TEXT,
                    pages TEXT,
                    doi TEXT,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_references_paper ON paper_references(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_references_year ON paper_references(year)")

            # 8. 引用关系表（论文之间的引用关系）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cited_paper_id INTEGER NOT NULL,
                    citing_paper_id INTEGER NOT NULL,

                    -- 引用类型
                    citation_type TEXT,

                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (cited_paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                    FOREIGN KEY (citing_paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                    UNIQUE(cited_paper_id, citing_paper_id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_paper_id)")

            # 创建触发器：自动更新 updated_at 字段
            tables_to_update = ['papers', 'innovations', 'motivations', 'roadmaps', 'impacts', 'mechanisms']
            for table in tables_to_update:
                cursor.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS update_{table}_timestamp
                    AFTER UPDATE ON {table}
                    FOR EACH ROW
                    BEGIN
                        UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    END
                """)

    def insert_paper(self, paper: Paper) -> bool:
        """
        插入单篇论文数据

        Args:
            paper: Paper 对象

        Returns:
            是否插入成功
        """
        try:
            with self.get_cursor() as cursor:
                # 1. 插入论文基础信息
                cursor.execute("""
                    INSERT INTO papers (
                        folder_name, title, authors, year, journal, volume, issue, pages, doi,
                        published_date, received_date, accepted_date,
                        abstract, keywords, introduction, sections, conclusion, acknowledgments,
                        analysis_completed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper.folder_name,
                    paper.metadata.title,
                    ', '.join(paper.metadata.authors),
                    paper.metadata.year,
                    paper.metadata.journal,
                    paper.metadata.volume,
                    paper.metadata.issue,
                    paper.metadata.pages,
                    paper.metadata.doi,
                    paper.metadata.published_date,
                    paper.metadata.received_date,
                    paper.metadata.accepted_date,
                    paper.content.abstract,
                    ', '.join(paper.content.keywords),
                    paper.content.introduction,
                    str(paper.content.sections),
                    paper.content.conclusion,
                    paper.content.acknowledgments,
                    1 if paper.analysis_completed else 0
                ))

                paper_id = cursor.lastrowid

                # 2. 插入创新点分析
                if paper.innovations:
                    cursor.execute("""
                        INSERT INTO innovations (
                            paper_id, innovation_type,
                            new_phenomena, new_methods, new_objects, summary,
                            confidence_phenomena, confidence_methods, confidence_objects, confidence_overall
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        'innovation_analysis',
                        ', '.join(paper.innovations.new_phenomena),
                        ', '.join(paper.innovations.new_methods),
                        ', '.join(paper.innovations.new_objects),
                        paper.innovations.summary,
                        paper.innovations.confidence_scores.get('phenomena', 0.0),
                        paper.innovations.confidence_scores.get('methods', 0.0),
                        paper.innovations.confidence_scores.get('objects', 0.0),
                        sum(paper.innovations.confidence_scores.values()) / len(paper.innovations.confidence_scores) if paper.innovations.confidence_scores else 0.0
                    ))

                # 3. 插入研究动机
                if paper.motivation:
                    cursor.execute("""
                        INSERT INTO motivations (
                            paper_id, problem_statement, research_objective,
                            research_gap, industry_pain_point, motivation_strength
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        paper.motivation.problem_statement,
                        paper.motivation.research_objective,
                        paper.motivation.research_gap,
                        paper.motivation.industry_pain_point,
                        paper.motivation.motivation_strength
                    ))

                # 4. 插入技术路线
                if paper.roadmap:
                    cursor.execute("""
                        INSERT INTO roadmaps (
                            paper_id, methodology, tools, algorithms, validation_method, roadmap_type
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        paper.roadmap.methodology,
                        ', '.join(paper.roadmap.tools),
                        ', '.join(paper.roadmap.algorithms),
                        paper.roadmap.validation_method,
                        paper.roadmap.roadmap_type
                    ))

                # 5. 插入影响评估
                if paper.impact:
                    cursor.execute("""
                        INSERT INTO impacts (
                            paper_id, time_weight, impact_factor, journal_tier,
                            citation_count, overall_score, maturity_level
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        paper.impact.time_weight,
                        paper.impact.impact_factor,
                        paper.impact.journal_tier,
                        paper.impact.citation_count,
                        paper.impact.overall_score,
                        paper.impact.maturity_level
                    ))

                # 6. 插入机理解析
                if paper.mechanism:
                    cursor.execute("""
                        INSERT INTO mechanisms (
                            paper_id, physical_mechanism, theoretical_basis,
                            key_principles, explanation_quality
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        paper.mechanism.physical_mechanism,
                        paper.mechanism.theoretical_basis,
                        ', '.join(paper.mechanism.key_principles),
                        paper.mechanism.explanation_quality
                    ))

                # 7. 插入参考文献
                if paper.content.references:
                    for order, ref in enumerate(paper.content.references, 1):
                        # 尝试解析参考文献（简化版）
                        cursor.execute("""
                            INSERT INTO paper_references (
                                paper_id, reference_order, title
                            ) VALUES (?, ?, ?)
                        """, (paper_id, order, ref[:500]))  # 限制长度

                # 8. 更新全文搜索字段
                full_text = ' '.join([
                    paper.metadata.title,
                    paper.content.abstract,
                    ' '.join(paper.content.keywords),
                    paper.content.introduction
                ])
                cursor.execute("UPDATE papers SET full_text = ? WHERE id = ?", (full_text, paper_id))

                return True

        except Exception as e:
            print(f"插入论文失败: {e}")
            return False

    def batch_insert_papers(self, papers: List[Paper]) -> int:
        """
        批量插入论文数据

        Args:
            papers: Paper 对象列表

        Returns:
            成功插入的数量
        """
        success_count = 0

        for paper in papers:
            if self.insert_paper(paper):
                success_count += 1

        return success_count

    def get_paper_by_id(self, paper_id: int) -> Optional[Paper]:
        """
        根据 ID 获取论文

        Args:
            paper_id: 论文 ID

        Returns:
            Paper 对象或 None
        """
        try:
            with self.get_cursor() as cursor:
                # 查询论文基础信息
                cursor.execute("""
                    SELECT * FROM papers WHERE id = ?
                """, (paper_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                # 构建 Paper 对象（简化版，实际需要更复杂的逻辑）
                from .paper import Paper, PaperMetadata, PaperContent

                metadata = PaperMetadata(
                    title=row['title'],
                    authors=row['authors'].split(', ') if row['authors'] else [],
                    year=row['year'],
                    journal=row['journal'],
                    volume=row['volume'],
                    issue=row['issue'],
                    pages=row['pages'],
                    doi=row['doi'],
                    published_date=row['published_date'],
                    received_date=row['received_date'],
                    accepted_date=row['accepted_date']
                )

                content = PaperContent(
                    abstract=row['abstract'] or '',
                    keywords=row['keywords'].split(', ') if row['keywords'] else [],
                    introduction=row['introduction'] or '',
                    sections={},
                    conclusion=row['conclusion'] or '',
                    acknowledgments=row['acknowledgments'] or ''
                )

                paper = Paper(
                    folder_name=row['folder_name'],
                    metadata=metadata,
                    content=content
                )

                return paper

        except Exception as e:
            print(f"获取论文失败: {e}")
            return None

    def get_papers_by_year(self, year: int) -> List[Paper]:
        """
        根据年份获取论文列表

        Args:
            year: 年份

        Returns:
            Paper 对象列表
        """
        papers = []

        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM papers WHERE year = ? ORDER BY year DESC
                """, (year,))

                rows = cursor.fetchall()
                for row in rows:
                    paper = self.get_paper_by_id(row['id'])
                    if paper:
                        papers.append(paper)

        except Exception as e:
            print(f"获取论文列表失败: {e}")

        return papers

    def search_papers_by_keyword(self, keyword: str) -> List[Paper]:
        """
        根据关键词搜索论文

        Args:
            keyword: 关键词

        Returns:
            匹配的 Paper 对象列表
        """
        papers = []

        try:
            with self.get_cursor() as cursor:
                # 搜索标题、摘要和关键词字段
                cursor.execute("""
                    SELECT id FROM papers
                    WHERE title LIKE ?
                    OR abstract LIKE ?
                    OR keywords LIKE ?
                """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))

                rows = cursor.fetchall()
                for row in rows:
                    paper = self.get_paper_by_id(row['id'])
                    if paper:
                        papers.append(paper)

        except Exception as e:
            print(f"搜索论文失败: {e}")

        return papers

    def get_top_impact_papers(self, limit: int = 10) -> List[Paper]:
        """
        获取高影响力论文

        Args:
            limit: 返回数量

        Returns:
            高影响力 Paper 对象列表
        """
        papers = []

        try:
            with self.get_cursor() as cursor:
                # 按照 overall_score 排序
                cursor.execute("""
                    SELECT p.id FROM papers p
                    LEFT JOIN impacts i ON p.id = i.paper_id
                    ORDER BY i.overall_score DESC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()
                for row in rows:
                    paper = self.get_paper_by_id(row['id'])
                    if paper:
                        papers.append(paper)

        except Exception as e:
            print(f"获取高影响力论文失败: {e}")

        return papers

    def get_innovation_summary(self) -> Dict[str, List[Paper]]:
        """
        获取创新点汇总

        Returns:
            按新现象/新方法/新对象分类的论文字典
        """
        summary = {
            'new_phenomena': [],
            'new_methods': [],
            'new_objects': []
        }

        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT i.paper_id, i.new_phenomena, i.new_methods, i.new_objects
                    FROM innovations i
                    WHERE i.new_phenomena IS NOT NULL
                    OR i.new_methods IS NOT NULL
                    OR i.new_objects IS NOT NULL
                """)

                rows = cursor.fetchall()
                for row in rows:
                    paper = self.get_paper_by_id(row['paper_id'])
                    if not paper:
                        continue

                    if row['new_phenomena']:
                        summary['new_phenomena'].append(paper)
                    if row['new_methods']:
                        summary['new_methods'].append(paper)
                    if row['new_objects']:
                        summary['new_objects'].append(paper)

        except Exception as e:
            print(f"获取创新点汇总失败: {e}")

        return summary

    def get_all_papers(self, limit: Optional[int] = None) -> List[Paper]:
        """
        获取所有论文

        Args:
            limit: 最大返回数量（None表示全部）

        Returns:
            论文列表
        """
        papers = []

        try:
            with self.get_cursor() as cursor:
                if limit:
                    cursor.execute(f"""
                        SELECT id FROM papers
                        ORDER BY year DESC
                        LIMIT {limit}
                    """)
                else:
                    cursor.execute("""
                        SELECT id FROM papers
                        ORDER BY year DESC
                    """)

                rows = cursor.fetchall()
                for row in rows:
                    paper = self.get_paper_by_id(row['id'])
                    if paper:
                        papers.append(paper)

        except Exception as e:
            logger.error(f"获取所有论文失败: {e}")

        return papers

    def detect_research_gaps(self) -> List[Dict]:
        """
        检测研究空白

        Returns:
            研究空白列表
        """
        gaps = []

        try:
            with self.get_cursor() as cursor:
                # 查询所有研究空白字段
                cursor.execute("""
                    SELECT m.research_gap, p.title, p.year
                    FROM motivations m
                    JOIN papers p ON m.paper_id = p.id
                    WHERE m.research_gap IS NOT NULL AND m.research_gap != ''
                """)

                rows = cursor.fetchall()
                for row in rows:
                    gaps.append({
                        'gap': row['research_gap'],
                        'paper_title': row['title'],
                        'year': row['year']
                    })

        except Exception as e:
            print(f"检测研究空白失败: {e}")

        return gaps

    def export_to_csv(self, table_name: str, output_path: str):
        """
        导出数据表到 CSV

        Args:
            table_name: 表名
            output_path: 输出文件路径
        """
        import csv

        try:
            with self.get_cursor() as cursor:
                # 安全的表名处理（防止 SQL 注入）
                allowed_tables = [
                    'papers', 'innovations', 'motivations', 'roadmaps',
                    'impacts', 'mechanisms', 'paper_references', 'citations'
                ]

                if table_name not in allowed_tables:
                    raise ValueError(f"无效的表名: {table_name}")

                # 查询表数据
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                if not rows:
                    print(f"表 {table_name} 为空")
                    return

                # 获取列名
                column_names = [description[0] for description in cursor.description]

                # 转换为字典列表
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(column_names):
                        value = row[i]
                        # 处理 bytes 类型
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        row_dict[col_name] = value
                    data.append(row_dict)

                # 写入 CSV
                with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                    if data:
                        writer = csv.DictWriter(f, fieldnames=column_names)
                        writer.writeheader()
                        writer.writerows(data)

                print(f"导出成功: {output_path}")

        except Exception as e:
            print(f"导出 CSV 失败: {e}")

    def export_to_json(self, output_path: str):
        """
        导出整个数据库到 JSON

        Args:
            output_path: 输出文件路径
        """
        import json

        try:
            data = {}

            with self.get_cursor() as cursor:
                # 获取所有表名
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]

                # 导出每个表的数据
                for table in tables:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()

                    # 获取列名
                    column_names = [description[0] for description in cursor.description]

                    # 转换为字典列表，处理 bytes 类型
                    table_data = []
                    for row in rows:
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            value = row[i]
                            # 处理 bytes 类型
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='ignore')
                            row_dict[col_name] = value
                        table_data.append(row_dict)

                    data[table] = table_data

            # 写入 JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"导出成功: {output_path}")

        except Exception as e:
            print(f"导出 JSON 失败: {e}")


if __name__ == "__main__":
    # 测试代码
    print("数据库操作模块已加载")
