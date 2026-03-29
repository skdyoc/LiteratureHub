"""
Readers 模块

职责：安全、完整地读取 Markdown 文件
设计原则：完整读取，不截断，保留原文
"""

from .full_md_reader import FullMdReader

__all__ = ["FullMdReader"]
