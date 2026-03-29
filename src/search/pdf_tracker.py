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
PDF 跟踪器

跟踪和管理 PDF 文件的下载状态。
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from enum import Enum


class PDFStatus(Enum):
    """PDF 状态枚举"""
    PENDING = "pending"  # 待下载
    DOWNLOADING = "downloading"  # 下载中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    PAUSED = "paused"  # 已暂停


class PDFTracker:
    """PDF 跟踪器

    跟踪和管理 PDF 文件的下载状态、进度和历史。

    功能：
    - PDF 下载状态跟踪
    - 下载进度记录
    - 文件完整性校验
    - 下载历史管理
    - 断点续传支持
    """

    def __init__(self, download_dir: str = "data/pdfs", tracker_db: str = "data/pdf_tracker.json"):
        """初始化 PDF 跟踪器

        Args:
            download_dir: PDF 下载目录
            tracker_db: 跟踪数据库文件路径
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.tracker_db = Path(tracker_db)
        self.tracker_data: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(self.__class__.__name__)

        # 加载跟踪数据
        self._load_tracker_data()

    def _load_tracker_data(self):
        """加载跟踪数据"""
        if self.tracker_db.exists():
            import json
            try:
                with open(self.tracker_db, 'r', encoding='utf-8') as f:
                    self.tracker_data = json.load(f)
                self.logger.info(f"已加载 {len(self.tracker_data)} 个跟踪记录")
            except Exception as e:
                self.logger.error(f"加载跟踪数据失败: {e}")
                self.tracker_data = {}

    def _save_tracker_data(self):
        """保存跟踪数据"""
        import json
        try:
            with open(self.tracker_db, 'w', encoding='utf-8') as f:
                json.dump(self.tracker_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存跟踪数据失败: {e}")

    def add_pdf(
        self,
        paper_id: str,
        url: str,
        title: str,
        expected_size: int = None,
        expected_hash: str = None
    ):
        """添加 PDF 到跟踪列表

        Args:
            paper_id: 文献 ID
            url: 下载 URL
            title: 文献标题
            expected_size: 预期文件大小（字节）
            expected_hash: 预期文件哈希（MD5）
        """
        if paper_id in self.tracker_data:
            self.logger.warning(f"PDF 已在跟踪列表中: {paper_id}")
            return

        self.tracker_data[paper_id] = {
            "url": url,
            "title": title,
            "status": PDFStatus.PENDING.value,
            "progress": 0.0,  # 下载进度 (0-100)
            "downloaded_size": 0,
            "expected_size": expected_size,
            "expected_hash": expected_hash,
            "actual_hash": None,
            "file_path": None,
            "error_message": None,
            "attempts": 0,
            "max_attempts": 3,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None
        }

        self._save_tracker_data()
        self.logger.info(f"已添加 PDF 到跟踪列表: {paper_id}")

    def update_progress(self, paper_id: str, progress: float, downloaded_size: int):
        """更新下载进度

        Args:
            paper_id: 文献 ID
            progress: 下载进度 (0-100)
            downloaded_size: 已下载大小（字节）
        """
        if paper_id not in self.tracker_data:
            self.logger.warning(f"PDF 不在跟踪列表中: {paper_id}")
            return

        record = self.tracker_data[paper_id]
        record["progress"] = progress
        record["downloaded_size"] = downloaded_size
        record["status"] = PDFStatus.DOWNLOADING.value
        record["updated_at"] = datetime.now().isoformat()

        # 不频繁保存，仅在进度变化较大时保存
        if progress % 10 < 1:
            self._save_tracker_data()

    def mark_completed(self, paper_id: str, file_path: str):
        """标记下载完成

        Args:
            paper_id: 文献 ID
            file_path: 下载文件路径
        """
        if paper_id not in self.tracker_data:
            self.logger.warning(f"PDF 不在跟踪列表中: {paper_id}")
            return

        # 计算文件哈希
        actual_hash = self._calculate_file_hash(file_path)

        record = self.tracker_data[paper_id]
        record["status"] = PDFStatus.COMPLETED.value
        record["progress"] = 100.0
        record["file_path"] = file_path
        record["actual_hash"] = actual_hash
        record["completed_at"] = datetime.now().isoformat()
        record["updated_at"] = datetime.now().isoformat()

        # 验证文件完整性
        if record["expected_hash"] and actual_hash != record["expected_hash"]:
            self.logger.warning(f"文件哈希不匹配: {paper_id}")

        self._save_tracker_data()
        self.logger.info(f"PDF 下载完成: {paper_id}")

    def mark_failed(self, paper_id: str, error_message: str):
        """标记下载失败

        Args:
            paper_id: 文献 ID
            error_message: 错误消息
        """
        if paper_id not in self.tracker_data:
            self.logger.warning(f"PDF 不在跟踪列表中: {paper_id}")
            return

        record = self.tracker_data[paper_id]
        record["status"] = PDFStatus.FAILED.value
        record["error_message"] = error_message
        record["attempts"] += 1
        record["updated_at"] = datetime.now().isoformat()

        self._save_tracker_data()
        self.logger.error(f"PDF 下载失败: {paper_id} - {error_message}")

    def mark_paused(self, paper_id: str):
        """标记暂停下载

        Args:
            paper_id: 文献 ID
        """
        if paper_id not in self.tracker_data:
            self.logger.warning(f"PDF 不在跟踪列表中: {paper_id}")
            return

        record = self.tracker_data[paper_id]
        record["status"] = PDFStatus.PAUSED.value
        record["updated_at"] = datetime.now().isoformat()

        self._save_tracker_data()
        self.logger.info(f"PDF 下载已暂停: {paper_id}")

    def get_status(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """获取 PDF 状态

        Args:
            paper_id: 文献 ID

        Returns:
            状态信息字典
        """
        return self.tracker_data.get(paper_id)

    def get_all_by_status(self, status: PDFStatus) -> List[Dict[str, Any]]:
        """获取指定状态的所有 PDF

        Args:
            status: PDF 状态

        Returns:
            PDF 列表
        """
        return [
            {"paper_id": paper_id, **data}
            for paper_id, data in self.tracker_data.items()
            if data["status"] == status.value
        ]

    def get_pending(self) -> List[Dict[str, Any]]:
        """获取待下载的 PDF 列表

        Returns:
            待下载 PDF 列表
        """
        return self.get_all_by_status(PDFStatus.PENDING)

    def get_failed(self) -> List[Dict[str, Any]]:
        """获取失败的 PDF 列表

        Returns:
            失败 PDF 列表
        """
        return self.get_all_by_status(PDFStatus.FAILED)

    def retry_failed(self, paper_id: str):
        """重试失败的下载

        Args:
            paper_id: 文献 ID
        """
        if paper_id not in self.tracker_data:
            self.logger.warning(f"PDF 不在跟踪列表中: {paper_id}")
            return

        record = self.tracker_data[paper_id]

        if record["attempts"] >= record["max_attempts"]:
            self.logger.warning(f"已达到最大重试次数: {paper_id}")
            return

        record["status"] = PDFStatus.PENDING.value
        record["error_message"] = None
        record["updated_at"] = datetime.now().isoformat()

        self._save_tracker_data()
        self.logger.info(f"已重置 PDF 下载: {paper_id}")

    def remove_pdf(self, paper_id: str):
        """从跟踪列表移除 PDF

        Args:
            paper_id: 文献 ID
        """
        if paper_id in self.tracker_data:
            del self.tracker_data[paper_id]
            self._save_tracker_data()
            self.logger.info(f"已移除 PDF: {paper_id}")

    def clear_completed(self):
        """清空已完成的记录"""
        to_remove = [
            paper_id for paper_id, data in self.tracker_data.items()
            if data["status"] == PDFStatus.COMPLETED.value
        ]

        for paper_id in to_remove:
            del self.tracker_data[paper_id]

        if to_remove:
            self._save_tracker_data()
            self.logger.info(f"已清空 {len(to_remove)} 个已完成记录")

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        stats = {status.value: 0 for status in PDFStatus}

        for data in self.tracker_data.values():
            stats[data["status"]] += 1

        stats["total"] = len(self.tracker_data)

        return stats

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件 MD5 哈希

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希字符串
        """
        hash_md5 = hashlib.md5()

        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)

            return hash_md5.hexdigest()

        except Exception as e:
            self.logger.error(f"计算文件哈希失败: {e}")
            return ""
