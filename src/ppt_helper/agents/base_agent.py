"""
AI Agent 基类

所有 AI Agent 的基础类，定义统一的接口和 GLM-4.7 API 调用逻辑
"""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from zhipuai import ZhipuAI


class APIKeyManager:
    """API 密钥管理器 - 单密钥模式"""

    def __init__(self, keys_file: str):
        """
        初始化 API 密钥管理器

        Args:
            keys_file: API 密钥文件路径（只使用第一个密钥）
        """
        self.keys_file = keys_file
        self.api_key = self._load_first_key()

    def _load_first_key(self) -> Optional[str]:
        """从文件加载第一个 API 密钥"""
        try:
            with open(self.keys_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释行
                    if line and not line.startswith("#"):
                        return line
            return None
        except Exception as e:
            print(f"❌ 加载 API 密钥失败: {e}")
            return None

    def get_key(self) -> Optional[str]:
        """
        获取 API 密钥

        Returns:
            API 密钥，如果没有可用密钥返回 None
        """
        return self.api_key


class BaseAgent(ABC):
    """AI Agent 基类"""

    # ⭐ Coding API 端点
    CODING_API_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"

    def __init__(self, keys_file: str, model: str = "glm-4.7"):
        """
        初始化 Agent

        Args:
            keys_file: API 密钥文件路径
            model: 模型名称
        """
        self.model = model

        # ⭐ 直接使用相对路径（不要转换为绝对路径，避免中文路径问题）
        self.api_key_manager = APIKeyManager(keys_file)

        # 获取密钥
        self.current_api_key = self.api_key_manager.get_key()

        if not self.current_api_key:
            raise ValueError(f"⚠️ 没有可用的 API 密钥！请检查 {keys_file}")

    def _call_glm_api(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 128000,  # ⭐ GLM-4.7 API 上限（不能超过 128000）
        timeout: int = 3000,  # ⭐ 超时时间：3000 秒（50 分钟）
        retry_count: int = 0,
    ) -> Optional[str]:
        """
        调用 GLM-4.7 API（使用 Coding API 端点）

        Args:
            prompt: Prompt 模板
            temperature: 温度参数
            max_tokens: 最大 token 数
            timeout: 超时时间（秒），默认 3000 秒
            retry_count: 重试次数

        Returns:
            API 响应内容，如果失败返回 None
        """
        max_retries = 3

        self.log_progress(f"API 调用中（超时: {timeout}秒）...")

        for attempt in range(max_retries):
            try:
                # ⭐ 创建客户端，使用 Coding API 端点
                client = ZhipuAI(
                    api_key=self.current_api_key,
                    base_url=self.CODING_API_BASE_URL  # ⭐ 使用 Coding API 端点
                )

                # 调用 API（添加超时参数）
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,  # ⭐ 超时参数
                )

                # 提取响应内容
                content = response.choices[0].message.content

                self.log_progress(f"API 调用成功（收到 {len(content)} 字符）")
                return content

            except Exception as e:
                error_type = type(e).__name__
                print(f"⚠️ API 调用失败（尝试 {attempt + 1}/{max_retries}）: {error_type}: {e}")

                # ⭐ 检查是否是速率限制错误
                is_rate_limit = "429" in str(e) or "1302" in str(e) or "rate limit" in str(e).lower()

                if attempt < max_retries - 1:
                    if is_rate_limit:
                        # 速率限制：等待更长时间（60 秒）
                        wait_time = 60
                        print(f"⏳ 遇到速率限制，等待 {wait_time} 秒后重试...")
                        print(f"💡 提示：也可以等待 30-60 分钟后手动重新运行")
                    else:
                        # 其他错误：指数退避
                        wait_time = 2**attempt
                        print(f"⏳ 等待 {wait_time} 秒后重试...")

                    time.sleep(wait_time)
                else:
                    print(f"❌ API 调用最终失败")
                    if is_rate_limit:
                        print(f"💡 建议：等待 30-60 分钟后重新运行，或者检查 API 密钥配额")
                    return None

        return None

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 API 返回的 JSON

        Args:
            response: API 响应内容

        Returns:
            解析后的 JSON 对象，如果失败返回 None
        """
        if not response:
            print("❌ 响应为空")
            return None

        # ⭐ 保存完整响应用于调试
        debug_file = Path("data/processed/debug_api_response.txt")
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response)
        print(f"🔍 完整响应已保存到: {debug_file}")

        # 尝试直接解析
        try:
            result = json.loads(response)
            print("✅ 直接解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️ 直接解析失败: {e}")

        # 尝试提取 JSON 块（处理 Markdown 代码块）
        try:
            # 查找 ```json ... ```
            start = response.find("```json")
            if start != -1:
                start += 7  # 跳过 ```json
                # 跳过换行符
                while start < len(response) and response[start] in ['\n', '\r']:
                    start += 1

                end = response.find("```", start)
                if end != -1:
                    json_str = response[start:end].strip()
                    print(f"🔍 提取到的 JSON 字符串长度: {len(json_str)}")
                    print(f"🔍 JSON 开头: {json_str[:200]}...")
                    result = json.loads(json_str)
                    print("✅ 代码块解析成功")
                    return result
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️ 代码块解析失败: {e}")

        # 尝试提取 {...} 块
        try:
            start = response.find("{")
            if start != -1:
                # 找到匹配的 }
                brace_count = 0
                for i in range(start, len(response)):
                    if response[i] == "{":
                        brace_count += 1
                    elif response[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start : i + 1]
                            print(f"🔍 提取 {{...}} 块长度: {len(json_str)}")
                            result = json.loads(json_str)
                            print("✅ {{...}} 块解析成功")
                            return result
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️ {{...}} 块解析失败: {e}")

        print(f"❌ JSON 解析失败（所有方法都失败）")
        print(f"响应内容（前500字符）: {response[:500]}...")
        return None

    @abstractmethod
    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析任务（子类必须实现）

        Args:
            input_data: 输入数据

        Returns:
            分析结果
        """
        pass

    def save_result(self, result: Dict[str, Any], output_path: str) -> bool:
        """
        保存分析结果到 JSON 文件

        Args:
            result: 分析结果
            output_path: 输出文件路径

        Returns:
            True 如果成功，False 否则
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False

    def load_result(self, input_path: str) -> Optional[Dict[str, Any]]:
        """
        从 JSON 文件加载分析结果

        Args:
            input_path: 输入文件路径

        Returns:
            分析结果，如果加载失败返回 None
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return None

    def validate_result(
        self, result: Dict[str, Any], required_fields: List[str]
    ) -> bool:
        """
        验证分析结果的完整性

        Args:
            result: 分析结果
            required_fields: 必需字段列表

        Returns:
            True 如果完整，False 否则
        """
        if not result:
            print(f"❌ 结果为空")
            return False

        for field in required_fields:
            if field not in result:
                print(f"❌ 缺少必需字段: {field}")
                return False

        return True

    def log_progress(self, message: str):
        """
        记录进度信息

        Args:
            message: 进度信息
        """
        print(f"[{self.__class__.__name__}] {message}")


# ============================================================================
# 使用示例
# ============================================================================


class ExampleAgent(BaseAgent):
    """示例 Agent"""

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析"""
        self.log_progress("开始分析...")

        # 这里是实际的 AI 调用逻辑
        # 构造 Prompt
        prompt = f"分析以下数据：{input_data}"

        # 调用 API
        response = self._call_glm_api(prompt)

        # 解析响应
        if response:
            result = self._parse_json_response(response)
            if result:
                self.log_progress("分析完成")
                return result

        # 如果失败，返回默认结果
        return {"status": "failed", "message": "API 调用失败"}


if __name__ == "__main__":
    # 使用示例
    try:
        agent = ExampleAgent(keys_file="config/api_keys.txt", model="glm-4.7")

        # 执行分析
        input_data = {"test": "data"}
        result = agent.analyze(input_data)

        print(f"结果: {result}")

        # 验证结果
        is_valid = agent.validate_result(result, required_fields=["status"])
        print(f"结果有效: {is_valid}")

    except Exception as e:
        print(f"❌ 错误: {e}")
