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
MinerU API 客户端

提供 MinerU 精准解析 API 的完整封装，支持单文件和批量解析。

API 文档: https://mineru.net/
支持功能:
- 单文件 URL 解析
- 批量文件上传解析
- 任务状态查询
- 结果下载和解压
"""

import logging
import time
import zipfile
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

import requests


class ModelVersion(str, Enum):
    """MinerU 模型版本"""
    PIPELINE = "pipeline"  # 传统方法（默认）
    VLM = "vlm"  # 视觉语言模型（推荐）
    MINERU_HTML = "MinerU-HTML"  # HTML 文件专用


class TaskState(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 排队中
    RUNNING = "running"  # 正在解析
    CONVERTING = "converting"  # 格式转换中
    DONE = "done"  # 完成
    FAILED = "failed"  # 失败
    WAITING_FILE = "waiting-file"  # 等待文件上传（批量模式）


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    task_id: str
    state: TaskState
    markdown_url: Optional[str] = None
    zip_url: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[int] = None

    # 进度信息（仅当 state=running 时有效）
    extracted_pages: Optional[int] = None
    total_pages: Optional[int] = None


@dataclass
class MinerUConfig:
    """MinerU API 配置"""
    api_base: str = "https://mineru.net/api/v4"
    token: Optional[str] = None
    timeout: int = 30
    upload_timeout: int = 300
    poll_timeout: int = 600  # 10分钟
    poll_interval: int = 10  # 10秒
    max_retries: int = 3

    # 默认解析参数
    default_model: ModelVersion = ModelVersion.VLM
    enable_formula: bool = True
    enable_table: bool = True
    language: str = "ch"

    def __post_init__(self):
        """初始化后加载 token"""
        if self.token is None:
            self.token = self._load_token_from_file()

    def _load_token_from_file(self) -> Optional[str]:
        """从文件加载 token

        按优先级尝试以下路径:
        1. d:/xfs/phd/github项目/.私人信息/mineru_token.txt
        2. d:/xfs/phd/.私人信息/mineru_token.txt
        """
        possible_paths = [
            Path("d:/xfs/phd/github项目/.私人信息/mineru_token.txt"),
            Path("d:/xfs/phd/.私人信息/mineru_token.txt"),
        ]

        for token_file in possible_paths:
            if token_file.exists():
                try:
                    with open(token_file, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except Exception as e:
                    logging.warning(f"读取 token 文件失败 {token_file}: {e}")

        return None


class MinerUClient:
    """MinerU API 客户端

    提供完整的 PDF 解析功能，支持单文件和批量解析。
    """

    def __init__(self, config: Optional[MinerUConfig] = None):
        """初始化客户端

        Args:
            config: MinerU 配置，默认使用默认配置
        """
        self.config = config or MinerUConfig()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 验证 token
        if not self.config.token:
            raise ValueError(
                "MinerU token 未配置！\n"
                "请将 token 放在以下任一位置:\n"
                "  - d:/xfs/phd/github项目/.私人信息/mineru_token.txt\n"
                "  - d:/xfs/phd/.私人信息/mineru_token.txt"
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json"
        })

    # ==================== 单文件 URL 解析 ====================

    def parse_url(
        self,
        url: str,
        model_version: ModelVersion = ModelVersion.VLM,
        is_ocr: bool = False,
        enable_formula: Optional[bool] = None,
        enable_table: Optional[bool] = None,
        language: Optional[str] = None,
        page_ranges: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        data_id: Optional[str] = None,
        callback: Optional[str] = None,
        no_cache: bool = False,
        poll: bool = True
    ) -> ParseResult:
        """通过 URL 解析文档

        Args:
            url: 文档 URL
            model_version: 模型版本（默认 VLM）
            is_ocr: 是否启用 OCR
            enable_formula: 是否启用公式识别
            enable_table: 是否启用表格识别
            language: 文档语言
            page_ranges: 页码范围（如 "1-10,15-20"）
            extra_formats: 额外输出格式（如 ["docx", "html"]）
            data_id: 数据 ID
            callback: 回调 URL
            no_cache: 是否绕过缓存
            poll: 是否轮询等待结果

        Returns:
            ParseResult: 解析结果
        """
        # 使用默认值
        enable_formula = enable_formula if enable_formula is not None else self.config.enable_formula
        enable_table = enable_table if enable_table is not None else self.config.enable_table
        language = language if language is not None else self.config.language

        # 构建请求体
        data = {
            "url": url,
            "model_version": model_version.value,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language
        }

        # 可选参数
        if page_ranges:
            data["page_ranges"] = page_ranges
        if extra_formats:
            data["extra_formats"] = extra_formats
        if data_id:
            data["data_id"] = data_id
        if callback:
            data["callback"] = callback
            data["seed"] = "mineru_client"  # 简化的随机种子
        if no_cache:
            data["no_cache"] = True

        # 提交任务
        task_id = self._submit_task(data)
        if not task_id:
            return ParseResult(
                success=False,
                task_id="",
                state=TaskState.FAILED,
                error_message="提交任务失败"
            )

        # 轮询结果
        if poll:
            return self._poll_result(task_id)
        else:
            return ParseResult(
                success=True,
                task_id=task_id,
                state=TaskState.PENDING
            )

    # ==================== 批量文件上传解析 ====================

    def parse_files_batch(
        self,
        file_paths: List[Path],
        model_version: ModelVersion = ModelVersion.VLM,
        is_ocr: bool = False,
        enable_formula: Optional[bool] = None,
        enable_table: Optional[bool] = None,
        language: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, ParseResult]:
        """批量上传并解析文件

        Args:
            file_paths: 文件路径列表
            model_version: 模型版本（默认 VLM）
            is_ocr: 是否启用 OCR
            enable_formula: 是否启用公式识别
            enable_table: 是否启用表格识别
            language: 文档语言
            progress_callback: 进度回调函数 (current, total, filename)

        Returns:
            Dict[str, ParseResult]: 文件名到解析结果的映射
        """
        # 使用默认值
        enable_formula = enable_formula if enable_formula is not None else self.config.enable_formula
        enable_table = enable_table if enable_table is not None else self.config.enable_table
        language = language if language is not None else self.config.language

        # 步骤 1: 获取上传链接
        file_infos = [{"name": fp.name} for fp in file_paths]

        data = {
            "files": file_infos,
            "model_version": model_version.value,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language
        }

        batch_result = self._request(
            "POST",
            "/file-urls/batch",
            json=data
        )

        if not batch_result or batch_result.get("code") != 0:
            self.logger.error(f"获取上传链接失败: {batch_result}")
            return {}

        batch_id = batch_result["data"]["batch_id"]
        upload_urls = batch_result["data"]["file_urls"]

        self.logger.info(f"批次任务已创建: batch_id={batch_id}")

        # 步骤 2: 上传文件
        for i, (file_path, upload_url) in enumerate(zip(file_paths, upload_urls)):
            if progress_callback:
                progress_callback(i + 1, len(file_paths), f"上传: {file_path.name}")

            success = self._upload_file(file_path, upload_url)
            if not success:
                self.logger.error(f"文件上传失败: {file_path.name}")

        self.logger.info("所有文件已上传，等待解析...")

        # 步骤 3: 轮询批量结果
        return self._poll_batch_results(batch_id, file_paths, progress_callback)

    # ==================== 任务查询 ====================

    def get_task_status(self, task_id: str) -> Optional[ParseResult]:
        """查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            ParseResult: 任务状态，如果查询失败返回 None
        """
        result = self._request("GET", f"/extract/task/{task_id}")
        if not result or result.get("code") != 0:
            return None

        data = result["data"]
        state = TaskState(data.get("state", "pending"))

        return ParseResult(
            success=True,
            task_id=task_id,
            state=state,
            zip_url=data.get("full_zip_url"),
            error_message=data.get("err_msg"),
            extracted_pages=data.get("extract_progress", {}).get("extracted_pages"),
            total_pages=data.get("extract_progress", {}).get("total_pages")
        )

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, ParseResult]]:
        """查询批量任务状态

        Args:
            batch_id: 批次 ID

        Returns:
            Dict[str, ParseResult]: 文件名到任务状态的映射
        """
        result = self._request("GET", f"/extract-results/batch/{batch_id}")
        if not result or result.get("code") != 0:
            return None

        extract_results = result["data"].get("extract_result", [])

        results = {}
        for item in extract_results:
            file_name = item["file_name"]
            state = TaskState(item["state"])

            results[file_name] = ParseResult(
                success=True,
                task_id=batch_id,
                state=state,
                zip_url=item.get("full_zip_url"),
                error_message=item.get("err_msg"),
                error_code=item.get("err_code"),
                extracted_pages=item.get("extract_progress", {}).get("extracted_pages"),
                total_pages=item.get("extract_progress", {}).get("total_pages")
            )

        return results

    # ==================== 下载结果 ====================

    def download_and_extract(
        self,
        zip_url: str,
        output_dir: Path,
        expected_file: str = "full.md"
    ) -> Optional[Path]:
        """下载并解压结果 ZIP

        Args:
            zip_url: ZIP 文件 URL
            output_dir: 输出目录
            expected_file: 期望的文件名（用于验证）

        Returns:
            Path: 解压后的文件路径，失败返回 None
        """
        try:
            # 下载 ZIP
            self.logger.debug(f"下载结果: {zip_url}")
            response = requests.get(zip_url, timeout=self.config.upload_timeout)
            if response.status_code != 200:
                self.logger.error(f"下载失败: {response.status_code}")
                return None

            # 解压
            output_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(output_dir)

            # 验证
            result_path = output_dir / expected_file
            if result_path.exists():
                return result_path
            else:
                self.logger.error(f"期望的文件不存在: {expected_file}")
                return None

        except Exception as e:
            self.logger.error(f"下载解压失败: {e}")
            return None

    # ==================== 私有方法 ====================

    def _submit_task(self, data: Dict[str, Any]) -> Optional[str]:
        """提交解析任务

        Args:
            data: 请求数据

        Returns:
            task_id: 任务 ID，失败返回 None
        """
        result = self._request("POST", "/extract/task", json=data)
        if not result or result.get("code") != 0:
            return None

        return result["data"]["task_id"]

    def _upload_file(self, file_path: Path, upload_url: str) -> bool:
        """上传文件到 OSS

        Args:
            file_path: 文件路径
            upload_url: 上传 URL

        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'rb') as f:
                # 注意：上传时不需要 Content-Type
                response = requests.put(
                    upload_url,
                    data=f,
                    timeout=self.config.upload_timeout
                )
                return response.status_code in (200, 201)
        except Exception as e:
            self.logger.error(f"上传文件失败 {file_path.name}: {e}")
            return False

    def _poll_result(self, task_id: str) -> ParseResult:
        """轮询等待任务完成

        Args:
            task_id: 任务 ID

        Returns:
            ParseResult: 解析结果
        """
        start_time = time.time()
        poll_count = 0
        max_polls = self.config.poll_timeout // self.config.poll_interval

        while time.time() - start_time < self.config.poll_timeout:
            result = self.get_task_status(task_id)
            if not result:
                poll_count += 1
                time.sleep(self.config.poll_interval)
                continue

            # 检查状态
            if result.state == TaskState.DONE:
                self.logger.info(f"任务完成: {task_id}")
                result.success = True
                return result
            elif result.state == TaskState.FAILED:
                self.logger.error(f"任务失败: {result.error_message}")
                return result
            elif result.state == TaskState.RUNNING:
                if result.total_pages and result.extracted_pages is not None:
                    percent = (result.extracted_pages / result.total_pages) * 100
                    self.logger.info(
                        f"处理进度: {result.extracted_pages}/{result.total_pages} 页 ({percent:.1f}%)"
                    )
                else:
                    self.logger.info(f"处理中... ({poll_count * self.config.poll_interval}秒)")
            else:
                self.logger.info(f"等待中... ({result.state.value})")

            poll_count += 1
            time.sleep(self.config.poll_interval)

        # 超时
        self.logger.error(f"轮询超时: {task_id}")
        return ParseResult(
            success=False,
            task_id=task_id,
            state=TaskState.FAILED,
            error_message=f"轮询超时 ({self.config.poll_timeout}秒)"
        )

    def _poll_batch_results(
        self,
        batch_id: str,
        file_paths: List[Path],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, ParseResult]:
        """轮询批量任务结果

        Args:
            batch_id: 批次 ID
            file_paths: 文件路径列表
            progress_callback: 进度回调

        Returns:
            Dict[str, ParseResult]: 文件名到结果的映射
        """
        start_time = time.time()
        poll_count = 0
        max_polls = self.config.poll_timeout // self.config.poll_interval

        # 创建结果字典
        results = {fp.name: ParseResult(
            success=False,
            task_id=batch_id,
            state=TaskState.PENDING
        ) for fp in file_paths}

        completed = 0
        total = len(file_paths)

        while time.time() - start_time < self.config.poll_timeout:
            batch_results = self.get_batch_status(batch_id)
            if not batch_results:
                poll_count += 1
                time.sleep(self.config.poll_interval)
                continue

            # 更新结果
            new_completed = 0
            for file_name, result in batch_results.items():
                if result.state in (TaskState.DONE, TaskState.FAILED):
                    results[file_name] = result
                    if result.state == TaskState.DONE:
                        new_completed += 1

            # 进度回调
            if progress_callback and new_completed > 0:
                completed += new_completed
                progress_callback(completed, total, f"已完成: {completed}/{total}")

            # 检查是否全部完成
            all_done = all(
                r.state in (TaskState.DONE, TaskState.FAILED)
                for r in results.values()
            )

            if all_done:
                self.logger.info(f"批量任务完成: {batch_id}")
                return results

            # 显示进度
            running = sum(1 for r in results.values() if r.state == TaskState.RUNNING)
            pending = sum(1 for r in results.values() if r.state == TaskState.PENDING)
            self.logger.info(
                f"等待中... 完成: {completed}/{total}, 运行: {running}, 排队: {pending}"
            )

            poll_count += 1
            time.sleep(self.config.poll_interval)

        # 超时
        self.logger.error(f"批量轮询超时: {batch_id}")
        return results

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """发送 HTTP 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            Dict: 响应 JSON，失败返回 None
        """
        url = f"{self.config.api_base}{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.config.timeout,
                    **kwargs
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(
                        f"请求失败 ({attempt + 1}/{self.config.max_retries}): "
                        f"{response.status_code} - {response.text}"
                    )

            except requests.exceptions.ConnectionError as e:
                self.logger.warning(
                    f"连接失败 ({attempt + 1}/{self.config.max_retries}): {e}"
                )
            except requests.exceptions.Timeout as e:
                self.logger.warning(
                    f"请求超时 ({attempt + 1}/{self.config.max_retries}): {e}"
                )
            except Exception as e:
                self.logger.error(f"请求异常: {e}")
                break

        return None


# ==================== 便捷函数 ====================

def parse_pdf_file(
    pdf_path: Path,
    output_dir: Path,
    model_version: ModelVersion = ModelVersion.VLM,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bool:
    """解析单个 PDF 文件

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        model_version: 模型版本
        progress_callback: 进度回调

    Returns:
        bool: 是否成功
    """
    client = MinerUClient()
    results = client.parse_files_batch(
        [pdf_path],
        model_version=model_version,
        progress_callback=progress_callback
    )

    if not results:
        return False

    result = results[pdf_path.name]
    if not result.success or result.state != TaskState.DONE:
        return False

    # 下载并解压
    md_folder = output_dir / pdf_path.stem
    full_md = client.download_and_extract(result.zip_url, md_folder, "full.md")

    return full_md is not None and full_md.exists()


def parse_pdf_files(
    pdf_paths: List[Path],
    output_dir: Path,
    model_version: ModelVersion = ModelVersion.VLM,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, bool]:
    """批量解析 PDF 文件

    Args:
        pdf_paths: PDF 文件路径列表
        output_dir: 输出目录
        model_version: 模型版本
        progress_callback: 进度回调

    Returns:
        Dict[str, bool]: 文件名到成功状态的映射
    """
    client = MinerUClient()
    results = client.parse_files_batch(
        pdf_paths,
        model_version=model_version,
        progress_callback=progress_callback
    )

    success_map = {}
    for pdf_path in pdf_paths:
        result = results.get(pdf_path.name)
        if result and result.success and result.state == TaskState.DONE:
            md_folder = output_dir / pdf_path.stem
            full_md = client.download_and_extract(result.zip_url, md_folder, "full.md")
            success_map[pdf_path.name] = full_md is not None and full_md.exists()
        else:
            success_map[pdf_path.name] = False

    return success_map
