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
批量文献分类器（重构版）

基于用户指定的领域文件夹，使用 Agent 判断每篇论文的相关度。
"""

import json
import re
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class BatchPaperClassifier:
    """批量文献分类器（重构版）

    工作流程：
    1. 扫描 categories/ 目录下的所有子文件夹（领域）
    2. 对每篇论文，调用 Agent 判断它与各领域的相关度
    3. 将相关度达到阈值的论文复制到对应文件夹
    """

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.7",
        timeout: int = 1200  # 20 分钟
    ):
        """初始化批量分类器

        Args:
            api_key: GLM API 密钥
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def classify_papers_batch(
        self,
        papers: List[Dict[str, Any]],
        domains: List[str],
        categories_dir: Path,
        metadata_file: Path,
        progress_callback: callable = None,
        batch_size: int = 50,
        relevance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """批量分类文献（基于用户指定的领域）

        Args:
            papers: 文献列表
            domains: 用户指定的技术领域列表
            categories_dir: 领域文件夹目录
            metadata_file: metadata.json 文件路径
            progress_callback: 进度回调函数
            batch_size: 每批处理的文献数量
            relevance_threshold: 相关度阈值（默认 0.7）

        Returns:
            分类统计信息
        """
        from ..api.glm_client import GLMAPIClient

        # 1. 创建领域文件夹
        categories_dir.mkdir(parents=True, exist_ok=True)
        domain_dirs = {}
        for domain in domains:
            domain_path = categories_dir / domain
            domain_path.mkdir(parents=True, exist_ok=True)
            domain_dirs[domain] = domain_path

        self.logger.info(f"创建 {len(domains)} 个领域文件夹: {list(domains)}")

        # 只处理已下载的文献（基于 pdf_downloaded 字段）
        papers_with_pdf = []
        no_pdf_count = 0

        for paper in papers:
            if paper.get('pdf_downloaded', False):
                papers_with_pdf.append(paper)
            else:
                no_pdf_count += 1

        total_papers = len(papers)
        pdf_papers_count = len(papers_with_pdf)

        self.logger.info(f"[文献统计] 总数={total_papers}, 已下载={pdf_papers_count}, 未下载={no_pdf_count}")

        if pdf_papers_count == 0:
            self.logger.error("[错误] 没有找到任何已下载的PDF文献！请先下载文献。")
            return {
                "total": total_papers,
                "processed": 0,
                "classified": 0,
                "already_classified": 0,
                "failed": 0,
                "domain_distribution": {domain: 0 for domain in domains},
                "domain_count": len(domains)
            }

        self.logger.info(f"开始批量分类，共 {pdf_papers_count} 篇文献（仅处理已下载的）")

        # 只处理已下载的文献
        papers = papers_with_pdf
        total = len(papers)

        # 清空所有现有的题录.json文件（避免累积）
        for domain in domains:
            domain_dir = categories_dir / domain
            tilu_file = domain_dir / "题录.json"
            if tilu_file.exists():
                tilu_file.unlink()
                self.logger.info(f"[清空] 已删除 {domain} 的旧题录.json")

        if progress_callback:
            progress_callback(0, total, f"准备分类 {total} 篇文献...")

        # 2. 创建 API 客户端
        self.logger.info("创建 GLM API 客户端...")
        api_client = GLMAPIClient(
            api_key=self.api_key,
            model=self.model,
            timeout=self.timeout
        )
        self.logger.info("API 客户端创建成功")

        # 3. 分批处理
        self.logger.info("开始分批处理文献...")
        total = total_papers  # 便于后续使用
        processed_count = 0
        domain_stats = {domain: 0 for domain in domain_dirs}

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_papers = papers[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            self.logger.info(f"处理批次 {batch_num}/{total_batches}: 文献 {batch_start + 1}-{batch_end}")

            # 4. 构造 Prompt（包含领域列表）
            self.logger.info("构建 API Prompt...")
            system_prompt = self._build_system_prompt(domains)
            user_message = self._build_user_message(batch_papers, domains)
            self.logger.info(f"Prompt 构建完成，用户消息长度: {len(user_message)} 字符")

            # 5. 调用 API
            try:
                self.logger.info(f"调用 GLM API（超时设置: {self.timeout}秒）...")
                self.logger.info(f"[DEBUG] API 参数: system_prompt长度={len(system_prompt)}, user_message长度={len(user_message)}, max_tokens=128000")

                import time
                start_time = time.time()

                response = asyncio.run(api_client.generate(
                    system_message=system_prompt,
                    user_message=user_message,
                    max_tokens=128000
                ))

                elapsed = time.time() - start_time
                self.logger.info(f"[DEBUG] API 调用返回，耗时: {elapsed:.2f}秒")
                self.logger.info(f"API 调用成功，响应长度: {len(response)} 字符")

                if progress_callback:
                    progress_callback(batch_end, total, f"解析批次 {batch_num}/{total_batches} 结果...")

                # 6. 解析响应
                results = self._parse_response(response, len(batch_papers), len(domains))

                if not results:
                    self.logger.error(f"批次 {batch_num} 解析失败")
                    continue

                # 7. 复制相关论文到对应文件夹
                for i, paper in enumerate(batch_papers):
                    paper_id = i + 1
                    if paper_id < len(results):
                        paper_result = results[paper_id - 1]  # paper_id 从 1 开始

                        # 检查每个领域的相关度
                        for domain_name in domain_dirs:
                            relevance = paper_result.get(domain_name, {}).get("relevance", 0)

                            if relevance >= relevance_threshold:
                                # 复制 PDF 到领域文件夹
                                self._copy_paper_to_domain(
                                    paper, domain_dirs[domain_name], relevance
                                )
                                domain_stats[domain_name] += 1

                                if i % 5 == 0:
                                    title = paper.get('title', 'N/A')[:40]
                                    self.logger.info(f"[{domain_name}] {title}... → {relevance:.0%}")
                    elif paper_id >= len(results):
                        # AI 返回结果数量不足，记录警告
                        self.logger.warning(f"论文 {paper_id} ({paper.get('title', 'N/A')[:40]}) 的分类结果缺失")

                processed_count += len(batch_papers)

                if progress_callback:
                    progress_callback(batch_end, total, f"已完成 {batch_end}/{total} 篇")

            except Exception as e:
                self.logger.error(f"批次 {batch_num} 处理失败: {e}")

        # 8. 返回统计
        # 计算实际被分类到某个领域的文献数量（相关度 >= 70%）
        classified_count = sum(domain_stats.values())

        stats = {
            "total": total,
            "processed": processed_count,
            "classified": classified_count,  # GUI 期望的字段
            "already_classified": 0,  # 每次都是新分类，没有"已分类"
            "failed": 0,  # 暂不支持失败统计
            "domain_distribution": domain_stats,  # GUI 期望的字段
            "domains": domain_stats,  # 兼容旧字段
            "domain_count": len(domain_dirs)
        }

        self.logger.info(f"批量分类完成: {processed_count}/{total} 篇，相关度≥70%: {classified_count} 篇")

        if progress_callback:
            progress_callback(total, total, f"分类完成！")

        return stats

    def _copy_paper_to_domain(self, paper: Dict, domain_dir: Path, relevance: float):
        """复制论文 PDF 到领域文件夹

        Args:
            paper: 论文信息
            domain_dir: 领域文件夹路径
            relevance: 相关度
        """
        pdf_path = paper.get('pdf_path', '')
        if not pdf_path:
            return

        # 转换反斜杠为正斜杠
        pdf_path = pdf_path.replace('\\', '/')

        # 计算 PDF 绝对路径（基于 all_pdf_dir）
        # pdf_path 格式: data/projects/wind_aero/pdfs/all/xxx.pdf
        # 从 categories_dir 推算 all_pdf_dir
        all_pdf_dir = domain_dir.parent.parent / "all"  # categories/ -> all/
        pdf_full_path = all_pdf_dir / Path(pdf_path).name

        # 复制 PDF（如果存在）
        if pdf_full_path.exists():
            target_path = domain_dir / pdf_full_path.name
            try:
                shutil.copy2(pdf_full_path, target_path)
                self.logger.info(f"已复制 PDF: {pdf_full_path.name}")
            except Exception as e:
                self.logger.error(f"复制文件失败: {e}")
        else:
            self.logger.warning(f"PDF 不存在，仅记录到题录: {pdf_full_path.name}")

        # 无论如何都要记录到题录.json
        metadata_path = domain_dir / "题录.json"

        # 加载现有数据（如果存在）
        existing = []
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        paper_entry = {
            "title": paper.get('title', ''),
            "authors": paper.get('authors', []),
            "abstract": paper.get('abstract', ''),
            "year": paper.get('year', ''),
            "relevance": relevance,
            "pdf_path": pdf_path,
            "pdf_exists": pdf_full_path.exists()  # 新增：标记PDF是否存在
        }

        # 检查是否已存在（避免重复添加）
        title_match = False
        for entry in existing:
            if entry.get('title') == paper_entry.get('title'):
                title_match = True
                break

        if not title_match:
            existing.append(paper_entry)

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _build_system_prompt(self, domains: List[str]) -> str:
        """构建系统 Prompt

        Args:
            domains: 领域名称列表
        """
        domain_list = "\n".join([f"- {name}" for name in domains])

        return f"""你是一位专业的风电领域文献分类专家。

<task>
你需要判断每篇论文与指定技术领域的相关度。
</task>

<domain_list>
用户关心的技术领域：
{domain_list}
</domain_list>

<relevance_criteria>
相关度评估标准：
- 0.9-1.0：论文明确属于该领域（标题/摘要/关键词都直接相关）
- 0.7-0.9：论文很可能属于该领域（内容高度相关）
- 0.5-0.7：论文可能属于该领域（部分内容相关）
- <0.5：论文与该领域无关

<output_format>
你必须严格按照以下 JSON 数组格式输出：

```json
[
  {{
    "paper_id": 1,
    "领域1名称": {{"relevance": 0.85, "reasoning": "选择理由"}},
    "领域2名称": {{"relevance": 0.30, "reasoning": "选择理由"}},
    ...
  }},
  ...
]
```

重要：
- paper_id 从 1 开始连续编号
- 为每篇论文评估所有领域的相关度
- relevance 范围：0.0 - 1.0
"""

    def _build_user_message(self, papers: List[Dict], domains: List[str]) -> str:
        """构建用户消息

        Args:
            papers: 文献列表
            domains: 领域名称列表

        Returns:
            用户消息字符串
        """
        message = f"请对以下 {len(papers)} 篇文献进行分类，评估它们与 {len(domains)} 个领域的相关度：\n\n"
        message += f"领域列表：{', '.join(domains)}\n\n"

        for i, paper in enumerate(papers):
            message += f"--- 文献 {i + 1} ---\n"
            message += f"ID: {i + 1}\n"
            message += f"标题: {paper.get('title', 'N/A')}\n"

            abstract = paper.get('abstract', '')
            if abstract:
                abstract = abstract[:500] + "..." if len(abstract) > 500 else abstract
                message += f"摘要: {abstract}\n"

            keywords = paper.get('keywords', [])
            if keywords:
                keywords = keywords[:5]
                message += f"关键词: {', '.join(keywords)}\n"

            message += "\n"

        message += f"\n请返回 {len(papers)} 个结果，paper_id 从 1 到 {len(papers)} 连续编号。"

        return message

    def _parse_response(self, response: str, expected_count: int, domain_count: int) -> List[Dict]:
        """解析 AI 响应

        Args:
            response: AI 响应字符串
            expected_count: 期望的结果数量
            domain_count: 领域数量

        Returns:
            解析后的分类结果列表
        """
        # 尝试提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response.strip()

        # 尝试补全被截断的 JSON
        if not json_str.rstrip().endswith(']'):
            self.logger.warning("JSON 响应被截断，尝试补全...")
            # 统计未完成的 object
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')

            # 补全缺失的闭合括号
            missing = close_braces - open_braces
            if missing < 0:
                json_str += '}' * abs(missing)
                # 补全数组结束
                if not json_str.rstrip().endswith(']'):
                    json_str += '\n  }\n]'
                self.logger.info(f"已补全 JSON，添加了 {abs(missing)} 个闭合括号")

        # 解析 JSON
        try:
            results = json.loads(json_str)

            if not isinstance(results, list):
                self.logger.warning(f"响应不是列表格式")
                return []

            if len(results) != expected_count:
                self.logger.warning(f"返回结果数量 ({len(results)}) 与期望 ({expected_count}) 不符")

            return results

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            self.logger.error(f"响应内容前500字符: {response[:500]}")
            self.logger.error(f"响应内容后500字符: {response[-500:]}")
            return []
