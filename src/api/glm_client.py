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
GLM API 客户端

功能：
1. 调用智谱AI GLM-4.7 模型
2. 支持异步调用
3. 错误处理和重试机制
"""

import aiohttp
import json
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GLMAPIClient:
    """智谱AI API客户端（异步版本）"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.7",
        base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4",
        timeout: int = 1200,  # 20 分钟默认超时（与 Coding API 匹配）
        max_retries: int = 3
    ):
        """
        初始化GLM API客户端

        Args:
            api_key: 智谱API Key
            model: 模型名称（glm-4.7, glm-4-plus, glm-4-flash）
            base_url: API基础URL
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate(
        self,
        system_message: str,
        user_message: str,
        temperature: float = 0.3,
        top_p: float = 0.9,
        max_tokens: int = 128000  # 与 Coding API 上限一致
    ) -> str:
        """
        异步调用 GLM API

        Args:
            system_message: 系统消息
            user_message: 用户消息
            temperature: 温度参数（0-1）
            top_p: top_p 采样参数
            max_tokens: 最大token数

        Returns:
            str: AI 返回的内容
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"[GLM-DEBUG] 调用GLM API（尝试 {attempt + 1}/{self.max_retries}）")
                logger.info(f"[GLM-DEBUG] 请求URL: {url}")
                logger.info(f"[GLM-DEBUG] 请求超时: {self.timeout}秒")

                timeout = aiohttp.ClientTimeout(total=self.timeout)
                logger.info(f"[GLM-DEBUG] 准备创建 ClientSession...")
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"[GLM-DEBUG] ClientSession 创建成功，准备发送POST请求...")
                    logger.info(f"[GLM-DEBUG] 请求payload大小: {len(str(payload))} 字符")
                    async with session.post(url, json=payload, headers=headers) as response:
                        logger.info(f"[GLM-DEBUG] 收到响应，状态码: {response.status}")
                        response.raise_for_status()
                        logger.info(f"[GLM-DEBUG] 开始解析 JSON 响应...")
                        result = await response.json()
                        logger.info(f"[GLM-DEBUG] JSON 解析成功")

                        # 检查响应
                        if "choices" in result and len(result["choices"]) > 0:
                            message = result["choices"][0]["message"]
                            content = message.get("content", "")

                            # 如果 content 为空，尝试从 reasoning_content 获取
                            if not content or len(content.strip()) == 0:
                                content = message.get("reasoning_content", "")
                                if not content or len(content.strip()) == 0:
                                    # 检查是否所有可用字段都为空
                                    all_keys = list(message.keys())
                                    logger.error(f"API返回了空内容！消息字段: {all_keys}")
                                    logger.error(f"完整消息: {message}")
                                    # 尝试从所有字段中获取内容
                                    for key in all_keys:
                                        if key not in ["content", "reasoning_content"]:
                                            alt_content = message.get(key, "")
                                            if alt_content and len(str(alt_content).strip()) > 0:
                                                logger.info(f"从字段 '{key}' 获取到内容，长度 {len(str(alt_content))}")
                                                content = str(alt_content)
                                                break
                                    if not content or len(content.strip()) == 0:
                                        logger.error(f"API返回了空内容！完整响应: {result}")
                                        raise ValueError("API返回空内容")
                                logger.info(f"API 调用成功（从 reasoning_content 获取），返回 {len(content)} 字符")
                            else:
                                logger.info(f"API 调用成功，返回 {len(content)} 字符")
                            return content
                        else:
                            logger.error(f"API响应格式异常: {result}")
                            raise ValueError("Invalid response format")

            except asyncio.TimeoutError:
                logger.warning(f"API调用超时（尝试 {attempt + 1}）")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                raise TimeoutError(f"API 调用超时（{self.timeout}秒）")

            except aiohttp.ClientResponseError as e:
                logger.error(f"HTTP错误: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            except Exception as e:
                logger.error(f"API调用失败: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise RuntimeError(f"API 调用失败，已重试 {self.max_retries} 次")

    def call_api(self, prompt: str) -> Dict[str, Any]:
        """
        同步调用 GLM API（兼容旧代码）

        Args:
            prompt: 完整的提示词

        Returns:
            API响应结果
        """
        # 使用 asyncio.run 将异步调用转换为同步
        return asyncio.run(self._call_api_async(prompt))

    async def _call_api_async(self, prompt: str) -> Dict[str, Any]:
        """异步调用 API 的内部实现"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 128000  # 与 Coding API 上限一致
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"[GLM-DEBUG] 调用GLM API（尝试 {attempt + 1}/{self.max_retries}）")
                logger.info(f"[GLM-DEBUG] 请求URL: {url}")
                logger.info(f"[GLM-DEBUG] 请求超时: {self.timeout}秒")

                timeout = aiohttp.ClientTimeout(total=self.timeout)
                logger.info(f"[GLM-DEBUG] 准备创建 ClientSession...")
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"[GLM-DEBUG] ClientSession 创建成功，准备发送POST请求...")
                    logger.info(f"[GLM-DEBUG] 请求payload大小: {len(str(payload))} 字符")
                    async with session.post(url, json=payload, headers=headers) as response:
                        logger.info(f"[GLM-DEBUG] 收到响应，状态码: {response.status}")
                        response.raise_for_status()
                        logger.info(f"[GLM-DEBUG] 开始解析 JSON 响应...")
                        result = await response.json()
                        logger.info(f"[GLM-DEBUG] JSON 解析成功")

                        # 检查响应
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            return {
                                "success": True,
                                "content": content,
                                "model": result.get("model", self.model),
                                "usage": result.get("usage", {})
                            }
                        else:
                            logger.warning(f"API响应格式异常: {result}")
                            return {
                                "success": False,
                                "error": "Invalid response format",
                                "response": result
                            }

            except asyncio.TimeoutError:
                logger.warning(f"API调用超时（尝试 {attempt + 1}）")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {
                    "success": False,
                    "error": "Timeout"
                }

            except aiohttp.ClientResponseError as e:
                logger.error(f"HTTP错误: {e}")
                return {
                    "success": False,
                    "error": f"HTTP error: {e}"
                }

            except Exception as e:
                logger.error(f"API调用失败: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        return {
            "success": False,
            "error": "Max retries exceeded"
        }

    def extract_json_from_response(self, content: str) -> Optional[Dict]:
        """
        从API响应中提取JSON内容

        Args:
            content: API返回的文本内容

        Returns:
            解析后的JSON对象，如果失败返回None
        """
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的JSON
        import re

        # 查找 ```json ... ``` 格式
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_pattern, content, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # 查找 { ... } 格式
        brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(brace_pattern, content, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        logger.warning("无法从响应中提取JSON")
        return None


class GLMParallelAnalyzer:
    """GLM 并行分析器（使用智谱 AI GLM-4.7 模型）"""

    # 所有分析器使用相同的模型
    MODEL = "glm-4.7"
    BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"  # ⭐ 必须使用 coding 端点

    def __init__(
        self,
        api_keys_file: str = "D:/xfs/phd/.私人信息/glm_api_keys.txt",
        model: str = "glm-4.7",
        base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4",
        password: str = "2580",
        max_workers: int = 5,
    ):
        """
        初始化 GLM 并行分析器

        Args:
            api_keys_file: 加密的 API 密钥文件路径（或普通文件）
            model: 模型名称
            base_url: API 基础 URL（必须使用 coding 端点）
            password: 解密密码（如果文件加密）
            max_workers: 最大并行数
        """
        # 加载 API 密钥
        self.api_keys = self._load_api_keys(api_keys_file, password)

        if not self.api_keys:
            raise ValueError("未能加载任何 GLM API 密钥")

        # 为每个 API Key 创建客户端
        self.clients = []
        for key in self.api_keys:
            self.clients.append(
                GLMAPIClient(api_key=key, model=model, base_url=base_url, timeout=600)
            )

        self.current_index = 0
        self.max_workers = max_workers
        self.model = model
        self.base_url = base_url

        logger.info(f"GLM 并行分析器初始化完成:")
        logger.info(f"  - 客户端数量: {len(self.clients)} 个")
        logger.info(f"  - 模型: {model}")
        logger.info(f"  - API 端点: {base_url}")
        logger.info(f"  - 最大并发数: {max_workers}")

    def _load_api_keys(self, api_keys_file: str, password: str) -> list:
        """
        加载 API 密钥（支持加密和普通文件）

        Args:
            api_keys_file: API 密钥文件路径
            password: 解密密码

        Returns:
            API 密钥列表
        """
        import base64
        from pathlib import Path
        from cryptography.fernet import Fernet

        api_keys = []

        try:
            # 尝试作为加密文件加载
            key = base64.urlsafe_b64encode(password.encode("latin-1").ljust(32)[:32])
            cipher = Fernet(key)

            with open(api_keys_file, "r", encoding="utf-8") as f:
                encrypted_keys = [line.strip() for line in f if line.strip()]

            for encrypted_key in encrypted_keys:
                try:
                    decrypted = cipher.decrypt(encrypted_key.encode("utf-8"))
                    api_keys.append(decrypted.decode("utf-8"))
                except Exception:
                    # 如果解密失败，可能是未加密的文件
                    raise ValueError("需要使用未加密的加载方式")

            logger.info(f"成功解密 {len(api_keys)} 个 GLM API 密钥")
            return api_keys

        except Exception as e:
            logger.info(f"加密文件加载失败，尝试普通文件: {e}")

            # 尝试作为普通文件加载
            try:
                with open(api_keys_file, "r", encoding="utf-8") as f:
                    # ⭐ 修复：过滤掉注释行（以#开头）和空行
                    api_keys = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith("#")
                    ]

                logger.info(f"成功加载 {len(api_keys)} 个 GLM API 密钥（普通文件）")
                return api_keys

            except Exception as e2:
                logger.error(f"加载 API 密钥失败: {e2}")
                return []

    def _get_client(self) -> GLMAPIClient:
        """轮询获取客户端"""
        client = self.clients[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.clients)
        return client

    def analyze_paper(
        self,
        analyzer_prompts: Dict[str, str],
        paper_id: str,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        并行分析单篇论文

        Args:
            analyzer_prompts: 分析器名称到 Prompt 的映射
            paper_id: 论文 ID
            progress_callback: 进度回调函数

        Returns:
            所有分析器的结果
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        logger.info(f"开始 GLM 并行分析论文: {paper_id}")
        logger.info(f"分析器: {list(analyzer_prompts.keys())}")

        results = {}

        # 🔔 通知：开始
        for analyzer in analyzer_prompts:
            if progress_callback:
                try:
                    progress_callback(analyzer, f"启动: {analyzer}...", True)
                except Exception as e:
                    logger.warning(f"进度回调失败（开始）: {e}")

        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_analyzer = {}
            for analyzer, prompt in analyzer_prompts.items():
                future = executor.submit(
                    self._analyze_single,
                    analyzer,
                    prompt,
                )
                future_to_analyzer[future] = analyzer

            # 收集结果
            for future in future_to_analyzer:
                analyzer = future_to_analyzer[future]
                try:
                    result = future.result()
                    results[analyzer] = result

                    if result.get("success"):
                        logger.info(f"✓ {analyzer} 分析完成")

                        # 🔔 通知：完成
                        if progress_callback:
                            try:
                                progress_callback(analyzer, f"✓ {analyzer} 完成", False)
                            except Exception as e:
                                logger.warning(f"进度回调失败（完成）: {e}")
                    else:
                        logger.warning(f"✗ {analyzer} 分析失败: {result.get('error', 'Unknown')}")

                        # 🔔 通知：失败
                        if progress_callback:
                            try:
                                progress_callback(analyzer, f"✗ {analyzer} 失败", False)
                            except Exception as e:
                                logger.warning(f"进度回调失败（失败）: {e}")

                except Exception as e:
                    logger.error(f"分析器 {analyzer} 执行异常: {e}")
                    results[analyzer] = {
                        "success": False,
                        "error": str(e),
                        "analyzer_type": "glm",
                    }

        return results

    def _analyze_single(self, analyzer: str, prompt: str) -> Dict[str, Any]:
        """
        分析单个分析器（同步版本）

        Args:
            analyzer: 分析器名称
            prompt: 完整的 Prompt

        Returns:
            分析结果
        """
        client = self._get_client()

        try:
            logger.info(f"[{analyzer}] 开始调用 GLM API...")

            # 使用同步调用
            result = asyncio.run(client._call_api_async(prompt))

            if result.get("success"):
                content = result.get("content", "")

                # 尝试提取 JSON
                json_data = client.extract_json_from_response(content)

                if json_data:
                    logger.info(f"[{analyzer}] ✓ 成功提取 JSON 结果")
                    return {
                        "success": True,
                        "result": json_data,
                        "analyzer_type": "glm",
                        "parsed": True,
                        "raw_content": content,
                        "usage": result.get("usage", {}),
                    }
                else:
                    # 无法提取 JSON，但原始内容可用
                    logger.warning(f"[{analyzer}] ⚠ 无法提取 JSON，返回原始内容")
                    return {
                        "success": True,
                        "result": {"raw_content": content},
                        "analyzer_type": "glm",
                        "parsed": False,
                        "usage": result.get("usage", {}),
                    }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"[{analyzer}] ✗ API 调用失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "analyzer_type": "glm",
                }

        except Exception as e:
            logger.error(f"[{analyzer}] ✗ 分析异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "analyzer_type": "glm",
            }
