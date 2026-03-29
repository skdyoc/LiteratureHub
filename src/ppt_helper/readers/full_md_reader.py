"""
Full.md 文献读取器

职责：完整、安全地读取原始 Markdown 文献
设计原则：
1. 完整读取文档，不截断
2. 保留原文格式和结构
3. 安全的错误处理
"""

from pathlib import Path
from typing import Optional, Dict
import sys
import io


class FullMdReader:
    """Full.md 文献读取器"""

    def __init__(self):
        """初始化读取器"""
        pass

    def read_full_md(self, file_path: str) -> Optional[str]:
        """
        完整读取 full.md 文件

        ⚠️ 重要：必须完整读取，不允许截断或摘要！

        Args:
            file_path: full.md 文件路径

        Returns:
            完整的文档内容，如果读取失败返回 None
        """
        path = Path(file_path)

        if not path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return None

        try:
            # 使用 UTF-8 编码读取
            with open(path, "r", encoding="utf-8", errors="strict") as f:
                content = f.read()

            # 验证内容不为空
            if not content or len(content.strip()) == 0:
                print(f"⚠️ 文件为空: {file_path}")
                return None

            return content

        except UnicodeDecodeError as e:
            print(f"❌ 编码错误: {file_path} - {e}")
            return None

        except Exception as e:
            print(f"❌ 读取失败: {file_path} - {e}")
            return None

    def read_section(self, file_path: str, section_name: str) -> Optional[str]:
        """
        读取文档的特定章节

        Args:
            file_path: full.md 文件路径
            section_name: 章节名称，例如 "Abstract", "Introduction"

        Returns:
            章节内容，如果未找到返回 None
        """
        content = self.read_full_md(file_path)
        if not content:
            return None

        # 简单的章节提取（基于 Markdown 标题）
        lines = content.split("\n")
        section_lines = []
        in_section = False

        for line in lines:
            # 检查是否是目标章节
            if line.strip().startswith(f"# {section_name}"):
                in_section = True
                continue

            # 检查是否遇到下一个同级或更高级标题
            if in_section and line.strip().startswith("#"):
                break

            # 收集章节内容
            if in_section:
                section_lines.append(line)

        if not section_lines:
            return None

        return "\n".join(section_lines)

    def get_metadata(self, file_path: str) -> Dict[str, str]:
        """
        从文档中提取元数据（Front matter）

        Args:
            file_path: full.md 文件路径

        Returns:
            元数据字典
        """
        content = self.read_full_md(file_path)
        if not content:
            return {}

        # 简单的 Front matter 提取（YAML 格式）
        lines = content.split("\n")
        metadata = {}

        if lines[0].strip() == "---":
            in_metadata = True
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

        return metadata

    def validate_complete(self, file_path: str) -> bool:
        """
        验证文档是否完整

        Args:
            file_path: full.md 文件路径

        Returns:
            True 如果文档完整，False 否则
        """
        content = self.read_full_md(file_path)
        if not content:
            return False

        # 检查基本章节
        required_sections = ["Abstract", "Introduction"]
        for section in required_sections:
            if f"# {section}" not in content:
                print(f"⚠️ 缺少章节: {section}")
                return False

        return True


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # Windows UTF-8 支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    # 初始化读取器
    reader = FullMdReader()

    # 读取完整文档
    file_path = "D:/xfs/phd/参考文献/气动/markdown/2026_Paper_ID/full.md"

    print(f"📖 读取文档: {file_path}")
    content = reader.read_full_md(file_path)

    if content:
        print(f"✅ 成功读取，字符数: {len(content)}")
        print(f"   前 200 字符预览:")
        print(f"   {content[:200]}...")

        # 验证完整性
        if reader.validate_complete(file_path):
            print("✅ 文档完整")
        else:
            print("⚠️ 文档可能不完整")

        # 读取特定章节
        abstract = reader.read_section(file_path, "Abstract")
        if abstract:
            print(f"\n📄 Abstract:")
            print(f"   {abstract[:200]}...")

        # 提取元数据
        metadata = reader.get_metadata(file_path)
        if metadata:
            print(f"\n📋 元数据:")
            for key, value in metadata.items():
                print(f"   {key}: {value}")
    else:
        print("❌ 读取失败")
