"""NCX 模式：基于 toc.ncx 书签的章节检测"""

import os
import logging
from xml.etree import ElementTree as ET
from typing import List, Dict, Any, Optional
from .base import ChapterMode, Chapter, build_chapters

logger = logging.getLogger(__name__)

_NS = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}


def parse_ncx(ncx_path: str) -> List[Dict[str, str]]:
    """解析 toc.ncx，返回 [{title, href, filepos}]"""
    try:
        tree = ET.parse(ncx_path)
        root = tree.getroot()
    except Exception:
        return []

    bookmarks = []
    for np in root.findall('.//ncx:navPoint', _NS):
        label_elem = np.find('ncx:navLabel/ncx:text', _NS)
        content_elem = np.find('ncx:content', _NS)
        if label_elem is None or content_elem is None:
            continue
        label = (label_elem.text or '').strip()
        src = content_elem.get('src', '')
        filepos = None
        if '#filepos' in src:
            try:
                filepos = int(src.split('#filepos')[1])
            except (ValueError, IndexError):
                pass
        href = src.split('#')[0] if '#' in src else src
        bookmarks.append({"title": label, "href": href, "filepos": filepos})
    return bookmarks


class NcxBookmarkMode(ChapterMode):
    """toc.ncx 书签模式：使用 MOBI filepos 或 EPUB href 拆分"""

    name = "ncx_bookmark"

    def __init__(self, format_type: str = "mobi"):
        """
        format_type: "mobi" 用 filepos 拆分单个 HTML，"epub" 用 href 映射多个文件
        """
        self.format_type = format_type

    def applicable(self, context: Dict[str, Any]) -> bool:
        ncx_path = context.get("ncx_path")
        if not ncx_path or not os.path.exists(ncx_path):
            return False
        bookmarks = parse_ncx(ncx_path)
        return len(bookmarks) >= 3

    def extract(self, context: Dict[str, Any]) -> List[Chapter]:
        if self.format_type == "mobi":
            return self._extract_mobi(context)
        else:
            return self._extract_epub(context)

    def _extract_mobi(self, context: Dict[str, Any]) -> List[Chapter]:
        """MOBI: 用 filepos 拆分单个 HTML"""
        import re
        from bs4 import BeautifulSoup

        ncx_path = context.get("ncx_path", "")
        html_path = context.get("html_path", "")
        bookmarks = parse_ncx(ncx_path)

        # 只用有 filepos 的书签
        positioned = [(b["title"], b["filepos"]) for b in bookmarks if b["filepos"] is not None]
        if len(positioned) < 3:
            return []

        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()

        # 找 filepos anchor 位置
        positions = []
        for title, filepos in positioned:
            anchor = f'<a id="filepos{filepos}"'
            idx = html.find(anchor)
            if idx != -1:
                positions.append((title, idx))

        if len(positioned) < 3:
            return []

        # 子条目模式：甲、乙、一、二 等并入父章
        sub_pattern = re.compile(
            r'^[一二三四五六七八九十]{1,2}、'
            r'|^[甲乙丙丁戊己庚辛壬癸]、'
            r'|^[子丑寅卯辰巳午未申酉戌亥]、'
        )

        chapters = []
        current_title = None
        current_texts = []

        soup_parser = BeautifulSoup("", "html.parser")

        for i, (title, pos) in enumerate(positions):
            end_pos = positions[i + 1][1] if i + 1 < len(positions) else len(html)
            section_html = html[pos:end_pos]
            section_soup = BeautifulSoup(section_html, "html.parser")
            text = section_soup.get_text(separator="\n", strip=True)
            if not text:
                continue

            if sub_pattern.match(title):
                if current_title is None:
                    current_title = title
                current_texts.append(text)
            else:
                # 新章节
                if current_texts:
                    content = "\n\n".join(current_texts).strip()
                    if content and len(content) > 10:
                        chapters.append(Chapter(title=current_title or "Untitled", text_content=content))
                current_title = title
                current_texts = [text]

        # 最后一章
        if current_texts:
            content = "\n\n".join(current_texts).strip()
            if content and len(content) > 10:
                chapters.append(Chapter(title=current_title or "Untitled", text_content=content))

        return chapters

    def _extract_epub(self, context: Dict[str, Any]) -> List[Chapter]:
        """EPUB: 用 href 映射到 spine 文件"""
        from bs4 import BeautifulSoup

        ncx_path = context.get("ncx_path", "")
        epub_zip = context.get("epub_zip")
        opf_dir = context.get("opf_dir", ".")
        bookmarks = parse_ncx(ncx_path)

        if not bookmarks or not epub_zip:
            return []

        # 构建 href → title 映射
        href_titles = {}
        for b in bookmarks:
            href = b["href"]
            if opf_dir != ".":
                href = f"{opf_dir}/{href}"
            if href not in href_titles:
                href_titles[href] = b["title"]

        # 按 spine 顺序处理
        spine_ids = context.get("spine_ids", [])
        manifest = context.get("manifest", {})

        chapters = []
        for idref in spine_ids:
            if idref not in manifest:
                continue
            href = manifest[idref]
            file_path = href if opf_dir == "." else f"{opf_dir}/{href}"
            if file_path not in epub_zip.namelist():
                continue

            title = href_titles.get(file_path)
            if not title:
                continue

            content_bytes = epub_zip.read(file_path)
            content = content_bytes.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")
            head = soup.find("head")
            if head:
                head.decompose()
            text = soup.get_text(separator="\n", strip=True)
            if text and len(text) > 10:
                chapters.append(Chapter(title=title, text_content=text))

        return chapters
