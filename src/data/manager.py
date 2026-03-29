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
数据库管理器

提供 SQLite 数据库的统一管理接口，支持：
- 数据库连接管理
- CRUD 操作
- 事务管理
- 查询构建器
- 数据库版本控制
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime


class DatabaseManager:
    """数据库管理器

    负责管理 SQLite 数据库连接和操作。

    用法：
    ```python
    db = DatabaseManager("data/literature.db")

    # 插入文献
    db.insert('papers', {
        'title': 'Sample Paper',
        'doi': '10.1234/demo',
        'year': 2024
    })

    # 查询文献
    papers = db.query('papers', {'year': 2024})

    # 更新文献
    db.update('papers', {'doi': '10.1234/demo'}, {'year': 2025})

    # 删除文献
    db.delete('papers', {'doi': '10.1234/demo'})
    ```
    """

    def __init__(self, db_path: str = "data/literature.db"):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径（默认：data/literature.db）
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 初始化数据库
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. 文献表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    doi TEXT UNIQUE,
                    authors TEXT,
                    year INTEGER,
                    journal TEXT,
                    volume TEXT,
                    issue TEXT,
                    pages TEXT,
                    abstract TEXT,
                    keywords TEXT,
                    pdf_path TEXT,
                    markdown_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 2. 文献分析结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    analyze_type TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES papers (id),
                    UNIQUE(paper_id, analyze_type)
                )
            ''')

            # 3. 文献分类表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    domain TEXT NOT NULL,
                    subdomain TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES papers (id)
                )
            ''')

            # 4. 工作流任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workflow_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    parameters TEXT,
                    result TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')

            # 5. PPT 生成历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ppt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 6. 项目配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_paper ON analysis_results(paper_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON workflow_tasks(status)')

            conn.commit()
            self.logger.info(f"数据库初始化完成: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 返回字典格式
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"数据库错误: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据

        Args:
            table: 表名
            data: 数据字典

        Returns:
            插入的行 ID
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, list(data.values()))
            conn.commit()
            return cursor.lastrowid

    def query(
        self,
        table: str,
        where: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """查询数据

        Args:
            table: 表名
            where: 查询条件
            order_by: 排序字段
            limit: 限制数量

        Returns:
            查询结果列表
        """
        sql = f"SELECT * FROM {table}"
        params = []

        if where:
            conditions = ' AND '.join([f"{k} = ?" for k in where.keys()])
            sql += f" WHERE {conditions}"
            params = list(where.values())

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit:
            sql += f" LIMIT {limit}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update(self, table: str, where: Dict[str, Any], data: Dict[str, Any]) -> int:
        """更新数据

        Args:
            table: 表名
            where: 更新条件
            data: 更新数据

        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        params = list(data.values()) + list(where.values())

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """删除数据

        Args:
            table: 表名
            where: 删除条件

        Returns:
            影响的行数
        """
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clause}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, list(where.values()))
            conn.commit()
            return cursor.rowcount

    def execute_raw(self, sql: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """执行原生 SQL

        Args:
            sql: SQL 语句
            params: 参数列表

        Returns:
            查询结果（如果是 SELECT）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            if sql.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                conn.commit()
                return []

    def count(self, table: str, where: Dict[str, Any] = None) -> int:
        """统计记录数

        Args:
            table: 表名
            where: 查询条件

        Returns:
            记录数
        """
        sql = f"SELECT COUNT(*) as count FROM {table}"
        params = []

        if where:
            conditions = ' AND '.join([f"{k} = ?" for k in where.keys()])
            sql += f" WHERE {conditions}"
            params = list(where.values())

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result['count'] if result else 0

    def transaction(self):
        """获取事务上下文管理器

        用法：
        ```python
        with db.transaction() as conn:
            db.insert('papers', {...})
            db.insert('analysis_results', {...})
        ```
        """
        return self.get_connection()
