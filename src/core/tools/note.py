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
笔记工具集

提供笔记创建、管理、导出的工具集合。

工具集：
- NoteTakingToolkit: 笔记记录工具集
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base import BaseToolkit


class NoteTakingToolkit(BaseToolkit):
    """笔记记录工具集

    提供笔记创建、管理、搜索、导出等功能。
    """

    def get_name(self) -> str:
        return "NoteTakingToolkit"

    def get_tools(self) -> List[Any]:
        return [
            self.create_note,
            self.update_note,
            self.delete_note,
            self.search_notes,
            self.export_notes,
            self.link_to_paper,
            self.add_tags,
            self.get_note_summary
        ]

    def get_description(self) -> str:
        return "笔记记录工具集：支持笔记创建、管理、搜索、导出"

    # 工具方法
    def create_note(
        self,
        title: str,
        content: str,
        paper_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """创建笔记

        Args:
            title: 笔记标题
            content: 笔记内容
            paper_id: 关联文献ID（可选）
            tags: 标签列表（可选）

        Returns:
            创建的笔记对象
        """
        note = {
            "id": f"note_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "content": content,
            "paper_id": paper_id,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return note

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """更新笔记

        Args:
            note_id: 笔记ID
            title: 新标题（可选）
            content: 新内容（可选）
            tags: 新标签列表（可选）

        Returns:
            更新后的笔记对象
        """
        return {
            "id": note_id,
            "updated_at": datetime.now().isoformat()
        }

    def delete_note(self, note_id: str) -> bool:
        """删除笔记

        Args:
            note_id: 笔记ID

        Returns:
            是否成功
        """
        return True

    def search_notes(
        self,
        keyword: str,
        tags: Optional[List[str]] = None,
        paper_id: Optional[str] = None
    ) -> List[Dict]:
        """搜索笔记

        Args:
            keyword: 关键词
            tags: 标签过滤（可选）
            paper_id: 文献ID过滤（可选）

        Returns:
            笔记列表
        """
        return []

    def export_notes(
        self,
        notes: List[Dict],
        format: str = "markdown",
        output_path: Optional[str] = None
    ) -> str:
        """导出笔记

        Args:
            notes: 笔记列表
            format: 导出格式（markdown/json/txt）
            output_path: 输出路径（可选）

        Returns:
            导出文件路径或内容
        """
        if format == "markdown":
            content = self._to_markdown(notes)
        elif format == "json":
            import json
            content = json.dumps(notes, ensure_ascii=False, indent=2)
        else:
            content = self._to_text(notes)

        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
            return output_path
        return content

    def link_to_paper(self, note_id: str, paper_id: str) -> bool:
        """关联笔记到文献

        Args:
            note_id: 笔记ID
            paper_id: 文献ID

        Returns:
            是否成功
        """
        return True

    def add_tags(self, note_id: str, tags: List[str]) -> bool:
        """添加标签

        Args:
            note_id: 笔记ID
            tags: 标签列表

        Returns:
            是否成功
        """
        return True

    def get_note_summary(self, note_id: str) -> Dict[str, Any]:
        """获取笔记摘要

        Args:
            note_id: 笔记ID

        Returns:
            笔记摘要信息
        """
        return {
            "id": note_id,
            "word_count": 0,
            "tags": [],
            "linked_papers": []
        }

    # 私有方法
    def _to_markdown(self, notes: List[Dict]) -> str:
        """转换为 Markdown 格式

        Args:
            notes: 笔记列表

        Returns:
            Markdown 字符串
        """
        lines = ["# 笔记导出\n"]
        for note in notes:
            lines.append(f"## {note.get('title', '无标题')}\n")
            lines.append(f"{note.get('content', '')}\n")
            if note.get('tags'):
                lines.append(f"标签: {', '.join(note['tags'])}\n")
            lines.append("\n---\n")
        return "\n".join(lines)

    def _to_text(self, notes: List[Dict]) -> str:
        """转换为纯文本格式

        Args:
            notes: 笔记列表

        Returns:
            纯文本字符串
        """
        lines = []
        for note in notes:
            lines.append(f"标题: {note.get('title', '无标题')}")
            lines.append(note.get('content', ''))
            lines.append("-" * 50)
        return "\n".join(lines)


__all__ = ["NoteTakingToolkit"]
