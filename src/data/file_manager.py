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
文件管理器

负责管理所有文件类型，包括：
- PDF 文件管理
- Markdown 文件管理
- JSON 文件管理
- 配置文件管理
- 临时文件清理
"""

import os
import json
import shutil
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class FileManager:
    """文件管理器

    提供统一的文件操作接口。

    用法：
    ```python
    fm = FileManager("data/projects")

    # 保存 PDF
    pdf_path = fm.save_pdf(
        source_path="downloads/paper.pdf",
        project_id="project_001",
        paper_id="paper_123"
    )

    # 保存 Markdown
    md_path = fm.save_markdown(
        content="# Paper Title\\n\\nContent...",
        project_id="project_001",
        paper_id="paper_123",
        filename="analysis.md"
    )

    # 保存 JSON
    json_path = fm.save_json(
        data={"title": "Paper", "year": 2024},
        project_id="project_001",
        filename="metadata.json"
    )
    ```
    """

    def __init__(self, base_path: str = "data/projects"):
        """初始化文件管理器

        Args:
            base_path: 基础存储路径（默认：data/projects）
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 创建标准目录结构
        self._create_standard_structure()

    def _create_standard_structure(self):
        """创建标准目录结构"""
        directories = [
            "pdfs",           # PDF 文件
            "markdown",       # Markdown 文件
            "json",           # JSON 数据
            "cache",          # 缓存文件
            "temp",           # 临时文件
            "backups",        # 备份文件
            "ppt",            # PPT 文件
        ]

        for dir_name in directories:
            (self.base_path / dir_name).mkdir(exist_ok=True)

    def save_pdf(
        self,
        source_path: str,
        project_id: str,
        paper_id: str
    ) -> Path:
        """保存 PDF 文件到标准位置

        Args:
            source_path: 源文件路径
            project_id: 项目 ID
            paper_id: 文献 ID

        Returns:
            保存后的文件路径
        """
        # 构建目标路径：data/projects/{project_id}/pdfs/{paper_id}.pdf
        target_dir = self.base_path / project_id / "pdfs"
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / f"{paper_id}.pdf"

        # 复制文件
        shutil.copy2(source_path, target_path)

        self.logger.info(f"PDF 保存成功: {target_path}")
        return target_path

    def save_markdown(
        self,
        content: str,
        project_id: str,
        paper_id: str = None,
        filename: str = "full.md"
    ) -> Path:
        """保存 Markdown 文件

        Args:
            content: Markdown 内容
            project_id: 项目 ID
            paper_id: 文献 ID（可选）
            filename: 文件名（默认：full.md）

        Returns:
            保存后的文件路径
        """
        # 构建目标路径
        if paper_id:
            target_dir = self.base_path / project_id / "markdown" / paper_id
        else:
            target_dir = self.base_path / project_id / "markdown"

        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        # 写入文件
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Markdown 保存成功: {target_path}")
        return target_path

    def save_json(
        self,
        data: Dict[str, Any],
        project_id: str,
        filename: str,
        paper_id: str = None
    ) -> Path:
        """保存 JSON 数据

        Args:
            data: JSON 数据
            project_id: 项目 ID
            filename: 文件名
            paper_id: 文献 ID（可选）

        Returns:
            保存后的文件路径
        """
        # 构建目标路径
        if paper_id:
            target_dir = self.base_path / project_id / "json" / paper_id
        else:
            target_dir = self.base_path / project_id / "json"

        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        # 写入文件
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"JSON 保存成功: {target_path}")
        return target_path

    def read_markdown(self, file_path: str) -> str:
        """读取 Markdown 文件

        Args:
            file_path: 文件路径

        Returns:
            Markdown 内容
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def read_json(self, file_path: str) -> Dict[str, Any]:
        """读取 JSON 文件

        Args:
            file_path: 文件路径

        Returns:
            JSON 数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_files(
        self,
        project_id: str,
        file_type: str = "all"
    ) -> List[Path]:
        """列出项目中的所有文件

        Args:
            project_id: 项目 ID
            file_type: 文件类型（pdf, markdown, json, all）

        Returns:
            文件路径列表
        """
        project_dir = self.base_path / project_id

        if not project_dir.exists():
            return []

        files = []

        if file_type == "all":
            # 列出所有文件
            files = list(project_dir.rglob("*.*"))
        else:
            # 列出特定类型
            type_dir = project_dir / f"{file_type}s" if file_type != "markdown" else project_dir / file_type
            if type_dir.exists():
                files = list(type_dir.rglob("*.*"))

        return [f for f in files if f.is_file()]

    def delete_file(self, file_path: str) -> bool:
        """删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                self.logger.info(f"文件删除成功: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"文件删除失败: {e}")
            return False

    def move_file(self, source: str, target: str) -> bool:
        """移动文件

        Args:
            source: 源路径
            target: 目标路径

        Returns:
            是否成功
        """
        try:
            shutil.move(source, target)
            self.logger.info(f"文件移动成功: {source} -> {target}")
            return True
        except Exception as e:
            self.logger.error(f"文件移动失败: {e}")
            return False

    def copy_file(self, source: str, target: str) -> bool:
        """复制文件

        Args:
            source: 源路径
            target: 目标路径

        Returns:
            是否成功
        """
        try:
            shutil.copy2(source, target)
            self.logger.info(f"文件复制成功: {source} -> {target}")
            return True
        except Exception as e:
            self.logger.error(f"文件复制失败: {e}")
            return False

    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希值
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_file_size(self, file_path: str) -> int:
        """获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            文件大小
        """
        return Path(file_path).stat().st_size

    def clean_temp_files(self, project_id: str = None):
        """清理临时文件

        Args:
            project_id: 项目 ID（可选，不指定则清理所有）
        """
        if project_id:
            temp_dir = self.base_path / project_id / "temp"
        else:
            temp_dir = self.base_path / "temp"

        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"临时文件清理完成: {temp_dir}")

    def create_backup(
        self,
        project_id: str,
        backup_name: str = None
    ) -> Path:
        """创建项目备份

        Args:
            project_id: 项目 ID
            backup_name: 备份名称（可选）

        Returns:
            备份路径
        """
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        source_dir = self.base_path / project_id
        backup_dir = self.base_path / "backups" / backup_name

        if source_dir.exists():
            shutil.copytree(source_dir, backup_dir)
            self.logger.info(f"备份创建成功: {backup_dir}")
            return backup_dir
        else:
            raise FileNotFoundError(f"项目目录不存在: {source_dir}")

    def restore_backup(self, backup_path: str, project_id: str):
        """从备份恢复

        Args:
            backup_path: 备份路径
            project_id: 项目 ID
        """
        backup_dir = Path(backup_path)
        target_dir = self.base_path / project_id

        if backup_dir.exists():
            if target_dir.exists():
                shutil.rmtree(target_dir)

            shutil.copytree(backup_dir, target_dir)
            self.logger.info(f"备份恢复成功: {backup_path} -> {target_dir}")
        else:
            raise FileNotFoundError(f"备份目录不存在: {backup_path}")
