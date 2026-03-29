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
DeepSeek API 客户端（混合模式版本）
基于 OpenAI SDK，支持 DeepSeek-V3.2 模型
支持为不同分析器选择不同的模型

克隆自: Wind-Aero-Literature-Analysis-System/src/api/deepseek_client.py
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from cryptography.fernet import Fernet
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout: int = 300,
    ):
        """
        初始化 DeepSeek 客户端

        Args:
            api_key: DeepSeek API 密钥
            model: 模型名称 (deepseek-chat 或 deepseek-reasoner)
            base_url: API 基础 URL
            timeout: 超时时间（秒）
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model
        self.timeout = timeout
        logger.info(f"DeepSeek 客户端初始化完成: model={model}, timeout={timeout}s")

    def analyze(self, prompt: str, extract_json: bool = True) -> Dict[str, Any]:
        """
        分析单个 Prompt

        Args:
            prompt: 完整的 Prompt
            extract_json: 是否尝试提取 JSON

        Returns:
            分析结果
        """
        try:
            logger.info(f"调用 DeepSeek API: {self.model}")

            start_time = time.time()

            # 构建消息
            messages = [
                {"role": "system", "content": "你是一位专业的学术分析专家。"},
                {"role": "user", "content": prompt},
            ]

            # 思考模式需要特殊处理
            if self.model == "deepseek-reasoner":
                # 思考模式：启用思考参数
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=False,
                    extra_body={"thinking": {"type": "enabled"}},
                )
                # 提取思考内容
                reasoning_content = response.choices[0].message.reasoning_content
                if reasoning_content:
                    logger.info(f"思考模式推理内容长度: {len(reasoning_content)} 字符")
            else:
                # 标准模式
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, stream=False, temperature=0.7
                )

            elapsed_time = time.time() - start_time

            # 提取响应内容
            content = response.choices[0].message.content
            usage = response.usage

            logger.info(
                f"API 调用成功: 耗时 {elapsed_time:.2f}s, tokens: {usage.total_tokens}"
            )

            # 尝试提取 JSON
            parsed = False
            parsed_result = None

            if extract_json:
                parsed_result = self._extract_json_from_response(content)
                if parsed_result:
                    parsed = True
                    logger.info("成功提取 JSON 结果")
                else:
                    logger.warning("未能提取 JSON，返回原始文本")

            return {
                "success": True,
                "content": content,
                "parsed": parsed,
                "result": parsed_result if parsed else content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "elapsed_time": elapsed_time,
                "model": self.model,
            }

        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return {"success": False, "error": str(e)}

    def _extract_json_from_response(self, content: str) -> Optional[Dict]:
        """
        从响应中提取 JSON

        Args:
            content: 响应内容

        Returns:
            解析后的 JSON 对象，失败返回 None
        """
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取 markdown 代码块中的 JSON
        if "```json" in content:
            try:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试提取普通代码块中的 JSON
        if "```" in content:
            try:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
                # 移除可能的语言标识符（如 "json"）
                lines = json_str.split("\n")
                if lines and lines[0].strip().lower() in ["json", "javascript"]:
                    json_str = "\n".join(lines[1:])
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试查找 {...} 模式
        import re

        try:
            match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

        return None


class DeepSeekParallelAnalyzer:
    """DeepSeek 并行分析器（混合模式）"""

    # 模型配置：分析器名称 → 模型类型
    ANALYZER_MODELS = {
        "innovation": "deepseek-reasoner",  # 创新点分析：需要深度推理
        "motivation": "deepseek-chat",  # 研究动机：中等复杂度
        "roadmap": "deepseek-chat",  # 技术路线：中等复杂度
        "mechanism": "deepseek-reasoner",  # 机理解析：需要深度推理
        "impact": "deepseek-chat",  # 影响评估：相对简单
    }

    def __init__(
        self,
        api_keys_file: str = "D:/xfs/phd/.私人信息/deepseek_api_keys_encrypted.txt",
        default_model: str = "deepseek-chat",
        reasoning_model: str = "deepseek-reasoner",
        password: str = "2580",
        max_workers: int = 5,
    ):
        """
        初始化并行分析器

        Args:
            api_keys_file: 加密的 API 密钥文件路径
            default_model: 默认模型（用于简单分析器）
            reasoning_model: 推理模型（用于复杂分析器）
            password: 解密密码
            max_workers: 最大并行数
        """
        # 加载并解密 API 密钥
        self.api_keys = self._load_api_keys(api_keys_file, password)

        if not self.api_keys:
            raise ValueError("未能加载任何 API 密钥")

        # 为每种模型类型创建客户端池
        self.chat_clients = []
        self.reasoner_clients = []

        # 交替分配 API Key 到两种模型
        for i, key in enumerate(self.api_keys):
            if i % 2 == 0:
                # 偶数索引分配给 chat 模型
                self.chat_clients.append(
                    DeepSeekClient(api_key=key, model=default_model, timeout=300)
                )
            else:
                # 奇数索引分配给 reasoner 模型
                self.reasoner_clients.append(
                    DeepSeekClient(
                        api_key=key, model=reasoning_model, timeout=600  # 思考模式需要更长时间
                    )
                )

        self.current_chat_index = 0
        self.current_reasoner_index = 0
        self.max_workers = max_workers
        self.default_model = default_model
        self.reasoning_model = reasoning_model

        logger.info(f"DeepSeek 混合并行分析器初始化完成:")
        logger.info(f"  - Chat 模型客户端: {len(self.chat_clients)} 个 ({default_model})")
        logger.info(
            f"  - Reasoner 模型客户端: {len(self.reasoner_clients)} 个 ({reasoning_model})"
        )
        logger.info(f"  - 最大并发数: {max_workers}")

        logger.info("分析器模型分配:")
        for analyzer, model in self.ANALYZER_MODELS.items():
            model_type = "推理模式" if "reasoner" in model else "标准模式"
            logger.info(f"  - {analyzer}: {model} ({model_type})")

    def _load_api_keys(self, encrypted_file: str, password: str) -> List[str]:
        """
        加载并解密 API 密钥

        Args:
            encrypted_file: 加密的密钥文件
            password: 解密密码

        Returns:
            API 密钥列表
        """
        try:
            # 生成解密密钥
            key = base64.urlsafe_b64encode(password.encode("latin-1").ljust(32)[:32])
            cipher = Fernet(key)

            # 读取加密文件
            with open(encrypted_file, "r", encoding="utf-8") as f:
                encrypted_keys = [line.strip() for line in f if line.strip()]

            # 解密
            api_keys = []
            for encrypted_key in encrypted_keys:
                decrypted = cipher.decrypt(encrypted_key.encode("utf-8"))
                api_keys.append(decrypted.decode("utf-8"))

            logger.info(f"成功解密 {len(api_keys)} 个 API 密钥")
            return api_keys

        except Exception as e:
            logger.error(f"加载 API 密钥失败: {e}")
            return []

    def analyze_paper(
        self,
        analyzer_prompts: Dict[str, str],
        paper_id: str,
        progress_callback: Optional[Callable[[str, str, bool], None]] = None,
    ) -> Dict[str, Any]:
        """
        并行分析单篇论文（真正的并发执行）

        Args:
            analyzer_prompts: 分析器名称到Prompt的映射
            paper_id: 论文ID
            progress_callback: 进度回调函数

        Returns:
            所有分析器的结果
        """
        logger.info(f"开始混合模式并行分析论文: {paper_id}")
        logger.info(f"分析器: {list(analyzer_prompts.keys())}")

        results = {}
        start_time = time.time()

        # 使用线程池真正并发执行所有分析器
        logger.info(f"并发执行 {len(analyzer_prompts)} 个分析器（最大并发: {self.max_workers}）")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 准备所有任务
        tasks = {}
        for analyzer, prompt in analyzer_prompts.items():
            # 确定使用哪个模型
            model = self.ANALYZER_MODELS.get(analyzer, self.default_model)
            is_reasoner = "reasoner" in model

            # 获取对应模型的客户端
            client = self._get_client_by_model(model)

            # 创建任务
            tasks[analyzer] = {
                "client": client,
                "prompt": prompt,
                "model": model,
                "is_reasoner": is_reasoner,
            }

            # 🔔 通知：分析器开始
            if progress_callback:
                try:
                    model_type = "深度推理" if is_reasoner else "快速分析"
                    progress_callback(
                        analyzer, f"并发启动: {analyzer} ({model_type})...", True
                    )
                except Exception as e:
                    logger.warning(f"进度回调失败（开始）: {e}")

        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_analyzer = {}
            for analyzer, task_info in tasks.items():
                future = executor.submit(
                    self._analyze_single,
                    task_info["client"],
                    analyzer,
                    task_info["prompt"],
                    task_info["model"],
                )
                future_to_analyzer[future] = analyzer

            # 收集结果（按完成顺序）
            for future in as_completed(future_to_analyzer):
                analyzer = future_to_analyzer[future]
                try:
                    result = future.result()
                    results[analyzer] = result

                    if result.get("success"):
                        model = tasks[analyzer]["model"]
                        logger.info(f"✓ {analyzer} 分析完成 (模型: {model})")

                        # 🔔 通知：分析器完成
                        if progress_callback:
                            try:
                                progress_callback(analyzer, f"✓ {analyzer} 完成", False)
                            except Exception as e:
                                logger.warning(f"进度回调失败（完成）: {e}")
                    else:
                        logger.warning(
                            f"✗ {analyzer} 分析失败: {result.get('error', 'Unknown')}"
                        )

                        # 🔔 通知：分析器失败
                        if progress_callback:
                            try:
                                progress_callback(analyzer, f"✗ {analyzer} 失败", False)
                            except Exception as e:
                                logger.warning(f"进度回调失败（失败）: {e}")

                except Exception as e:
                    logger.error(f"{analyzer} 执行异常: {e}")
                    results[analyzer] = {"success": False, "error": str(e)}

        elapsed_time = time.time() - start_time
        logger.info(f"论文 {paper_id} 分析完成，总耗时: {elapsed_time:.2f}秒")

        # 统计 Token 使用
        total_tokens = sum(
            r.get("usage", {}).get("total_tokens", 0)
            for r in results.values()
            if r.get("success")
        )
        logger.info(f"总计消耗 Token: {total_tokens}")

        return results

    def _get_client_by_model(self, model: str) -> DeepSeekClient:
        """
        根据模型类型获取客户端

        Args:
            model: 模型名称

        Returns:
            对应的客户端
        """
        if "reasoner" in model:
            # 使用推理模式客户端
            client = self.reasoner_clients[self.current_reasoner_index]
            self.current_reasoner_index = (self.current_reasoner_index + 1) % len(
                self.reasoner_clients
            )
            return client
        else:
            # 使用标准模式客户端
            client = self.chat_clients[self.current_chat_index]
            self.current_chat_index = (self.current_chat_index + 1) % len(
                self.chat_clients
            )
            return client

    def _analyze_single(
        self, client: DeepSeekClient, analyzer: str, prompt: str, model: str
    ) -> Dict[str, Any]:
        """
        执行单个分析器

        Args:
            client: DeepSeek 客户端
            analyzer: 分析器名称
            prompt: 完整的 Prompt
            model: 使用的模型

        Returns:
            分析结果
        """
        return client.analyze(prompt, extract_json=True)
