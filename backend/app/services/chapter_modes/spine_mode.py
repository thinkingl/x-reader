"""Spine 模式：EPUB 每个 HTML 文件 = 一章（回退模式）"""

import logging
from typing import List, Dict, Any
from .base import ChapterMode, Chapter

logger = logging.getLogger(__name__)


class SpineFileMode(ChapterMode):
    """EPUB spine 文件模式：每个 HTML 文件作为独立章节"""

    name = "spine_file"

    def applicable(self, context: Dict[str, Any]) -> bool:
        return "epub_zip" in context and "spine_ids" in context

    def extract(self, context: Dict[str, Any]) -> List[Chapter]:
        from bs4 import BeautifulSoup

        epub_zip = context.get("epub_zip")
        spine_ids = context.get("spine_ids", [])
        manifest = context.get("manifest", {})
        opf_dir = context.get("opf_dir", ".")
        book_title = context.get("book_title", "")

        if not epub_zip or not spine_ids:
            return []

        # 从 ncx 获取标题映射
        ncx_titles = context.get("ncx_titles", {})

        chapters = []
        for idref in spine_ids:
            if idref not in manifest:
                continue
            href = manifest[idref]
            file_path = href if opf_dir == "." else f"{opf_dir}/{href}"
            if file_path not in epub_zip.namelist():
                continue

            # 跳过封面和目录
            if idref in ("cover", "coverpage", "nav", "toc"):
                continue

            content_bytes = epub_zip.read(file_path)
            content = content_bytes.decode("utf-8", errors="ignore")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")

            # 提取标题
            title = ncx_titles.get(file_path)
            if not title:
                title = self._extract_title(soup, len(chapters), book_title)

            # 提取正文
            head = soup.find("head")
            if head:
                head.decompose()
            text = soup.get_text(separator="\n", strip=True)

            if text and len(text) > 10:
                chapters.append(Chapter(title=title, text_content=text))

        return chapters

    def _extract_title(self, soup, chapter_num: int, book_title: str = "") -> str:
        """从 HTML 提取标题"""
        from .base import Chapter
        import re

        GENERIC_TITLES = {"正文", "Chapter", "无标题", "Untitled"}

        # h1-h3 标签
        title_tag = soup.find(["h1", "h2", "h3"])
        if title_tag:
            return title_tag.get_text(strip=True)

        # <title> 标签（排除书名和通用标题）
        html_title = soup.find("title")
        if html_title and html_title.string:
            t = html_title.string.strip()
            if t not in GENERIC_TITLES and t != book_title:
                return t

        return f"Chapter {chapter_num + 1}"
