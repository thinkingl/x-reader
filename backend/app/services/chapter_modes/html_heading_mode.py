"""HTML 标题模式：从 HTML 结构中的 H1/H2/H3 标签提取章节"""

import os
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import ChapterMode, Chapter, build_chapters

logger = logging.getLogger(__name__)


class HtmlHeadingMode(ChapterMode):
    """从 HTML heading 标签 (h1/h2/h3) 提取章节。

    适用于 MOBI/EPUB 中有明确 heading 结构的电子书，
    特别是英文小说合集（如 Sherlock Holmes）。
    """

    name = "html_heading"

    def __init__(self, heading_tags: tuple = ("h3",)):
        self.heading_tags = heading_tags

    def applicable(self, context: Dict[str, Any]) -> bool:
        html_path = context.get("html_path")
        return html_path and os.path.exists(html_path)

    def extract(self, context: Dict[str, Any]) -> List[Chapter]:
        html_path = context.get("html_path")
        if not html_path or not os.path.exists(html_path):
            return []

        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # 找到所有 heading 标签的位置
        headings = []
        for tag in self.heading_tags:
            for el in soup.find_all(tag):
                text = el.get_text(strip=True)
                if text and len(text) > 1:
                    headings.append((el, text))

        if len(headings) < 3:
            return []

        # 按 DOM 顺序排序（BeautifulSoup find_all 本身是文档顺序）
        # 构建章节：每个 heading 到下一个 heading 之间的内容
        chapter_data = []
        for i, (el, title) in enumerate(headings):
            # 收集当前 heading 到下一个 heading 之间的所有文本
            content_parts = []
            for sibling in el.next_siblings:
                # 遇到同类型 heading 标签就停止（包括被过滤掉的短标题）
                if hasattr(sibling, "name") and sibling.name in self.heading_tags:
                    break
                if i + 1 < len(headings) and sibling is headings[i + 1][0]:
                    break
                if hasattr(sibling, "get_text"):
                    text = sibling.get_text(separator="\n", strip=True)
                    if text:
                        content_parts.append(text)
                elif isinstance(sibling, str):
                    text = sibling.strip()
                    if text:
                        content_parts.append(text)

            content = "\n".join(content_parts)
            chapter_data.append({"title": title, "content": content})

        return build_chapters(chapter_data)
